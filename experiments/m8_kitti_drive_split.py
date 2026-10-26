#!/usr/bin/env python3
"""
m8_kitti_drive_split.py (m8-0.1, 2026-10-19) - KITTI split by recorded drive.

KITTI object frames are mapped to their raw drives with the devkit files mapping/train_rand.txt and
mapping/train_mapping.txt (object frame i -> line train_rand[i] of train_mapping.txt -> date, drive, raw frame).
Then m6 part A (KITTI distance, m1.analyse; labels as run and with the KITTI rule) and m6 part B (change of
dataset, both label versions) are repeated with the parts drawn by drive, in the two variants of m7 (m3-0.4):
  (i)  drives permuted with the original split function and fractions, every frame takes its drive's part,
       the frame stays the unit of the selection test and the HB interval;
  (ii) the same partition, the drive replaces the frame as the unit, with the loss of m3.scene_cell
       (mean of the per-frame a_f over the drive's frames in the cell; 0 for a drive without accepted detections).
In part B the nuScenes side is drawn by recorded scene (sample.json), as in m7; m4.car_cells draws its halves
with its own permutation (frac_select 0.5), which is applied to the units here in the same way.

Order: build the tables (m6.build_kitti, m6.kitti_ignore, m4.build_nuscenes), then the frame split through the
same loops as m6 main; its rows must equal m6/results/A_kitti_range_protocol.csv and
B_shift_seeds_protocol.csv byte for byte and the input hashes must equal m6/results/provenance.json,
otherwise the script stops before any drive-split result is computed. No analysis logic is changed: statistics,
split function and Cell come from m1, m3 and m4 unchanged; only m1.split_frames, m1.Cell and the unit array
passed to the m4-style halving are replaced at run time.
Read-only on /data/inputs, /data/nuscenes and the recorded results; writes only below --out.
"""
import argparse, filecmp, importlib.util, json, platform, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m6", str(HERE / "m6_protocol_seeds_weather.py"))
m6 = importlib.util.module_from_spec(spec); sys.modules["m6"] = m6; spec.loader.exec_module(m6)
m1, m3, m4 = m6.m1, m6.m3, m6.m4
SCRIPT_VERSION = "m8-0.1"
ORIG_SPLIT, ORIG_CELL = m1.split_frames, m1.Cell


def drive_index(devkit, fids):
    rand = [int(v) for v in (devkit / "mapping/train_rand.txt").read_text().strip().split(",")]
    mp = [l.split() for l in (devkit / "mapping/train_mapping.txt").read_text().splitlines() if l.strip()]
    assert len(rand) == len(mp) == 7481 and sorted(rand) == list(range(1, 7482)), "devkit mapping files incomplete"
    drv = [mp[rand[int(f)] - 1][1] for f in fids]
    drives = sorted(set(drv)); pos = {d: i for i, d in enumerate(drives)}
    return np.array([pos[d] for d in drv], dtype=np.int64), drives


def part_A(ktab, kign, split_fn, cell_cls):
    """m6 main, part A loop, unchanged apart from the split function and the Cell class."""
    m1.split_frames, m1.Cell = split_fn, cell_cls
    rows = []
    try:
        for proto, T in (("as_run", ktab), ("kitti_ignore", kign)):
            for ind in m6.IND:
                Ti = dict(T); Ti["u"] = T[ind]
                for seed in m6.SEEDS:
                    info, res, _ = m1.analyse(Ti, T["y_A_iou0.5"], ["Car"], 0.5, seed, m1.CFG, m6.ALPHAS, boot=False)
                    for r in res:
                        for c in r["cells"]:
                            rows.append({"protocol": proto, "indicator": ind, "seed": seed, "alpha": r["alpha"], "cut_m": info["cut_m"],
                                         "established": c["established"], "applied": c["applied"], "outcome": c["outcome"],
                                         "A_hat": c.get("A_hat"), "hb_L": c.get("hb_L"), "hb_U": c.get("hb_U"), "R_hat": c.get("R_hat"),
                                         "_n_select": info["classes"][c["established"]]["frames_select"],
                                         "_n_eval": info["classes"][c["applied"]]["frames_eval"]})
    finally:
        m1.split_frames, m1.Cell = ORIG_SPLIT, ORIG_CELL
    return rows


def unit_cells(tab, car_name, ind, seed, frac_select, uidx, cell_cls):
    """m4.car_cells with the units of uidx permuted instead of frames (identity uidx and m1.Cell = m4.car_cells)."""
    sel_mask = np.isin(tab["cls"], [car_name])
    nU = int(uidx.max()) + 1
    rng = np.random.default_rng(seed)
    codes = np.zeros(nU, dtype=np.int8)
    codes[rng.permutation(nU)[: int(round(frac_select * nU))]] = 1
    dcode = codes[uidx][tab["fpos"]]
    return {name: cell_cls(tab["fpos"][m], tab[ind][m], tab["y_A_iou0.5"][m])
            for name, c in (("select", 1), ("eval", 0)) for m in [sel_mask & (dcode == c)]}


def part_B(ktab, kign, ntab, cells_fn):
    """m6 main, part B loop, unchanged apart from the cell builder."""
    rows = []
    for proto, KT in (("as_run", ktab), ("kitti_ignore", kign)):
        tables = {"kitti": (KT, "Car"), "nuscenes": (ntab, "car")}
        for ind in m6.IND:
            for seed in m6.SEEDS:
                cells = {ds: cells_fn(ds, T, cn, ind, seed) for ds, (T, cn) in tables.items()}
                for src in ("kitti", "nuscenes"):
                    for tgt in ("kitti", "nuscenes"):
                        for alpha in m6.ALPHAS:
                            tau = m4.establish_tau(cells[src]["select"], np.array(m4.CFG["grid_levels"]), alpha, m1.CFG["delta"])
                            r = {"protocol": proto, "indicator": ind, "seed": seed, "alpha": alpha, "source": src, "target": tgt}
                            if tau is None:
                                r["outcome"] = "no threshold established"
                            else:
                                e = m4.evaluate(cells[tgt]["eval"], tau, alpha, m1.CFG["delta"], 200, seed)
                                r.update({k: e[k] for k in ("tau", "A_hat", "hb_L", "hb_U", "R_hat", "outcome")})
                            r["_n_select"], r["_n_eval"] = cells[src]["select"].m, cells[tgt]["eval"].m
                            rows.append(r)
    return rows


def strip(rows):
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]


def units(rows):
    return [{**{k: v for k, v in r.items() if not k.startswith("_")}, "n_select_units": r["_n_select"], "n_eval_units": r["_n_eval"]} for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rum", default="/data/inputs"); ap.add_argument("--out", required=True)
    ap.add_argument("--recorded", default="/data/work/m6/results"); ap.add_argument("--devkit", required=True)
    ap.add_argument("--nusc-meta", default="")
    a = ap.parse_args()
    t0 = time.time(); rum, out, rec = Path(a.rum), Path(a.out), Path(a.recorded); out.mkdir(parents=True, exist_ok=True)
    prov = {"script_version": SCRIPT_VERSION, "m6_version": m6.SCRIPT_VERSION, "m3_version": m3.SCRIPT_VERSION,
            "started": time.strftime("%Y-%m-%d %H:%M:%S"), "python": platform.python_version(), "numpy": np.__version__,
            "devkit_sha256": {f: m1.sha256(Path(a.devkit) / f) for f in ("mapping/train_rand.txt", "mapping/train_mapping.txt")}}
    meta = m6.find_meta(rum, a.nusc_meta)
    if meta is None:
        sys.exit("scene.json/sample.json not reachable; mount the nuScenes root at /data/nuscenes")
    print("building KITTI table and KITTI rule ...", flush=True)
    ktab, kscored, kseed, kin = m6.build_kitti(rum)
    why = m6.kitti_ignore(rum, ktab, kscored, kseed); kign = m6.subset(ktab, why == "")
    print(f"building nuScenes table ... ({time.time() - t0:.0f} s)", flush=True)
    ntab, _, nok, ncache, nbad, nin = m4.build_nuscenes(rum)
    if not nok:
        sys.exit(f"nuScenes verification failed ({nbad}/{ncache})")
    prov["inputs_sha256"] = {str(f): m1.sha256(f) for f in kin + nin}

    # ---- gate: frame split reproduces the recorded m6 A and B rows and input hashes
    print(f"gate: frame split ({time.time() - t0:.0f} s)", flush=True)
    g = out / "frame"; g.mkdir(exist_ok=True)
    m6.write_csv(g / "A_kitti_range_protocol.csv", strip(part_A(ktab, kign, ORIG_SPLIT, ORIG_CELL)))
    m6.write_csv(g / "B_shift_seeds_protocol.csv", strip(part_B(ktab, kign, ntab, lambda ds, T, cn, ind, seed: m4.car_cells(T, cn, ind, seed, 0.5))))
    recp = json.load(open(rec / "provenance.json"))
    same_in = all(prov["inputs_sha256"].get(k) == v for k, v in recp["inputs_sha256"].items())
    same_A = filecmp.cmp(g / "A_kitti_range_protocol.csv", rec / "A_kitti_range_protocol.csv", shallow=False)
    same_B = filecmp.cmp(g / "B_shift_seeds_protocol.csv", rec / "B_shift_seeds_protocol.csv", shallow=False)
    ident = np.arange(ktab["n_frames"])
    for ind in m6.IND:      # unit_cells with frames as units must equal m4.car_cells
        x, y0 = unit_cells(kign, "Car", ind, 3, 0.5, ident, ORIG_CELL), m4.car_cells(kign, "Car", ind, 3, 0.5)
        assert all(x[p].m == y0[p].m and np.array_equal(x[p].u, y0[p].u) for p in x), "unit_cells != m4.car_cells"
    gate = f"REPRODUCTION frame split: m6 A {'EQUAL' if same_A else 'DIFFERS'}, m6 B {'EQUAL' if same_B else 'DIFFERS'}, input hashes {'EQUAL' if same_in else 'DIFFER'}"
    print(gate, flush=True)
    if not (same_A and same_B and same_in):
        (out / "REPRO_FAILED.txt").write_text(gate + "\n"); sys.exit("stopping: frame split does not reproduce")
    (out / "REPRO_PASSED.txt").write_text(gate + "\n")

    # ---- drive split
    didx, drives = drive_index(Path(a.devkit), ktab["fids"])
    sidx, scenes = m3.scene_index(meta, ntab["fids"])
    prov["kitti_drives"] = len(drives); prov["nuscenes_scenes"] = len(scenes)
    prov["frames_per_drive"] = {d: int((didx == i).sum()) for i, d in enumerate(drives)}

    def split_by_drive(n_frames, seed, cfg):
        assert n_frames == len(didx)
        return ORIG_SPLIT(len(drives), seed, cfg)[didx]

    variants = (("(i) frame unit", "frame", ORIG_CELL, ORIG_CELL), ("(ii) drive unit", "drive", m3.scene_cell(didx), m3.scene_cell(sidx)))
    rowsA, rowsB = [], []
    for name, unit, kcell, ncell in variants:
        print(f"drive split, variant {name} ({time.time() - t0:.0f} s)", flush=True)
        rowsA += [dict(r, split="drive", hb_unit=unit) for r in units(part_A(ktab, kign, split_by_drive, kcell))]
        uid = {"kitti": didx, "nuscenes": sidx}; cc = {"kitti": kcell, "nuscenes": ncell}
        rowsB += [dict(r, split="drive (KITTI) / scene (nuScenes)", hb_unit=unit)
                  for r in units(part_B(ktab, kign, ntab, lambda ds, T, cn, ind, seed: unit_cells(T, cn, ind, seed, 0.5, uid[ds], cc[ds])))]
    m6.write_csv(out / "A_kitti_distance_drive.csv", rowsA)
    m6.write_csv(out / "B_dataset_drive.csv", rowsB)

    # ---- drives per part, KITTI distance (seed s) and dataset halves
    parts = {}
    car = kign["cls"] == "Car"
    for seed in m6.SEEDS:
        dc = ORIG_SPLIT(len(drives), seed, m1.CFG)
        parts[f"seed{seed}"] = {p: {"drives": int((dc == pc).sum()), "frames": int((dc[didx] == pc).sum()),
                                    "frames_with_car": int(len(np.unique(kign["fpos"][car & (dc[didx][kign["fpos"]] == pc)])))}
                                for p, pc in (("grid", 0), ("select", 1), ("eval", 2))}
    prov["parts_distance"] = parts
    S = [f"M8 SUMMARY ({SCRIPT_VERSION}): KITTI split by drive; {len(drives)} drives in the {ktab['n_frames']} KITTI validation frames, "
         f"{len(scenes)} nuScenes scenes", gate, ""]
    for title, rows, keys in (("A. KITTI distance", rowsA, ("hb_unit", "protocol", "indicator", "alpha", "established", "applied")),
                              ("B. change of dataset", rowsB, ("hb_unit", "protocol", "indicator", "alpha", "source", "target"))):
        S.append(f"{title}, outcome counts over 5 seeds:")
        t = m6.tally(rows, keys)
        for k in sorted(t, key=str):
            if k[-2] != k[-1]:
                S.append("   " + " ".join(str(x) for x in k) + ": " + ", ".join(f"{o} {n}" for o, n in sorted(t[k].items())))
        S.append("")
    prov["script_sha256"] = m1.sha256(__file__); prov["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "provenance.json").write_text(json.dumps(prov, indent=2, default=str))
    (out / "summary.txt").write_text("\n".join(S)); print("\n".join(S)); print(f"finished in {time.time() - t0:.0f} s; files in {out}")


if __name__ == "__main__":
    main()

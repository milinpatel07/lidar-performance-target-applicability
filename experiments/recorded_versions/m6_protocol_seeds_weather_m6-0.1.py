#!/usr/bin/env python3
"""
m6_protocol_seeds_weather.py (m6-0.1) — three checks the paper needs, in one run.

A. KITTI evaluation-protocol sensitivity. The labels used so far (RUM pipeline, m2) count a car
   detection as wrong when it lies in a KITTI DontCare region or on a Van. The KITTI devkit ignores
   such detections for the Car class [VERIFY against the devkit: a detection is ignored if it matches a
   Van at the matching overlap, or if its 2D box overlaps a DontCare box by more than 0.5 of the
   detection's own area]. Only detections currently labelled wrong can be ignored; ignored detections
   are removed (neither correct nor wrong) and the KITTI range matrix is recomputed. Both versions are
   reported. The KITTI difficulty filter (minimum box height, occlusion, truncation) is NOT applied: it
   changes the population, not the labels.
B. Dataset shift (KITTI <-> nuScenes, cars) over five seeds, with both KITTI label versions.
C. Weather (nuScenes, recorded): rain against clear daytime scenes. A frame's class comes from its
   scene description (no detector output). Night frames and rain-at-night frames are excluded and
   counted. Rain frames contain airborne scatterers and wet road together (C1 and C2 co-occur), so the
   cell is reported as recorded rain, not as one process. Skipped with a message if scene.json and
   sample.json are not reachable.

Needs m1_range_kitti.py, m2_indicators_kitti.py, m3_range_nuscenes.py, m4_dataset_shift.py in the same
folder. Read-only on the inputs; writes only below --out.
"""
import argparse, csv, importlib.util, json, os, pickle, platform, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m4", str(HERE / "m4_dataset_shift.py"))
m4 = importlib.util.module_from_spec(spec); sys.modules["m4"] = m4; spec.loader.exec_module(m4)
m1, m2, m3 = m4.m1, m4.m2, m4.m3          # m4's m1 keeps the KITTI configuration
SCRIPT_VERSION = "m6-0.1"
SEEDS = [0, 1, 2, 3, 4]
ALPHAS = m1.CFG["alphas_frozen"] + m1.CFG["alphas_exploratory"]
IND = ["u_s", "u_e"]


# ------------------------------------------------------------------ geometry helpers
def read_calib(path):
    d = {}
    for line in open(path):
        if ":" in line:
            k, v = line.split(":", 1)
            if v.strip():
                d[k.strip()] = np.array([float(t) for t in v.split()])
    return d["P2"].reshape(3, 4), d["R0_rect"].reshape(3, 3), d["Tr_velo_to_cam"].reshape(3, 4)


def corners3d(b):
    x, y, z, l, w, h, yaw = [float(v) for v in b[:7]]
    c, s = np.cos(yaw), np.sin(yaw)
    dx = np.array([l, l, -l, -l]) / 2; dy = np.array([w, -w, -w, w]) / 2
    xy = np.column_stack([c * dx - s * dy + x, s * dx + c * dy + y])
    return np.vstack([np.column_stack([xy, np.full(4, z - h / 2)]), np.column_stack([xy, np.full(4, z + h / 2)])])


def bbox2d(box, P2, R0, Tr, W=1242.0, H=375.0):
    p = corners3d(box)
    cam = (R0 @ (Tr @ np.hstack([p, np.ones((8, 1))]).T)).T
    if (cam[:, 2] < 0.1).any():
        return None
    img = (P2 @ np.hstack([cam, np.ones((8, 1))]).T).T
    u, v = img[:, 0] / img[:, 2], img[:, 1] / img[:, 2]
    bb = np.array([max(u.min(), 0), max(v.min(), 0), min(u.max(), W), min(v.max(), H)])
    return bb if bb[2] > bb[0] and bb[3] > bb[1] else None


def overlap_of_det(a, b):
    iw = min(a[2], b[2]) - max(a[0], b[0]); ih = min(a[3], b[3]) - max(a[1], b[1])
    if iw <= 0 or ih <= 0:
        return 0.0
    return iw * ih / ((a[2] - a[0]) * (a[3] - a[1]))


# ------------------------------------------------------------------ A. KITTI ignore rule
def build_kitti(rum):
    f_scored = rum / "detections/kitti_v2/scored_val.pkl"; f_cache = rum / "detections/kitti_v2/frame_errors_cache.pkl"
    f_info = rum / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl"
    scored = pickle.load(open(f_scored, "rb")); cache = pickle.load(open(f_cache, "rb"))
    gt, _ = m1.load_gt(f_info, cache["eval_classes"])
    seed_files = sorted((rum / "detections/kitti_v2").glob("seed*_val.pkl"))
    seed_data = [{str(e.get("frame_id", "")): e for e in pickle.load(open(sf, "rb"))} for sf in seed_files]
    tab, fnfp = m2.build(scored, seed_data, gt, m1.CFG["iou_settings"])
    bad, extra = m1.verify_against_cache(fnfp["A_iou0.5"], cache["errors"])
    if bad or extra:
        sys.exit(f"KITTI verification failed ({len(bad)} frames); stopping")
    return tab, scored, seed_data, [f_scored, f_cache, f_info] + list(seed_files)


def kitti_ignore(rum, tab, scored, seed_data):
    info = pickle.load(open(rum / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl", "rb"))
    annos = {}
    for e in info:
        idx = e.get("image_idx") or e.get("point_cloud", {}).get("lidar_idx")
        if idx is not None:
            annos[f"{int(idx):06d}"] = e.get("annos", {})
    n = len(tab["u_s"]); why = np.full(n, "", dtype=object)
    y = tab["y_A_iou0.5"]
    for fpos, fid in enumerate(tab["fids"]):
        rows = np.where((tab["fpos"] == fpos) & (tab["cls"] == "Car"))[0]
        if not len(rows) or not (y[rows] == 0).any():
            continue
        an = annos.get(fid, {}); names = list(an.get("name", [])); boxes = np.asarray(an.get("gt_boxes_lidar", np.zeros((0, 7))))
        bboxes = np.asarray(an.get("bbox", np.zeros((0, 4))), float)
        vans = [np.asarray(boxes[i], np.float32) for i in range(min(len(boxes), len(names))) if names[i] == "Van"]
        dcs = [bboxes[i] for i in range(min(len(bboxes), len(names))) if names[i] == "DontCare"]
        if not vans and not dcs:
            continue
        mdets = [m2.member_detections(sd[fid], scored["min_confidence"]) for sd in seed_data]
        cons = [c for c in m2.consensus_for_frame(mdets, scored["K"], scored["consensus_threshold"], scored["iou_threshold"]) if c["cls"] == "Car"]
        if len(cons) != len(rows) or not np.allclose([c["range"] for c in cons], tab["rng"][rows], atol=1e-4):
            sys.exit(f"frame {fid}: rebuilt car detections do not align with the table")
        P2, R0, Tr = read_calib(rum / f"data/kitti/training/calib/{fid}.txt") if dcs else (None, None, None)
        for k, c in zip(rows, cons):
            if y[k] != 0:
                continue
            box = np.asarray(c["consensus_box"][:7], np.float32)
            if vans and max(m1.rotated_iou_3d(box, v) for v in vans) >= 0.5:
                why[k] = "Van"; continue
            if dcs:
                bb = bbox2d(box, P2, R0, Tr)
                if bb is not None and max(overlap_of_det(bb, d) for d in dcs) > 0.5:
                    why[k] = "DontCare"
    return why


def subset(tab, keep):
    out = {"fids": tab["fids"], "n_frames": tab["n_frames"]}
    for k, v in tab.items():
        if k not in out and isinstance(v, np.ndarray) and len(v) == len(keep):
            out[k] = v[keep]
    return out


# ------------------------------------------------------------------ C. frame-class matrix (weather)
def class_matrix(tab, det_class, ind, seed, alphas, cfg, names=("clear", "rain"), car="car"):
    delta = cfg["delta"]; y = tab["y_A_iou0.5"]
    codes = m1.split_frames(tab["n_frames"], seed, cfg); dcode = codes[tab["fpos"]]
    sel = np.isin(tab["cls"], [car]) & (det_class >= 0)
    grid = np.unique(np.quantile(tab[ind][sel & (dcode == 0)], cfg["grid_levels"]))
    cells = {(s, c): m1.Cell(tab["fpos"][sel & (dcode == sc) & (det_class == c)], tab[ind][sel & (dcode == sc) & (det_class == c)],
                             y[sel & (dcode == sc) & (det_class == c)]) for s, sc in (("select", 1), ("eval", 2)) for c in (0, 1)}
    S = {c: np.array([cells[("select", c)].a_f(t).sum() for t in grid]) for c in (0, 1)}
    rows = []
    for alpha in alphas:
        p = {c: [m1.hb_pvalue(S[c][j], cells[("select", c)].m, alpha) for j in range(len(grid))] for c in (0, 1)}
        tau = {c: (float(grid[j]) if (j := m1.chain_index([p[c]], delta)) >= 0 else None) for c in (0, 1)}
        for c in (0, 1):
            for c2 in (0, 1):
                r = {"indicator": ind, "seed": seed, "alpha": alpha, "established": names[c], "applied": names[c2],
                     "frames_select": cells[("select", c)].m, "frames_eval": cells[("eval", c2)].m}
                if tau[c] is None:
                    r["outcome"] = "no threshold established"
                else:
                    ce = cells[("eval", c2)]; a = ce.a_f(tau[c]); Sx, nx = a.sum(), ce.m
                    U, L = m1.hb_upper(Sx, nx, delta / 2), m1.hb_lower(Sx, nx, delta / 2)
                    r.update({"tau": tau[c], "A_hat": float(Sx / nx) if nx else float("nan"), "hb_L": L, "hb_U": U,
                              "R_hat": ce.retention(tau[c]),
                              "outcome": "applies" if U <= alpha else ("does not apply" if L > alpha else "not determined")})
                rows.append(r)
    au = {}
    for c in (0, 1):
        ce = cells[("eval", c)]
        if len(ce.u) and 0 < ce.y.mean() < 1:
            gid, ng = m1.auroc_groups(-ce.u, ce.y); au[names[c]] = m1.auroc_weighted(gid, ng, ce.y, np.ones(len(ce.u)))
    return rows, au


def nusc_weather_classes(meta_dir, fids):
    samples = json.load(open(meta_dir / "sample.json")); scenes = {s["token"]: s for s in json.load(open(meta_dir / "scene.json"))}
    desc = {s["token"]: scenes[s["scene_token"]].get("description", "") for s in samples}
    cls = np.full(len(fids), -1, int); counts = {"clear_day": 0, "rain_day": 0, "night": 0, "rain_night": 0, "unknown": 0}
    for i, f in enumerate(fids):
        d = desc.get(f)
        if d is None:
            counts["unknown"] += 1; continue
        d = d.lower(); rain, night = "rain" in d, "night" in d
        if rain and night: counts["rain_night"] += 1
        elif night: counts["night"] += 1
        elif rain: cls[i] = 1; counts["rain_day"] += 1
        else: cls[i] = 0; counts["clear_day"] += 1
    return cls, counts


# ------------------------------------------------------------------ main
def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def tally(rows, keys):
    t = {}
    for r in rows:
        k = tuple(r[x] for x in keys); t.setdefault(k, {}); t[k][r["outcome"]] = t[k].get(r["outcome"], 0) + 1
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rum", default="/data/inputs"); ap.add_argument("--out", default="results")
    ap.add_argument("--nusc-meta", default="")
    ap.add_argument("--skip-shift", action="store_true"); ap.add_argument("--skip-weather", action="store_true")
    args = ap.parse_args()
    t0 = time.time(); rum, out = Path(args.rum), Path(args.out); out.mkdir(parents=True, exist_ok=True)
    S = [f"M6 SUMMARY ({SCRIPT_VERSION})", ""]; prov = {"script_version": SCRIPT_VERSION, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                        "python": platform.python_version(), "numpy": np.__version__}

    # A
    print("A: building KITTI table ...", flush=True)
    ktab, kscored, kseed, kin = build_kitti(rum)
    why = kitti_ignore(rum, ktab, kscored, kseed)
    car = ktab["cls"] == "Car"; fp = car & (ktab["y_A_iou0.5"] == 0)
    cut = float(np.quantile(ktab["rng"][car], 0.5)); far = ktab["rng"] > cut
    diag = {z: {"fp": int((fp & m).sum()), "DontCare": int((fp & m & (why == "DontCare")).sum()), "Van": int((fp & m & (why == "Van")).sum())}
            for z, m in (("near", ~far), ("far", far))}
    S += ["A. KITTI ignore rule (DontCare regions, Van as neighbouring class), car detections",
          f"   median car range {cut:.2f} m; false detections and how many the rule ignores:"]
    for z in ("near", "far"):
        d = diag[z]; share = (d["DontCare"] + d["Van"]) / d["fp"] if d["fp"] else 0
        S.append(f"   {z}: FP {d['fp']}, in DontCare {d['DontCare']}, on Van {d['Van']}, share ignored {share:.3f}")
    kign = subset(ktab, why == "")
    rowsA = []
    for proto, T in (("as_run", ktab), ("kitti_ignore", kign)):
        for ind in IND:
            Ti = dict(T); Ti["u"] = T[ind]
            for seed in SEEDS:
                info, res, _ = m1.analyse(Ti, T["y_A_iou0.5"], ["Car"], 0.5, seed, m1.CFG, ALPHAS, boot=False)
                for r in res:
                    for c in r["cells"]:
                        rowsA.append({"protocol": proto, "indicator": ind, "seed": seed, "alpha": r["alpha"], "cut_m": info["cut_m"],
                                      "established": c["established"], "applied": c["applied"], "outcome": c["outcome"],
                                      "A_hat": c.get("A_hat"), "hb_L": c.get("hb_L"), "hb_U": c.get("hb_U"), "R_hat": c.get("R_hat")})
    write_csv(out / "A_kitti_range_protocol.csv", rowsA)
    tA = tally(rowsA, ("protocol", "indicator", "alpha", "established", "applied"))
    S.append("   outcome counts over 5 seeds (KITTI range, car, median cut):")
    for k in sorted(tA):
        if k[3] != k[4]:
            S.append(f"   {k[0]:12s} {k[1]} alpha={k[2]:<7g} {k[3]}->{k[4]}: " + ", ".join(f"{o} {n}" for o, n in sorted(tA[k].items())))
    prov["A"] = {"diagnostics": diag, "median_car_range_m": cut, "ignored_total": int((why != "").sum())}

    # B
    if not args.skip_shift:
        print("B: building nuScenes table (takes about 20 min) ...", flush=True)
        ntab, (_, ncar), nok, ncache, nbad, nin = m4.build_nuscenes(rum)
        if not nok:
            sys.exit(f"nuScenes verification failed ({nbad}/{ncache})")
        rowsB = []
        for proto, KT in (("as_run", ktab), ("kitti_ignore", kign)):
            tables = {"kitti": (KT, "Car"), "nuscenes": (ntab, "car")}
            for ind in IND:
                for seed in SEEDS:
                    cells = {ds: m4.car_cells(T, cn, ind, seed, 0.5) for ds, (T, cn) in tables.items()}
                    for src in ("kitti", "nuscenes"):
                        for tgt in ("kitti", "nuscenes"):
                            for alpha in ALPHAS:
                                tau = m4.establish_tau(cells[src]["select"], np.array(m4.CFG["grid_levels"]), alpha, m1.CFG["delta"])
                                r = {"protocol": proto, "indicator": ind, "seed": seed, "alpha": alpha, "source": src, "target": tgt}
                                if tau is None:
                                    r["outcome"] = "no threshold established"
                                else:
                                    e = m4.evaluate(cells[tgt]["eval"], tau, alpha, m1.CFG["delta"], 200, seed)
                                    r.update({k: e[k] for k in ("tau", "A_hat", "hb_L", "hb_U", "R_hat", "outcome")})
                                rowsB.append(r)
        write_csv(out / "B_shift_seeds_protocol.csv", rowsB)
        tB = tally(rowsB, ("protocol", "indicator", "alpha", "source", "target"))
        S += ["", "B. Dataset shift, car, outcome counts over 5 seeds:"]
        for k in sorted(tB):
            if k[3] != k[4]:
                S.append(f"   {k[0]:12s} {k[1]} alpha={k[2]:<7g} {k[3]}->{k[4]}: " + ", ".join(f"{o} {n}" for o, n in sorted(tB[k].items())))
        kin += nin
    else:
        ntab = None

    # C
    meta = Path(args.nusc_meta) if args.nusc_meta else None
    cands = [meta] if meta else [rum / "data/nuscenes/v1.0-trainval/v1.0-trainval", Path("/data/nuscenes/v1.0-trainval")]
    meta = next((c for c in cands if c and (c / "scene.json").exists() and (c / "sample.json").exists()), None)
    if args.skip_weather or args.skip_shift:
        S += ["", "C. Weather: skipped (needs the nuScenes table from part B)."]
    elif meta is None:
        S += ["", "C. Weather: skipped, scene.json/sample.json not reachable. Mount the nuScenes root at /data/nuscenes."]
    else:
        fcls, counts = nusc_weather_classes(meta, ntab["fids"])
        S += ["", f"C. Weather (nuScenes, recorded), frames by scene description: {counts}"]
        det_class = fcls[ntab["fpos"]]
        rowsC, aus = [], {}
        for ind in IND:
            for seed in SEEDS:
                rr, au = class_matrix(ntab, det_class, ind, seed, ALPHAS, m1.CFG)
                rowsC += rr
                if seed == 0:
                    aus[ind] = au
        write_csv(out / "C_weather_nuscenes.csv", rowsC)
        tC = tally(rowsC, ("indicator", "alpha", "established", "applied"))
        S.append(f"   AUROC on the evaluation split, seed 0: {aus}")
        for k in sorted(tC):
            S.append(f"   {k[0]} alpha={k[1]:<7g} {k[2]}->{k[3]}: " + ", ".join(f"{o} {n}" for o, n in sorted(tC[k].items())))
        r0 = [r for r in rowsC if r["seed"] == 0 and r["alpha"] in (0.05, 0.1) and "A_hat" in r]
        S.append("   seed 0 cells at exploratory alpha (A with interval, retention):")
        for r in r0:
            S.append(f"   {r['indicator']} alpha={r['alpha']} {r['established']}->{r['applied']}: {r['outcome']} | A={r['A_hat']:.3f} "
                     f"[{r['hb_L']:.3f}, {r['hb_U']:.3f}] R={r['R_hat']:.2f} | frames sel/eval {r['frames_select']}/{r['frames_eval']}")
        prov["C"] = {"frame_counts": counts, "meta_dir": str(meta)}

    prov["inputs_sha256"] = {str(f): m1.sha256(f) for f in kin}
    prov["script_sha256"] = m1.sha256(__file__)
    (out / "provenance.json").write_text(json.dumps(prov, indent=2, default=str))
    (out / "summary.txt").write_text("\n".join(S)); print("\n".join(S)); print(f"finished in {time.time() - t0:.0f} s; files in {out}")


if __name__ == "__main__":
    main()

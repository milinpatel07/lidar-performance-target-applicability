#!/usr/bin/env python3
"""
export_tables.py - per-detection tables of both datasets, cached once and exported for split 0.

Uses the analysis code in experiments/ unchanged; no statistic is re-implemented here.
Read-only on the inputs and on results/; writes only below --work (default work/).

  build   rebuild the KITTI and nuScenes per-detection tables (m6.build_kitti, m6.kitti_ignore,
          m4.build_nuscenes, m6.nusc_weather_classes), verify the per-frame false negatives and false
          positives against frame_errors_cache.pkl, and cache them to <work>/cache/tables.pkl
  export  write <work>/data/*.csv and tau_*.json for split 0 and run the checks against the recorded values

Usage:
  python3 tools/export_tables.py build  --rum /data/inputs --nusc-meta /data/nuscenes/v1.0-trainval
  python3 tools/export_tables.py export --kitti-cut m6rule
"""
import argparse, csv, hashlib, importlib.util, json, pickle, sys, time
from pathlib import Path
import numpy as np
import layout

EXPORT_VERSION = "export-1.1 (2026-10-19)"
ALPHA = 0.1
SEED = 0


def load_code(code):
    sys.path.insert(0, str(code))
    spec = importlib.util.spec_from_file_location("m6", str(Path(code) / "m6_protocol_seeds_weather.py"))
    m6 = importlib.util.module_from_spec(spec); sys.modules["m6"] = m6; spec.loader.exec_module(m6)
    return m6


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ build
def cmd_build(a):
    t0 = time.time(); rum, rel = Path(a.rum), Path(a.work)
    (rel / "cache").mkdir(parents=True, exist_ok=True)
    m6 = load_code(a.code); m1, m4 = m6.m1, m6.m4
    print(f"box overlap backend: {m1._resolve_backend()} (m6 default 'auto'; m2/m3/m4 recorded 'clip')", flush=True)
    print("KITTI: rebuild + verification (m6.build_kitti) ...", flush=True)
    ktab, kscored, kseed, kin = m6.build_kitti(rum)            # exits if per-frame FN/FP differ
    print(f"  KITTI frames {ktab['n_frames']}, detections {len(ktab['u_s'])}  ({time.time()-t0:.0f} s)", flush=True)
    why = m6.kitti_ignore(rum, ktab, kscored, kseed)
    print(f"  KITTI rule: {int((why != '').sum())} detections ignored  ({time.time()-t0:.0f} s)", flush=True)
    print("nuScenes: rebuild + verification (m4.build_nuscenes) ...", flush=True)
    ntab, _, nok, ncache, nbad, nin = m4.build_nuscenes(rum)
    if not nok:
        sys.exit(f"ABORT nuScenes verification failed ({nbad}/{ncache} frames differ)")
    print(f"  nuScenes frames {ntab['n_frames']}, detections {len(ntab['u_s'])}  ({time.time()-t0:.0f} s)", flush=True)
    pickle.dump({"ktab": ktab, "why": why, "ntab": ntab}, open(rel / "cache/tables_partial.pkl", "wb"))
    meta = Path(a.nusc_meta)
    if (meta / "sample.json").exists() and (meta / "scene.json").exists():
        wcls, wcounts = m6.nusc_weather_classes(meta, ntab["fids"])
        scene_of = {s["token"]: s["scene_token"] for s in json.load(open(meta / "sample.json"))}
        scene_tok = [scene_of.get(f, "") for f in ntab["fids"]]
    else:      # needed only for the rain setting and the scene split, not for the export
        print(f"nuScenes metadata not reachable at {meta}; weather classes and scene tokens not built", flush=True)
        wcls, wcounts, scene_tok = None, "not available (metadata not reachable)", None
    inputs = {str(f): sha256(f) for f in sorted(set(map(str, kin + nin)))}
    prov = {"export_version": EXPORT_VERSION, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "kitti_verification": f"PASSED for {ktab['n_frames']} frames (m6.build_kitti)",
            "nuscenes_verification": f"PASSED for {ncache} frames (m4.build_nuscenes)",
            "kitti_ignored_total": int((why != "").sum()), "weather_frame_counts": wcounts,
            "inputs_sha256": inputs,
            "code_sha256": {p.name: sha256(p) for p in sorted(Path(a.code).glob("m[1-6]_*.py"))}}
    pickle.dump({"ktab": ktab, "why": why, "ntab": ntab, "wcls": wcls, "scene_tok": scene_tok, "prov": prov},
                open(rel / "cache/tables.pkl", "wb"))
    json.dump(prov, open(rel / "cache/build_provenance.json", "w"), indent=2)
    print(json.dumps(prov, indent=2)); print(f"build finished in {time.time()-t0:.0f} s")


# ------------------------------------------------------------------ export
def write_rows(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def distance_rows(ds, tab, car, cut, codes, excluded):
    dcode = codes[tab["fpos"]]
    idx = np.where((tab["cls"] == car) & (dcode == 2))[0]
    y = tab["y_A_iou0.5"]
    return [{"dataset": ds, "frame": tab["fids"][tab["fpos"][i]],
             "condition": "far" if tab["rng"][i] > cut else "near",
             "u_s": f"{tab['u_s'][i]:.6f}", "u_e": f"{tab['u_e'][i]:.6f}", "correct": int(y[i]),
             "dist_m": f"{tab['rng'][i]:.3f}", "excluded": int(excluded[i])} for i in idx]


def cmd_export(a):
    rel = Path(a.work); (rel / "data").mkdir(parents=True, exist_ok=True)
    m6 = load_code(a.code); m1, m4 = m6.m1, m6.m4
    C = pickle.load(open(rel / "cache/tables.pkl", "rb"))
    ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
    log, fails = [f"{EXPORT_VERSION}  export, kitti-cut = {a.kitti_cut}", ""], []

    def check(name, got, want, tol):
        ok = abs(got - want) <= tol
        log.append(f"{'PASS' if ok else 'FAIL'}  {name}: got {got:.4f}, expected {want} (tol {tol})")
        if not ok:
            fails.append(name)

    # --- check 1: verification and frame counts (the build stage exits on a per-frame mismatch)
    m6prov = json.load(open(layout.RESULTS / "m6_five_splits/provenance.json"))
    log.append(f"PASS  KITTI per-frame FN/FP: {C['prov']['kitti_verification']}")
    log.append(f"PASS  nuScenes per-frame FN/FP: {C['prov']['nuscenes_verification']}")
    check("KITTI frames", ktab["n_frames"], 3769, 0); check("nuScenes frames", ntab["n_frames"], 6019, 0)
    same = all(C["prov"]["inputs_sha256"].get(k) == v for k, v in m6prov["inputs_sha256"].items())
    log.append(f"{'PASS' if same else 'FAIL'}  input files sha256 equal to m6 provenance ({len(m6prov['inputs_sha256'])} files)")
    if not same: fails.append("inputs sha256")
    check("KITTI rule: ignored detections vs m6 provenance", int((why != '').sum()), m6prov["A"]["ignored_total"], 0)

    # --- check 2: median u_s of cars, all detections
    kcar, ncar = ktab["cls"] == "Car", ntab["cls"] == "car"
    check("median u_s, KITTI cars, all detections", float(np.median(ktab["u_s"][kcar])), 0.187, 0.0005)
    check("median u_s, nuScenes cars, all detections", float(np.median(ntab["u_s"][ncar])), 0.256, 0.0005)

    # --- distance setting, split 0: m1.analyse as in m2 (KITTI, as run), m6 (KITTI rule), m3 (nuScenes)
    def run(tab, car, analyse_mod):
        T = dict(tab); T["u"] = tab["u_s"]
        return analyse_mod.analyse(T, tab["y_A_iou0.5"], [car], 0.5, SEED, analyse_mod.CFG, [ALPHA], boot=False)
    k_info, k_res, _ = run(ktab, "Car", m1)                                  # = m2 primary, seed 0
    kign = m6.subset(ktab, why == "")
    r_info, r_res, _ = run(kign, "Car", m1)                                  # = m6 kitti_ignore, seed 0
    n_info, n_res, _ = run(ntab, "car", m6.m3.m1)                            # = m3 primary, seed 0
    check("AUROC u_s KITTI near (split 0, as run)", k_info["auroc_eval"]["near"]["auroc"], 0.896, 0.0005)
    check("AUROC u_s KITTI far (split 0, as run)", k_info["auroc_eval"]["far"]["auroc"], 0.834, 0.0005)
    check("AUROC u_s nuScenes near (split 0)", n_info["auroc_eval"]["near"]["auroc"], 0.7295, 0.0001)   # recorded 0.729491
    check("AUROC u_s nuScenes far (split 0)", n_info["auroc_eval"]["far"]["auroc"], 0.655, 0.0005)
    check("nuScenes cut (m)", n_info["cut_m"], 21.4, 0.005)
    check("KITTI cut, m2 split 0 (m)", k_info["cut_m"], 35.68486713209648, 1e-9)
    check("KITTI cut, m6 kitti_ignore split 0 (m)", r_info["cut_m"], 34.805719918803426, 1e-9)
    log.append(f"INFO  KITTI median car range over all frames (m6 provenance A): {m6prov['A']['median_car_range_m']:.3f} m; "
               f"recomputed {float(np.quantile(ktab['rng'][kcar], 0.5)):.3f} m")
    log.append(f"INFO  KITTI rule applied: AUROC u_s near {r_info['auroc_eval']['near']['auroc']:.4f}, "
               f"far {r_info['auroc_eval']['far']['auroc']:.4f} (split 0, cut {r_info['cut_m']:.3f} m)")
    log.append(f"INFO  frames per class, split 0 (select/eval): KITTI as run {k_info['classes']}; "
               f"KITTI rule {r_info['classes']}; nuScenes {n_info['classes']}")

    # --- write distance CSVs and tau JSONs
    if a.kitti_cut == "m6rule":
        kc, kr = r_info["cut_m"], r_res[0]; ksrc = "m6 kitti_ignore, split 0 (rule applied before the split analysis)"
    else:
        kc, kr = k_info["cut_m"], k_res[0]; ksrc = "m2 primary, split 0 (labels as run, rule not applied)"
    excl = (why != "").astype(int)
    kcodes = m1.split_frames(ktab["n_frames"], SEED, m1.CFG)
    ncodes = m6.m3.m1.split_frames(ntab["n_frames"], SEED, m6.m3.m1.CFG)
    write_rows(rel / "data/kitti_distance_split0.csv", distance_rows("KITTI", ktab, "Car", kc, kcodes, excl))
    write_rows(rel / "data/nuscenes_distance_split0.csv",
               distance_rows("nuScenes", ntab, "car", n_info["cut_m"], ncodes, np.zeros(len(ntab["u_s"]), int)))
    json.dump({"alpha": ALPHA, "indicator": "u_s", "cut_m": round(kc, 3), "tau": kr["tau"] | {},
               "source": ksrc}, open(rel / "data/tau_kitti_distance_split0.json", "w"), indent=1)
    json.dump({"alpha": ALPHA, "indicator": "u_s", "cut_m": round(n_info["cut_m"], 3), "tau": n_res[0]["tau"] | {},
               "source": "m3 primary, split 0"}, open(rel / "data/tau_nuscenes_distance_split0.json", "w"), indent=1)
    log.append(f"INFO  tau KITTI ({ksrc}): {kr['tau']}, cut {kc:.3f} m")
    log.append(f"INFO  tau nuScenes (m3, split 0): {n_res[0]['tau']}, cut {n_info['cut_m']:.3f} m")

    # --- dataset setting: all car detections of all frames; part = m4 split 0 (select/eval)
    taus = {}
    for ds, tab, car, ex in (("KITTI", ktab, "Car", excl), ("nuScenes", ntab, "car", np.zeros(len(ntab["u_s"]), int))):
        rng = np.random.default_rng(SEED); codes = np.zeros(tab["n_frames"], np.int8)
        codes[rng.permutation(tab["n_frames"])[: int(round(m4.CFG["frac_select"] * tab["n_frames"]))]] = 1
        idx = np.where(tab["cls"] == car)[0]
        write_rows(rel / f"data/{ds.lower()}_all.csv",
                   [{"dataset": ds, "frame": tab["fids"][tab["fpos"][i]], "condition": "all",
                     "u_s": f"{tab['u_s'][i]:.6f}", "u_e": f"{tab['u_e'][i]:.6f}", "correct": int(tab["y_A_iou0.5"][i]),
                     "dist_m": f"{tab['rng'][i]:.3f}", "excluded": int(ex[i]),
                     "part": "select" if codes[tab["fpos"][i]] == 1 else "eval"} for i in idx])
        cells = m4.car_cells(tab, car, "u_s", SEED, m4.CFG["frac_select"])
        taus[ds] = m4.establish_tau(cells["select"], np.array(m4.CFG["grid_levels"]), ALPHA, m1.CFG["delta"])
    cells_r = m4.car_cells(kign, "Car", "u_s", SEED, m4.CFG["frac_select"])
    taus["KITTI_rule"] = m4.establish_tau(cells_r["select"], np.array(m4.CFG["grid_levels"]), ALPHA, m1.CFG["delta"])
    check("T_K, dataset setting, u_s, alpha 0.1, split 0 (m6 B as_run: 0.12)", taus["KITTI"], 0.12, 1e-9)
    check("T_N, dataset setting, u_s, alpha 0.1, split 0 (m6 B: 0.20)", taus["nuScenes"], 0.20, 1e-9)
    log.append(f"INFO  T_K with KITTI rule (m6 B kitti_ignore: 0.14): {taus['KITTI_rule']}")
    json.dump(taus, open(rel / "data/tau_dataset_split0.json", "w"), indent=1)

    log += ["", "ABORT: " + ", ".join(fails) if fails else "ALL CHECKS PASSED"]
    (rel / "export_checks.txt").write_text("\n".join(log)); print("\n".join(log))
    sys.exit(3 if fails else 0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=EXPORT_VERSION); sp = p.add_subparsers(dest="cmd")
    b = sp.add_parser("build"); b.add_argument("--rum", default=str(layout.RUM))
    b.add_argument("--nusc-meta", default=str(layout.NUSC_META))
    e = sp.add_parser("export"); e.add_argument("--kitti-cut", choices=["m6rule", "m2"], required=True)
    for q in (b, e):
        q.add_argument("--code", default=str(layout.ANALYSIS)); q.add_argument("--work", default=str(layout.WORK))
    a = p.parse_args()
    {"build": cmd_build, "export": cmd_export}.get(a.cmd, lambda _: p.print_help())(a)

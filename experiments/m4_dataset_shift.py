#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m4_dataset_shift.py

Dataset-shift applicability. The within-dataset runs (m2 KITTI, m3 nuScenes) ask
whether a threshold established in one range class holds in another range class of
the SAME dataset. This script asks the harder, more operationally relevant question:

  A rejection threshold established on the whole of one dataset (KITTI), does it
  still keep the false acceptance proportion at or below alpha on the whole of
  another dataset (nuScenes), and in reverse?

This is the extrapolation a safety case makes when evidence gathered with one
sensor, in one city, is carried to another. Here the two detectors were trained
separately, so the shift bundles several causes at once: sensor (KITTI 64-beam
forward, nuScenes 32-beam 360 degrees), scene and city, and class distribution.
The paper must state that this cell measures their combined effect, not a single
isolated cause. The threshold is carried as a RAW indicator value, with no
rescaling, because rescaling would hide the mismatch a safety team needs to see.
The indicator-value quantiles of each dataset are reported so the scale difference
is visible.

Only the shared class is used: car (KITTI 'Car', nuScenes 'car').

Design decisions (logged in decisions_m4.md):
  D-shift-1  the unit is the whole dataset, not a range class; tau is established
             on the selection split of the source dataset and evaluated on the
             evaluation split of the target dataset.
  D-shift-2  threshold carried raw; scale reported, not corrected.
  D-shift-3  empty-frame convention: a_f = 0 for frames with no accepted car
             detection (same as the within-dataset runs).
  D-shift-4  u_s = 1 - mean pairwise rotated IoU (VEHITS Eq. 3);
             u_e = 1 - mean confidence over K members (VEHITS Eq. 1).

Imports the tested statistics from m1_range_kitti.py, the KITTI builder from
m2_indicators_kitti.py, and the nuScenes builder from m3_range_nuscenes.py.
All four files must sit in the same folder.

Usage (inside the container):
  python3 m4_dataset_shift.py --selftest
  python3 m4_dataset_shift.py --rum /data/inputs --out /data/work/m4_dataset_shift/results

Inputs (read-only): the KITTI and nuScenes detection files used by m2 and m3.
Outputs: only below --out.
"""
import argparse
import csv
import importlib.util
import json
import pickle
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, str(HERE / filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


m1 = _load("m1", "m1_range_kitti.py")
m2 = _load("m2", "m2_indicators_kitti.py")
m3 = _load("m3", "m3_range_nuscenes.py")

SCRIPT_VERSION = "m4-0.1"

CFG = {
    "delta": 0.05,
    "alphas_frozen": [1e-2, 1e-3, 1e-4],
    "alphas_exploratory": [5e-2, 1e-1],
    "frac_select": 0.5,          # half of each dataset's frames establish tau, half evaluate
    "grid_levels": [round(0.01 * i, 2) for i in range(1, 101)],
    "n_boot": 2000,
    "seed": 0,
    "indicators": ["u_s", "u_e"],
}
DATASETS = ["kitti", "nuscenes"]


# ----------------------------------------------------------------------------
# Build the per-detection table for one dataset, restricted to cars, using the
# already-tested builders. Returns per-detection frame index, u_s, u_e, y.
# ----------------------------------------------------------------------------
def build_kitti(rum):
    f_scored = rum / "detections/kitti_v2/scored_val.pkl"
    f_cache = rum / "detections/kitti_v2/frame_errors_cache.pkl"
    f_info = rum / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl"
    scored = pickle.load(open(f_scored, "rb"))
    cache = pickle.load(open(f_cache, "rb"))
    gt, _ = m1.load_gt(f_info, cache["eval_classes"])
    seed_files = sorted((rum / "detections/kitti_v2").glob("seed*_val.pkl"))
    seed_data = [{str(e.get("frame_id", "")): e for e in pickle.load(open(sf, "rb"))} for sf in seed_files]
    tab, fnfp = m2.build(scored, seed_data, gt, m1.CFG["iou_settings"])
    bad, extra = m1.verify_against_cache(fnfp["A_iou0.5"], cache["errors"])
    ok = not (bad or extra)
    inputs = [f_scored, f_cache, f_info] + list(seed_files)
    return tab, ("A_iou0.5", "Car"), ok, len(cache["errors"]), len(bad), inputs


def build_nuscenes(rum):
    f_scored = rum / "detections/nuscenes/scored_val.pkl"
    f_cache = rum / "detections/nuscenes/frame_errors_cache.pkl"
    f_info = rum / "data/nuscenes/v1.0-trainval/nuscenes_infos_10sweeps_val.pkl"
    scored = pickle.load(open(f_scored, "rb"))
    cache = pickle.load(open(f_cache, "rb"))
    gt = m3.load_gt_nuscenes(f_info, cache["eval_classes"])
    seed_files = sorted((rum / "detections/nuscenes").glob("seed*_val.pkl"))
    seed_data = [{m3._entry_token(e): e for e in pickle.load(open(sf, "rb"))} for sf in seed_files]
    iou_settings = {"A_iou0.5": {c: 0.5 for c in m3.NUSC_CLASSES}}
    tab, fnfp = m3.build(scored, seed_data, gt, iou_settings)
    bad, extra = m1.verify_against_cache(fnfp["A_iou0.5"], cache["errors"])
    ok = not (bad or extra)
    inputs = [f_scored, f_cache, f_info] + list(seed_files)
    return tab, ("A_iou0.5", "car"), ok, len(cache["errors"]), len(bad), inputs


def car_cells(tab, car_name, ind, seed, frac_select):
    """Split the dataset's frames into selection and evaluation halves (by frame, fixed
    seed). Return a selection Cell and an evaluation Cell over car detections only, with
    the chosen indicator as u."""
    sel_mask = np.isin(tab["cls"], [car_name])
    nF = tab["n_frames"]
    rng = np.random.default_rng(seed)
    codes = np.zeros(nF, dtype=np.int8)
    codes[rng.permutation(nF)[: int(round(frac_select * nF))]] = 1   # 1 = selection, 0 = evaluation
    dcode = codes[tab["fpos"]]
    out = {}
    for name, c in (("select", 1), ("eval", 0)):
        m = sel_mask & (dcode == c)
        out[name] = m1.Cell(tab["fpos"][m], tab[ind][m], tab["y_A_iou0.5"][m])
    return out


def establish_tau(cell_sel, grid, alpha, delta):
    """Largest grid threshold whose selection-split false acceptance proportion is
    certified at or below alpha by the Hoeffding-Bentkus fixed sequence."""
    S = np.array([cell_sel.a_f(t).sum() for t in grid])
    p = [m1.hb_pvalue(S[j], cell_sel.m, alpha) for j in range(len(grid))]
    j = m1.chain_index([p], delta)
    return (float(grid[j]) if j >= 0 else None)


def evaluate(cell_eval, tau, alpha, delta, n_boot, seed):
    a = cell_eval.a_f(tau)
    S, n = a.sum(), cell_eval.m
    U, L = m1.hb_upper(S, n, delta / 2), m1.hb_lower(S, n, delta / 2)
    outcome = "applies" if U <= alpha else ("does not apply" if L > alpha else "not determined")
    res = {"tau": tau, "A_hat": float(S / n) if n else float("nan"), "hb_L": L, "hb_U": U,
           "outcome": outcome, "R_hat": cell_eval.retention(tau), "n_eval_frames": n}
    if n > 0:
        W = np.random.default_rng(seed + 7).multinomial(n, np.full(n, 1.0 / n), size=n_boot)
        Ab = W @ a / n
        res["boot_lo"], res["boot_hi"] = [float(v) for v in np.percentile(Ab, [100 * delta / 2, 100 * (1 - delta / 2)])]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rum", default="/data/inputs")
    ap.add_argument("--out", default="results")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--bev", choices=["auto", "shapely", "clip"], default="auto")
    args = ap.parse_args()
    m1.BEV_BACKEND = args.bev
    if args.selftest:
        sys.exit(0 if selftest() else 1)

    t0 = time.time()
    rum, out = Path(args.rum), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"box overlap backend: {m1._resolve_backend()}")

    tables, meta, inputs_all = {}, {}, []
    for ds, builder in (("kitti", build_kitti), ("nuscenes", build_nuscenes)):
        print(f"building {ds} table ...", flush=True)
        tab, (iou, car), ok, n_cache, n_bad, inputs = builder(rum)
        print(f"  {ds}: {tab['n_frames']} frames, {int(len(tab['u_s']))} detections, "
              f"verify {'PASSED' if ok else f'FAILED ({n_bad}/{n_cache})'}")
        if not ok:
            (out / "verification_failed.txt").write_text(f"{ds} verification failed: {n_bad}/{n_cache}")
            sys.exit(2)
        tables[ds] = tab
        meta[ds] = {"car_name": car, "n_frames": tab["n_frames"], "n_detections": int(len(tab["u_s"]))}
        inputs_all += inputs

    delta = CFG["delta"]
    grid = np.array(CFG["grid_levels"])
    alphas = CFG["alphas_frozen"] + CFG["alphas_exploratory"]

    # indicator-value quantiles per dataset per indicator (the scale difference, reported)
    scales = {}
    for ds in DATASETS:
        car = meta[ds]["car_name"]
        m = np.isin(tables[ds]["cls"], [car])
        scales[ds] = {ind: {str(q): float(np.quantile(tables[ds][ind][m], q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
                      for ind in CFG["indicators"]}

    rows = []
    for ind in CFG["indicators"]:
        cells = {ds: car_cells(tables[ds], meta[ds]["car_name"], ind, CFG["seed"], CFG["frac_select"]) for ds in DATASETS}
        for src in DATASETS:
            for tgt in DATASETS:
                for alpha in alphas:
                    tau = establish_tau(cells[src]["select"], grid, alpha, delta)
                    if tau is None:
                        rows.append({"indicator": ind, "source": src, "target": tgt, "alpha": alpha,
                                     "frozen": alpha in CFG["alphas_frozen"], "tau": None,
                                     "outcome": "no threshold established"})
                        continue
                    r = evaluate(cells[tgt]["eval"], tau, alpha, delta, CFG["n_boot"], CFG["seed"])
                    rows.append({"indicator": ind, "source": src, "target": tgt, "alpha": alpha,
                                 "frozen": alpha in CFG["alphas_frozen"], **r})

    with open(out / "shift_matrix.csv", "w", newline="") as f:
        cols = ["indicator", "source", "target", "alpha", "frozen", "tau", "A_hat", "hb_L", "hb_U",
                "boot_lo", "boot_hi", "outcome", "R_hat", "n_eval_frames"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

    prov = {"script_version": SCRIPT_VERSION, "bev_backend": m1._resolve_backend(),
            "started": time.strftime("%Y-%m-%d %H:%M:%S"), "python": platform.python_version(),
            "numpy": np.__version__, "m1_version": m1.SCRIPT_VERSION, "m2_version": m2.SCRIPT_VERSION,
            "m3_version": m3.SCRIPT_VERSION, "config": CFG, "meta": meta,
            "indicator_value_quantiles_car": scales,
            "inputs_sha256": {str(f): m1.sha256(f) for f in inputs_all}}
    (out / "provenance.json").write_text(json.dumps(prov, indent=2))

    # summary
    L = ["M4 SUMMARY  dataset-shift applicability (car only, threshold carried raw)",
         "A threshold established on the SOURCE dataset, evaluated on the TARGET dataset.",
         "within-dataset cells (source == target) are the baseline; cross cells are the shift.", ""]
    L.append("indicator-value quantiles for car (shows the scale difference between datasets):")
    for ind in CFG["indicators"]:
        L.append(f"  {ind}:")
        for ds in DATASETS:
            qs = scales[ds][ind]
            L.append(f"    {ds:9s} 5/25/50/75/95% = " + " / ".join(m1.fmt(qs[str(q)]) for q in (0.05, 0.25, 0.5, 0.75, 0.95)))
    L.append("")
    for ind in CFG["indicators"]:
        L.append("=" * 70)
        L.append(f"INDICATOR {ind}")
        for alpha in alphas:
            tag = "frozen" if alpha in CFG["alphas_frozen"] else "EXPLORATORY"
            L.append(f"  alpha = {alpha:g}  [{tag}]")
            for src in DATASETS:
                for tgt in DATASETS:
                    r = next(x for x in rows if x["indicator"] == ind and x["source"] == src
                             and x["target"] == tgt and x["alpha"] == alpha)
                    arrow = f"{src} -> {tgt}"
                    if r.get("tau") is None:
                        L.append(f"    {arrow:22s}: no threshold established")
                    else:
                        kind = "within" if src == tgt else "SHIFT"
                        L.append(f"    {arrow:22s} [{kind}]: {r['outcome']} | tau={m1.fmt(r['tau'],5)} "
                                 f"A={m1.fmt(r['A_hat'])} HB[{m1.fmt(r['hb_L'])}, {m1.fmt(r['hb_U'])}] "
                                 f"| R={m1.fmt(r['R_hat'])} | n_eval={r['n_eval_frames']}")
        L.append("")
    text = "\n".join(L)
    (out / "summary.txt").write_text(text)
    print(text)
    print(f"finished in {time.time() - t0:.0f} s; files in {out}")


def selftest():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail else ""))
        ok = ok and cond

    if not m2.selftest():
        print("m2 selftest failed; fix it first")
        return False

    # synthetic: two "datasets" with the SAME indicator scale but different FP prevalence.
    # A threshold from the clean dataset should transfer to the clean one and fail on the dirty one.
    def synth(n_frames, p_fp, seed):
        rng = np.random.default_rng(seed)
        fpos, u, y = [], [], []
        for f in range(n_frames):
            k = rng.integers(3, 9)
            yy = (rng.uniform(size=k) > p_fp).astype(np.uint8)
            uu = np.where(yy == 1, rng.beta(2, 20, size=k), rng.beta(6, 6, size=k))  # correct low u, wrong high u
            fpos.append(np.full(k, f)); u.append(uu); y.append(yy)
        tab = {"n_frames": n_frames, "fpos": np.concatenate(fpos),
               "u_s": np.concatenate(u), "u_e": np.concatenate(u),
               "cls": np.full(sum(len(x) for x in u), "car"),
               "y_A_iou0.5": np.concatenate(y)}
        return tab

    clean = synth(4000, 0.15, 1)
    dirty = synth(4000, 0.55, 2)
    grid = np.array(CFG["grid_levels"])
    cl = car_cells(clean, "car", "u_s", 0, 0.5)
    di = car_cells(dirty, "car", "u_s", 0, 0.5)
    tau = establish_tau(cl["select"], grid, 0.05, 0.05)
    check("a threshold is established on the clean source", tau is not None, f"tau={tau}")
    if tau is not None:
        r_same = evaluate(cl["eval"], tau, 0.05, 0.05, 200, 0)
        r_shift = evaluate(di["eval"], tau, 0.05, 0.05, 200, 0)
        check("clean->clean does not report 'does not apply'", r_same["outcome"] != "does not apply",
              r_same["outcome"])
        check("clean->dirty admits more false acceptances than clean->clean",
              r_shift["A_hat"] > r_same["A_hat"], f"{r_shift['A_hat']:.3f} vs {r_same['A_hat']:.3f}")

    print("M4 SELFTEST " + ("PASSED" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    main()

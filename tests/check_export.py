#!/usr/bin/env python3
"""check_export.py - independent check of the export of export_tables.py: AUROC, A and R recomputed from the
exported CSVs with the functions of tools/figures/make_figures.py (not with the m1 analysis code that wrote them).

Usage: python3 tests/check_export.py   (after export_tables.py build and export)"""
import json, sys
from pathlib import Path
import pandas as pd
TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS)); sys.path.insert(0, str(TOOLS / "figures")); import make_figures as mf
import layout

M2_CUT = 35.68486713209648
WANT = {("KITTI", "near"): 0.896, ("KITTI", "far"): 0.834, ("nuScenes", "near"): 0.729, ("nuScenes", "far"): 0.655}
k = pd.read_csv(layout.WORK / "data/kitti_distance_split0.csv", dtype={"frame": str})
n = pd.read_csv(layout.WORK / "data/nuscenes_distance_split0.csv", dtype={"frame": str})
fails = []
for ds, df, cond in (("KITTI", k, {"near": k.dist_m <= M2_CUT, "far": k.dist_m > M2_CUT}),
                     ("nuScenes", n, {"near": n.condition == "near", "far": n.condition == "far"})):
    for c, m in cond.items():
        _, _, auc = mf.roc(df[m], "u_s"); ok = round(auc, 3) == WANT[(ds, c)]
        fails += [] if ok else [f"{ds} {c}"]
        print(f"{'PASS' if ok else 'FAIL'}  AUROC u_s {ds} {c} (labels as run{', m2 cut' if ds == 'KITTI' else ''}): "
              f"{auc:.6f} -> {round(auc, 3)} vs {WANT[(ds, c)]}")
d = k[k.excluded == 0]
for c in ("near", "far"):
    _, _, auc = mf.roc(d[d.condition == c], "u_s"); print(f"INFO  AUROC u_s KITTI rule {c} (cut 34.806): {auc:.6f}")
t = json.load(open(layout.WORK / "data/tau_kitti_distance_split0.json"))["tau"]
for e in ("near", "far"):
    for a in ("near", "far"):
        s = d[d.condition == a]
        A = mf.frame_fap(s, "u_s", t[e]).mean()
        R = ((s.u_s <= t[e]) & (s.correct == 1)).sum() / (s.correct == 1).sum()
        print(f"INFO  KITTI rule u_s alpha 0.1 {e}->{a}: A {A:.6f}  R {R:.6f}  frames {s.frame.nunique()}")
print("ALL CHECKS PASSED" if not fails else "ABORT: " + ", ".join(fails))

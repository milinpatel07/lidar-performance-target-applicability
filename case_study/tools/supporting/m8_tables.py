#!/usr/bin/env python3
"""m8_tables.py (from v25n-0.1, 2026-10-19; paths adapted to the repository layout) - two tables of the division by
recorded KITTI drive (m8), KITTI rule.

  counts  -> work/supporting_analyses/m8_outcome_counts.csv: outcome counts over the five splits per cell, from
             results/division_by_sequence/kitti_by_drive/A_kitti_distance_drive.csv and B_dataset_drive.csv only (no data needed).
  drives  -> work/supporting_analyses/m8_drives_per_part.csv: drives and frames with a car detection per part and
             condition; needs work/cache/tables.pkl and the KITTI devkit mapping files (option --devkit).
Compare the outputs with results/supporting_analyses/.

Usage, from case_study/:
  python3 tools/supporting/m8_tables.py counts
  python3 tools/supporting/m8_tables.py drives --devkit /data/kitti_devkit
"""
import argparse, pickle, sys
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import layout

OUT = layout.WORK / "supporting_analyses"


def counts():
    M8 = layout.RESULTS / "division_by_sequence/kitti_by_drive"
    rows = []
    for f, key in (("A_kitti_distance_drive.csv", ("established", "applied")), ("B_dataset_drive.csv", ("source", "target"))):
        d = pd.read_csv(M8 / f)
        d = d[d.protocol == "kitti_ignore"]
        for (unit, ind, a, src, dst), g in d.groupby(["hb_unit", "indicator", "alpha", key[0], key[1]]):
            c = Counter(g.outcome)
            rows.append({"setting": "KITTI distance" if f.startswith("A") else "change of dataset", "division": "by drive",
                         "unit": "frame" if unit == "frame" else "drive", "indicator": ind, "alpha": a, "direction": f"{src} -> {dst}",
                         "applicable": c["applies"], "not_applicable": c["does not apply"], "not_determined": c["not determined"],
                         "no_threshold": c["no threshold established"]})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "m8_outcome_counts.csv", index=False, lineterminator=chr(10))
    print(f"wrote {OUT / 'm8_outcome_counts.csv'} ({len(rows)} rows)")


def drives(devkit):
    m6 = layout.load_analysis(); m1 = m6.m1
    C = pickle.load(open(layout.CACHE, "rb")); ktab, why = C["ktab"], C["why"]
    kign = m6.subset(ktab, why == "")
    mp = Path(devkit) / "mapping"
    rand = [int(v) for v in (mp / "train_rand.txt").read_text().strip().split(",")]
    mapping = [l.split() for l in (mp / "train_mapping.txt").read_text().splitlines() if l.strip()]
    drv = [mapping[rand[int(f)] - 1][1] for f in ktab["fids"]]; dr = sorted(set(drv)); didx = np.array([dr.index(d) for d in drv])
    kc = kign["cls"] == "Car"; cnt_rows = []
    for seed in range(5):
        dc = m1.split_frames(len(dr), seed, m1.CFG)[didx][kign["fpos"]]
        cut = float(np.quantile(kign["rng"][kc & (dc == 0)], 0.5))
        for p, pc in (("grid", 0), ("select", 1), ("eval", 2)):
            for cond, cm in (("near", kign["rng"] <= cut), ("far", kign["rng"] > cut)):
                m = kc & (dc == pc) & cm
                cnt_rows.append({"setting": "KITTI distance", "seed": seed, "part": p, "condition": cond, "cut_m": round(cut, 3),
                                 "drives": int(len(np.unique(didx[kign["fpos"][m]]))), "frames": int(len(np.unique(kign["fpos"][m])))})
        rng = np.random.default_rng(seed); codes = np.zeros(len(dr), np.int8)
        codes[rng.permutation(len(dr))[: int(round(0.5 * len(dr)))]] = 1
        for p, pc in (("select", 1), ("eval", 0)):
            m = kc & (codes[didx][kign["fpos"]] == pc)
            cnt_rows.append({"setting": "change of dataset (KITTI side)", "seed": seed, "part": p, "condition": "KITTI", "cut_m": "",
                             "drives": int(len(np.unique(didx[kign["fpos"][m]]))), "frames": int(len(np.unique(kign["fpos"][m])))})
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(cnt_rows).to_csv(OUT / "m8_drives_per_part.csv", index=False, lineterminator=chr(10))
    print(f"wrote {OUT / 'm8_drives_per_part.csv'} ({len(cnt_rows)} rows)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=["counts", "drives"]); ap.add_argument("--devkit", default="")
    a = ap.parse_args()
    counts() if a.what == "counts" else drives(a.devkit)

"""Count applicability outcomes over every cell, variant and seed of the runs.

Reads the per-cell result files written by m2, m3 and m4 and writes
work/outcome_counts.csv and work/failing_cells_primary.csv. No statistics are recomputed; each row
of a result file is one cell (established class -> applied class) for one
indicator, overlap setting, object set, cut, seed and target.

Usage: python3 tools/outcome_counts.py   (compare with results/outcome_counts.csv)
"""
import csv
import os
from collections import Counter

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
OUT = os.environ.get("WORK_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work"))
RUNS = {
    "m2_kitti_range": "m2_indicators_kitti/matrix_all_variants.csv",
    "m3_nuscenes_range": "m3_range_nuscenes/matrix_all_variants.csv",
    "m4_dataset_shift": "m4_dataset_shift/shift_matrix.csv",
}
OUTCOMES = ["applies", "does not apply", "not determined", "no threshold established"]
FROZEN = {0.01: "frozen 1e-2", 0.001: "frozen <=1e-3", 0.0001: "frozen <=1e-3"}


def cell_kind(row):
    if "established" in row:
        src, dst = row["established"], row["applied"]
    else:
        src, dst = row["source"], row["target"]
    return "diagonal" if src == dst else "off-diagonal"


def main():
    counts = Counter()
    for run, rel in RUNS.items():
        with open(os.path.join(HERE, rel), newline="") as fh:
            for row in csv.DictReader(fh):
                group = FROZEN.get(float(row["alpha"]), "exploratory")
                counts[(run, group, cell_kind(row), row["outcome"])] += 1
    os.makedirs(OUT, exist_ok=True); out = os.path.join(OUT, "outcome_counts.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "target_group", "cell", *OUTCOMES, "total"])
        keys = sorted({k[:3] for k in counts})
        for key in keys:
            row = [counts[(*key, o)] for o in OUTCOMES]
            w.writerow([*key, *row, sum(row)])
    print("wrote", out)
    failing_primary()


# Primary variant of each range run (provenance.json, config "primary").
PRIMARY = {"iou": "A_iou0.5", "cut_q": "0.5", "seed": "0"}
PRIMARY_OBJECTS = {"m2_kitti_range": "Car", "m3_nuscenes_range": "car"}


def failing_primary():
    """Write every off-diagonal 'does not apply' cell of the primary variants."""
    out = os.path.join(OUT, "failing_cells_primary.csv")
    cols = ["run", "indicator", "alpha", "source", "target", "A_hat", "hb_L", "hb_U", "R_hat"]
    with open(out, "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(cols)
        for run, rel in RUNS.items():
            with open(os.path.join(HERE, rel), newline="") as fh:
                for r in csv.DictReader(fh):
                    if cell_kind(r) != "off-diagonal" or r["outcome"] != "does not apply":
                        continue
                    if run in PRIMARY_OBJECTS:
                        if r["objects"] != PRIMARY_OBJECTS[run] or any(r[k] != v for k, v in PRIMARY.items()):
                            continue
                        src, dst = r["established"], r["applied"]
                    else:
                        src, dst = r["source"], r["target"]
                    w.writerow([run, r["indicator"], r["alpha"], src, dst,
                                r["A_hat"], r["hb_L"], r["hb_U"], r["R_hat"]])
    print("wrote", out)


if __name__ == "__main__":
    main()

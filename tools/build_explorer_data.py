"""Write explorer/data/outcomes.json, the data of the results explorer, from the recorded result files.

Every record is one cell (pair of conditions, condition of selection, condition of use, indicator, limit α, split) of
one division of the data, with the file and line it was read from. Before writing, the frame-division counts are
compared with the table "Outcomes over the five splits" of docs/results.md; the script stops if they differ.

    python tools/build_explorer_data.py              # write explorer/data/outcomes.json
    python tools/build_explorer_data.py --check      # exit 1 if the committed file differs from a fresh build
    python tools/build_explorer_data.py --root PATH  # read results/ and docs/ of another copy of the repository

The output depends only on the input files: keys are sorted, the order of records is fixed, the date is a constant.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

GENERATOR_VERSION = "explorer-data-1.0"
DATA_DATE = "2026-10-21"  # constant so that a rebuild gives the same bytes
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = SCRIPT_ROOT / "explorer" / "data" / "outcomes.json"

M6A = "results/m6_protocol_seeds_weather/A_kitti_range_protocol.csv"
M6B = "results/m6_protocol_seeds_weather/B_shift_seeds_protocol.csv"
M7 = "results/m7_scene_split/m7_scene_split.csv"
M8A = "results/m8_kitti_drive_split/A_kitti_distance_drive.csv"
M8B = "results/m8_kitti_drive_split/B_dataset_drive.csv"
POST = "results/post_hoc/outcomes.csv"
SOURCES = [M6A, M6B, M7, M8A, M8B, POST]

OUTCOME = {"applies": "applicable", "applicable": "applicable",
           "does not apply": "not applicable", "not applicable": "not applicable",
           "not determined": "not determined",
           "no threshold established": "no threshold selected", "no threshold selected": "no threshold selected"}
CODE = {"applicable": "A", "not applicable": "N", "not determined": "?", "no threshold selected": "-"}
DATASET = {"kitti": "KITTI", "nuscenes": "nuScenes"}
TARGET_LIMITS = (0.01, 0.001, 0.0001)
PAIR_ORDER = ["KITTI distance", "nuScenes distance", "nuScenes weather", "change of dataset and detector"]
DIVISION_ORDER = ["by frame", "by recorded sequence"]


def num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(v)


def read(root, rel):
    df = pd.read_csv(root / rel)
    with open(root / rel, encoding="utf-8") as fh:
        lines = sum(1 for _ in fh)
    assert lines == len(df) + 1, f"{rel}: {lines} lines for {len(df)} rows (quoted line breaks?)"
    df["_line"] = range(2, len(df) + 2)  # header is line 1
    return df


def rec(row, rel, **kw):
    alpha = float(row["alpha"])
    r = {"alpha": alpha, "limit_type": "target" if alpha in TARGET_LIMITS else "exploratory",
         "split": int(row["seed"] if "seed" in row else row["split"]),
         "source_file": rel, "source_row": int(row["_line"]),
         "tau": None, "A_hat": None, "L": None, "U": None, "retention": None,
         "n_select_units": None, "n_eval_units": None, "kitti_rule": None,
         "estimate": "FAP", "ratio": None, "method": None}
    r.update(kw)
    r["outcome"] = OUTCOME[row["outcome"]]
    r["code"] = CODE[r["outcome"]]
    r["own_condition"] = r["condition_of_selection"] == r["condition_of_use"]
    return r


def std(row, **kw):
    """Fields shared by the run files m6, m7, m8."""
    out = {"indicator": row["indicator"], "A_hat": num(row.get("A_hat")), "L": num(row.get("hb_L")),
           "U": num(row.get("hb_U")), "retention": num(row.get("R_hat")), "tau": num(row.get("tau"))}
    for k in ("n_select_units", "n_eval_units"):
        if k in row:
            out[k] = None if num(row[k]) is None else int(row[k])
    out.update(kw)
    return out


def build(root):
    recs = []
    for _, r in read(root, M6A).iterrows():
        recs.append(rec(r, M6A, **std(r, pair="KITTI distance", division="by frame", unit="frame",
                                       kitti_rule=r["protocol"] == "kitti_ignore",
                                       condition_of_selection=r["established"], condition_of_use=r["applied"])))
    for _, r in read(root, M6B).iterrows():
        recs.append(rec(r, M6B, **std(r, pair="change of dataset and detector", division="by frame", unit="frame",
                                       kitti_rule=r["protocol"] == "kitti_ignore",
                                       condition_of_selection=DATASET[r["source"]],
                                       condition_of_use=DATASET[r["target"]])))
    variant = {"frame": ("by frame", "frame"), "scene_frame_unit": ("by recorded sequence", "frame"),
               "scene_scene_unit": ("by recorded sequence", "recorded sequence")}
    for _, r in read(root, M7).iterrows():
        div, unit = variant[r["variant"]]
        pair = {"distance": "nuScenes distance", "rain": "nuScenes weather"}[r["setting"]]
        recs.append(rec(r, M7, **std(r, pair=pair, division=div, unit=unit,
                                      condition_of_selection=r["established"], condition_of_use=r["applied"])))
    unit8 = {"frame": "frame", "drive": "recorded sequence"}
    for _, r in read(root, M8A).iterrows():
        recs.append(rec(r, M8A, **std(r, pair="KITTI distance", division="by recorded sequence",
                                       unit=unit8[r["hb_unit"]], kitti_rule=r["protocol"] == "kitti_ignore",
                                       condition_of_selection=r["established"], condition_of_use=r["applied"])))
    for _, r in read(root, M8B).iterrows():
        recs.append(rec(r, M8B, **std(r, pair="change of dataset and detector", division="by recorded sequence",
                                       unit=unit8[r["hb_unit"]], kitti_rule=r["protocol"] == "kitti_ignore",
                                       condition_of_selection=DATASET[r["source"]],
                                       condition_of_use=DATASET[r["target"]])))
    for _, r in read(root, POST).iterrows():
        kitti = r["pair"] in ("KITTI distance", "change of dataset and detector")
        x = rec(r, POST, pair=r["pair"], division="by recorded sequence", unit="recorded sequence",
                method="post-hoc Method " + r["method"], indicator=r["indicator"],
                kitti_rule=True if kitti else None,  # seq_ratio.py reads the kitti_ignore rows only
                condition_of_selection=r["established"], condition_of_use=r["applied"],
                tau=num(r["tau_c"]), A_hat=num(r["mean_Y"]), L=num(r["L_Y"]), U=num(r["U_Y"]),
                ratio=num(r["ratio"]), retention=num(r["retention"]), estimate="Y",
                n_select_units=int(r["n_select_seq"]), n_eval_units=int(r["n_eval_seq"]))
        assert x["own_condition"] == bool(r["own_condition"]), r["_line"]
        assert x["limit_type"] == r["limit"], r["_line"]
        recs.append(x)

    key = lambda r: (PAIR_ORDER.index(r["pair"]), DIVISION_ORDER.index(r["division"]), r["unit"],
                     r["method"] or "", str(r["kitti_rule"]), r["indicator"], r["condition_of_selection"],
                     r["condition_of_use"], -r["alpha"], r["split"])
    recs.sort(key=key)
    keys = [key(r) for r in recs]
    assert len(set(keys)) == len(keys), "two records describe the same cell"
    meta = {"generator": "tools/build_explorer_data.py", "generator_version": GENERATOR_VERSION,
            "date": DATA_DATE, "records": len(recs),
            "sources": {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in SOURCES},
            "note": "A_hat, L, U are the FAP estimate and its HB interval; for post-hoc records (estimate = Y) they "
                    "are the mean of the transformed sequence loss Y_s and its interval, compared with the limit α."}
    return meta, recs


def check_against_docs(root, recs):
    """Frame division, KITTI rule, transfers: counts must equal docs/results.md."""
    text = (root / "docs/results.md").read_text(encoding="utf-8")
    sec = text.split("## Outcomes over the five splits", 1)[1].split("\n## ", 1)[0]
    rows = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| setting") and "---" not in l]
    assert len(rows) == 8, f"expected 8 table rows in docs/results.md, found {len(rows)}"
    cols = [("u_s", 0.01), ("u_s", 0.05), ("u_s", 0.1), ("u_e", 0.01), ("u_e", 0.05), ("u_e", 0.1)]
    pair = {"change of dataset": "change of dataset and detector"}
    frame = [r for r in recs if r["division"] == "by frame" and r["kitti_rule"] in (True, None)]
    n = 0
    for line in rows:
        cells = [c.strip() for c in line.strip("|").split("|")]
        p = pair.get(cells[0], cells[0])
        sel, use = [s.strip() for s in cells[1].split("→")]
        for (ind, a), doc in zip(cols, cells[2:]):
            got = Counter(r["code"] for r in frame if r["pair"] == p and r["condition_of_selection"] == sel
                          and r["condition_of_use"] == use and r["indicator"] == ind and r["alpha"] == a)
            want = Counter({m.group(1).replace("–", "-"): int(m.group(2))
                            for m in re.finditer(r"([AN?–-])(\d)", doc)})
            assert got == want, f"{p} {sel}->{use} {ind} {a}: files {dict(got)}, docs/results.md {doc}"
            n += 1
    low = [r for r in frame if r["alpha"] in (0.001, 0.0001) and r["outcome"] != "no threshold selected"]
    assert not low, f"docs/results.md: no threshold at 1e-3 and 1e-4, but {len(low)} frame-division cells have one"
    return n


def dump(meta, recs):
    body = ",\n".join(json.dumps(r, sort_keys=True, separators=(",", ":"), allow_nan=False) for r in recs)
    return ('{"meta":' + json.dumps(meta, sort_keys=True, separators=(",", ":")) +
            ',\n"records":[\n' + body + "\n]}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=SCRIPT_ROOT, help="repository root holding results/ and docs/")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--check", action="store_true", help="compare with the existing file instead of writing")
    a = ap.parse_args()
    meta, recs = build(a.root.resolve())
    n = check_against_docs(a.root.resolve(), recs)
    text = dump(meta, recs)
    if a.check:
        same = a.out.exists() and a.out.read_text(encoding="utf-8") == text
        print(f"{a.out}: {'up to date' if same else 'DIFFERS from a fresh build'}")
        sys.exit(0 if same else 1)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(text.encode("utf-8"))  # bytes: no newline translation on Windows
    print(f"{len(recs)} records, {n} cells of docs/results.md reproduced, written to {a.out}")


if __name__ == "__main__":
    main()

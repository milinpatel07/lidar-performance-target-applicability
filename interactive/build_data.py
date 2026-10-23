#!/usr/bin/env python3
"""Write the data files of the interactive pages from the recorded result files.

    python3 interactive/build_data.py            # write interactive/data/units.json and separation.json
    python3 interactive/build_data.py --check    # exit 1 if the files differ from what the result files give

Every number in the two JSON files is copied from a recorded file; each entry names its file and its line
(line 1 is the header). The files are written with sorted keys and fixed formatting, so the check compares bytes.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

GENERATOR_VERSION = "interactive-data-1.0"
HERE = Path(__file__).resolve().parent

SRC = {
    "frames": "results/supporting_analyses/frames_per_condition.csv",
    "scenes_m7": "results/m7_scene_split/m7_scene_split.csv",
    "drives_m8": "results/supporting_analyses/m8_drives_per_part.csv",
    "dataset_m8": "results/m8_kitti_drive_split/B_dataset_drive.csv",
    "sequences_all": "results/post_hoc/ns_per_condition.csv",
    "separation": "results/supporting_analyses/fig_separation_curves.csv",
}

FRAME_SETTING = {
    "KITTI distance (KITTI rule)": ("KITTI distance", "KITTI"),
    "nuScenes distance": ("nuScenes distance", "nuScenes"),
    "nuScenes rain": ("nuScenes weather", "nuScenes"),
    "change of dataset": ("change of dataset and detector", None),
}
FRAME_CONDITION = {"KITTI (KITTI rule)": "KITTI"}
M7_SETTING = {"distance": "nuScenes distance", "rain": "nuScenes weather"}
DATASET_NAME = {"kitti": "KITTI", "nuscenes": "nuScenes"}

PANELS = [
    # (panel label in the CSV, id, pair, indicator, condition of selection, condition of use)
    ("distance (KITTI, $u_{\\mathrm{s}}$)", "kitti_distance", "KITTI distance", "u_s", "near", "far"),
    ("weather (nuScenes, $u_{\\mathrm{e}}$)", "nuscenes_weather", "nuScenes weather", "u_e", "clear", "rain"),
    ("dataset and detector ($u_{\\mathrm{s}}$)", "dataset_detector", "change of dataset and detector", "u_s",
     "nuScenes", "KITTI"),
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(root, key):
    with open(root / SRC[key], newline="", encoding="utf-8") as fh:
        # enumerate from 2: line 1 is the header
        return [(i, row) for i, row in enumerate(csv.DictReader(fh), start=2)]


def unit_entry(dataset, pair, condition, unit, unit_name, split, part, n, key, line):
    return {"dataset": dataset, "pair": pair, "condition": condition, "unit": unit, "unit_name": unit_name,
            "split": int(split), "part": part, "n": int(n), "source_file": SRC[key], "source_row": line}


def build_units(root):
    out = []
    # frames per condition and part (frame-level evaluation)
    for line, r in read(root, "frames"):
        pair, ds = FRAME_SETTING[r["setting"]]
        cond = FRAME_CONDITION.get(r["condition"], r["condition"])
        dataset = ds or cond
        for part, col in (("selection", "frames_select"), ("test", "frames_eval")):
            out.append(unit_entry(dataset, pair, cond, "frame", "frames", r["seed"], part, r[col], "frames", line))
    # nuScenes scenes per condition and part (sequence-level evaluation, m7 variant scene_scene_unit);
    # the selection count is recorded in the rows of the condition of selection, the test count in the rows of
    # the condition of use that have a selected threshold
    seen = {}
    for line, r in read(root, "scenes_m7"):
        if r["variant"] != "scene_scene_unit":
            continue
        pair = M7_SETTING[r["setting"]]
        for part, cond, col in (("selection", r["established"], "n_select_units"),
                                ("test", r["applied"], "n_eval_units")):
            if r[col] == "":
                continue
            k = (pair, cond, r["seed"], part)
            n = int(float(r[col]))
            if k in seen:
                if seen[k][0] != n:
                    raise SystemExit(f"{SRC['scenes_m7']}: two different unit counts for {k}")
                continue
            seen[k] = (n, line)
    for (pair, cond, seed, part), (n, line) in sorted(seen.items()):
        out.append(unit_entry("nuScenes", pair, cond, "recorded sequence", "scenes", seed, part, n, "scenes_m7", line))
    # KITTI drives per condition and part (m8)
    for line, r in read(root, "drives_m8"):
        if r["part"] == "grid":
            continue
        pair = "KITTI distance" if r["setting"] == "KITTI distance" else "change of dataset and detector"
        part = {"select": "selection", "eval": "test"}[r["part"]]
        out.append(unit_entry("KITTI", pair, r["condition"], "recorded sequence", "drives", r["seed"], part,
                              r["drives"], "drives_m8", line))
    # nuScenes scenes of the change of dataset and detector (m8 B, unit recorded sequence, KITTI rule rows)
    seen = {}
    for line, r in read(root, "dataset_m8"):
        if r["hb_unit"] != "drive" or r["protocol"] != "kitti_ignore":
            continue
        for part, ds, col in (("selection", r["source"], "n_select_units"), ("test", r["target"], "n_eval_units")):
            if ds != "nuscenes" or r[col] == "":
                continue
            k = (r["seed"], part)
            n = int(float(r[col]))
            if k in seen:
                if seen[k][0] != n:
                    raise SystemExit(f"{SRC['dataset_m8']}: two different unit counts for {k}")
                continue
            seen[k] = (n, line)
    for (seed, part), (n, line) in sorted(seen.items()):
        out.append(unit_entry("nuScenes", "change of dataset and detector", "nuScenes", "recorded sequence", "scenes",
                              seed, part, n, "dataset_m8", line))
    # all recorded sequences that hold the condition (all parts together)
    for line, r in read(root, "sequences_all"):
        dataset = "KITTI" if r["pair"] == "KITTI distance" or r["condition"] == "KITTI" else "nuScenes"
        out.append(unit_entry(dataset, r["pair"], r["condition"], "recorded sequence",
                              "drives" if dataset == "KITTI" else "scenes", r["split"], "all", r["sequences"],
                              "sequences_all", line))
    out.sort(key=lambda e: (e["split"], e["pair"], e["condition"], e["unit"], e["part"]))
    return out


def build_separation(root):
    rows = read(root, "separation")
    panels = []
    for label, pid, pair, ind, c_sel, c_use in PANELS:
        p = {"id": pid, "pair": pair, "indicator": ind, "condition_of_selection": c_sel, "condition_of_use": c_use,
             "source_file": SRC["separation"], "conditions": {}}
        first_line, last_line = None, None
        for line, r in rows:
            if r["panel"] != label:
                continue
            first_line = first_line or line
            last_line = line
            c = r["condition"]
            if c not in (c_sel, c_use):
                raise SystemExit(f"{SRC['separation']} line {line}: unknown condition {c}")
            d = p["conditions"].setdefault(c, {"roc": [], "fap": [], "operating_points": [], "interval": None})
            x, y = float(r["x"]), float(r["y"])
            if r["row"] == "ROC":
                d["roc"].append([x, y])
            elif r["row"] == "A_c(tau)":
                d["fap"].append([x, y])
            elif r["row"] == "ROC operating point":
                d["operating_points"].append({"tau": float(r["tau"]), "withheld": x, "rejected": y, "source_row": line})
            elif r["row"] == "HB interval at tau(0.1)":
                d["interval"] = {"tau": x, "A_hat": y, "L": float(r["L"]), "U": float(r["U"]), "source_row": line}
            else:
                raise SystemExit(f"{SRC['separation']} line {line}: unknown row type {r['row']}")
        if set(p["conditions"]) != {c_sel, c_use}:
            raise SystemExit(f"{SRC['separation']}: panel {label} lacks a condition")
        # the threshold selected at 0.1 is the one with the interval; the other recorded threshold is the one at 1e-2
        t01 = p["conditions"][c_sel]["interval"]["tau"]
        others = sorted({op["tau"] for op in p["conditions"][c_sel]["operating_points"]} - {t01})
        if len(others) != 1:
            raise SystemExit(f"{SRC['separation']}: panel {label} does not hold exactly two recorded thresholds")
        p["tau_selected"] = {"0.1": t01, "0.01": others[0]}
        p["source_rows"] = [first_line, last_line]
        panels.append(p)
    return panels


def dump(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def build(root):
    meta = {"generator": "interactive/build_data.py", "generator_version": GENERATOR_VERSION}
    used_units = ["frames", "scenes_m7", "drives_m8", "dataset_m8", "sequences_all"]
    units = {"meta": dict(meta, sources={SRC[k]: sha256(root / SRC[k]) for k in used_units},
                          note="n: number of units per condition, part and split as recorded; part 'all': every "
                               "recorded sequence that holds the condition, before division into parts."),
             "units": build_units(root)}
    sep = {"meta": dict(meta, sources={SRC["separation"]: sha256(root / SRC["separation"])},
                        note="Test part of split 0. ROC: [correct detections withheld, wrong detections rejected]; "
                             "fap: [tau, estimated FAP]; operating points and interval as recorded."),
           "panels": build_separation(root)}
    return {"units.json": dump(units), "separation.json": dump(sep)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=HERE.parent, help="repository root (default: parent of interactive/)")
    ap.add_argument("--check", action="store_true", help="compare instead of writing; exit 1 on a difference")
    a = ap.parse_args()
    files = build(a.root.resolve())
    bad = 0
    for name, text in files.items():
        path = HERE / "data" / name
        if a.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                print(f"DIFFERS: interactive/data/{name} (run python3 interactive/build_data.py)")
                bad += 1
            else:
                print(f"up to date: interactive/data/{name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote interactive/data/{name}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

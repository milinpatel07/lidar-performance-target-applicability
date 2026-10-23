#!/usr/bin/env python3
"""check_recorded_results.py - every recorded result file of version 1.0.0 is unchanged, at its current path.

tests/recorded_results_v1.0.0.sha256 holds the results/ lines of MANIFEST.sha256 of the tag v1.0.0. Since the layout of
version 2.0, the run folders of results/ are named by content; RENAMED maps the folder names of 1.0.0 to the current
ones. For every listed file the check computes the SHA-256 of the file at its current path and compares it with the
recorded one. Two files are not recorded results and are skipped: results/README.md (a description, extended since)
and results/INPUT_HASHES.md (a list that the build writes from the provenance.json files, whose headings name the run
folders; the provenance.json files themselves are checked).

    python3 tests/check_recorded_results.py     # from the repository root; exit 1 on a missing or changed file
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIST = Path(__file__).resolve().parent / "recorded_results_v1.0.0.sha256"
RENAMED = {"m1_range_kitti": "m1_kitti_distance_pilot", "m2_indicators_kitti": "m2_kitti_distance",
           "m3_range_nuscenes": "m3_nuscenes_distance", "m4_dataset_shift": "m4_dataset_change",
           "m6_protocol_seeds_weather": "m6_five_splits", "m7_scene_split": "m7_nuscenes_by_scene",
           "m8_kitti_drive_split": "m8_kitti_by_drive"}
NOT_RECORDED = {"results/README.md", "results/INPUT_HASHES.md"}


def current_path(old):
    parts = old.split("/")
    if len(parts) > 2 and parts[1] in RENAMED:
        parts[1] = RENAMED[parts[1]]
    return "/".join(parts)


def main():
    rows = [line.split("  ", 1) for line in LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    bad, n = [], 0
    for want, old in rows:
        if old in NOT_RECORDED:
            continue
        new = current_path(old)
        p = ROOT / new
        n += 1
        if not p.is_file():
            bad.append(f"MISSING  {new} (1.0.0: {old})")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != want:
            bad.append(f"CHANGED  {new} (1.0.0: {old})")
    for b in bad:
        print(b)
    print(f"{n} recorded result files of version 1.0.0 checked at their current paths, {len(bad)} missing or changed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

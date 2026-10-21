# Experiment scripts

The scripts load each other by file name (m3 loads m1; m4 loads m1, m2 and m3; m6 loads m4; m8 loads m6), so
they stay in this folder and are run from it. Each script states its inputs, outputs and options in its header.

| script | run | what it does |
|---|---|---|
| `m1_range_kitti.py` | m1 | statistics core: Eq. 1 per frame (`Cell`), Hoeffding-Bentkus p-value and interval, fixed-sequence selection, splits (`split_frames`), `analyse()` for two conditions; KITTI distance with the blended score; `--selftest` |
| `m2_indicators_kitti.py` | m2 | rebuilds the merged KITTI detections from the four networks, computes u_s and u_e, KITTI distance |
| `m3_range_nuscenes.py` | m3 | the same for nuScenes; `--split scene` draws the parts by recorded scene (variants (i) and (ii)); `--selftest` |
| `m4_dataset_shift.py` | m4 | change of dataset and detector, halves for selection and test |
| `m6_protocol_seeds_weather.py` | m6 | KITTI rule, change of dataset and detector on five splits, nuScenes weather; `--split scene` for weather |
| `m7_scene_split_report.py` | m7 | reproduction gate of the division by frame and the side-by-side table of the division by recorded scene |
| `m8_kitti_drive_split.py` | m8 | KITTI parts drawn by recorded drive (devkit mapping), with a reproduction gate |

A variant replaces `m1.split_frames` or `m1.Cell` at run time; the statistics in m1 are never edited.
[`SCRIPT_VERSIONS.md`](SCRIPT_VERSIONS.md) names the file behind each recorded run; earlier versions are in
[`recorded_versions/`](recorded_versions/).

**Headers written during the study.** The scripts are published byte for byte as they ran, so that their SHA-256 values
match the provenance of the runs. Some header texts therefore use the wording of the time they were written:

- `m1_range_kitti.py` calls itself "milestone 1" and says that its numbers are "not paper numbers": m1 used the blended
  score `u` of the detection pipeline (RUM), before the indicators u_s and u_e of m2; its statistics functions are used
  by every later run.
- `m3_range_nuscenes.py` repeats part of the docstring of m2 (including an output path of m2), and its self-test prints
  "M2 SELFTEST"; the code is the nuScenes version.
- `m6_protocol_seeds_weather.py` names version m6-0.1 in its first line; `SCRIPT_VERSION` in the code (m6-0.3) is the
  version. Its open note "[VERIFY against the devkit ...]" refers to the KITTI rule, which [`../docs/method.md`](../docs/method.md)
  states as implemented.
- "established" and "applied" in all scripts mean condition of selection and condition of use; "applies", "does not
  apply" and "no threshold established" mean applicable, not applicable and no threshold selected
  ([`../docs/glossary.md`](../docs/glossary.md)).

# Recorded results

The recorded results of the KITTI and nuScenes case study: one folder per run, as written by the run, with `provenance.json` (script version and SHA-256, SHA-256 of every input,
configuration) and `summary.txt` (consistency check against the detection pipeline and outcome counts).
[`../docs/results.md`](../docs/results.md) explains every folder and column and lists which files hold the values of each
section, table and figure of the paper; [`INPUT_HASHES.md`](INPUT_HASHES.md) lists the input files of every run. The
files keep the labels they were written with; [`../docs/glossary.md`](../docs/glossary.md) maps them to the terms of the
paper (for example m7 `variant` = `scene_frame_unit` is the third run and `scene_scene_unit` the sequence-level
evaluation).

[`post_hoc/`](post_hoc/README.md) holds analyses added after the parameters were fixed and the outcomes were known; they
are labelled as post hoc throughout.

| folder | run | script (in [`../experiments/`](../experiments/README.md)) | what it holds | folder name up to version 1.2.0 |
|---|---|---|---|---|
| [`m1_kitti_distance_pilot/`](m1_kitti_distance_pilot/) | m1 | `m1_range_kitti.py` | KITTI near and far distance with the blended score of the detection pipeline (precursor of m2) | `m1_range_kitti` |
| [`m2_kitti_distance/`](m2_kitti_distance/) | m2 | `m2_indicators_kitti.py` | KITTI near and far distance with the indicators u_s and u_e, with the variants of m1 | `m2_indicators_kitti` |
| [`m3_nuscenes_distance/`](m3_nuscenes_distance/) | m3 | `recorded_versions/m3_range_nuscenes_m3-0.2.py` | nuScenes near and far distance, five splits, frame-level evaluation (Fig. 4) | `m3_range_nuscenes` |
| [`m4_dataset_change/`](m4_dataset_change/) | m4 | `m4_dataset_shift.py` | change of dataset and detector, one split | `m4_dataset_shift` |
| [`m6_five_splits/`](m6_five_splits/) | m6 | `recorded_versions/m6_protocol_seeds_weather_m6-0.1.py` | KITTI distance with and without the KITTI rule (A), change of dataset and detector (B) and nuScenes weather (C) on five splits, frame-level evaluation (Fig. 4) | `m6_protocol_seeds_weather` |
| [`m7_nuscenes_by_scene/`](m7_nuscenes_by_scene/) | m7 | `m3_range_nuscenes.py`, `m6_protocol_seeds_weather.py` (`--split scene`), `m7_scene_split_report.py` | nuScenes distance and weather divided by recorded scene: reproduction of the frame-level evaluation, third run and sequence-level evaluation | `m7_scene_split` |
| [`m8_kitti_by_drive/`](m8_kitti_by_drive/) | m8 | `m8_kitti_drive_split.py` | KITTI distance and change of dataset and detector divided by recorded KITTI drive: third run and sequence-level evaluation | `m8_kitti_drive_split` |
| [`supporting_analyses/`](supporting_analyses/) | - | `tools/supporting/`, `tools/figures/` | retention, changes in the detections, intervals, common threshold, recall, annotation checks, figure data | (unchanged) |
| [`post_hoc/`](post_hoc/README.md) | - | `post_hoc/code/` | analyses added after the outcomes were known | (unchanged) |

The folders were renamed in version 2.0; their files are those of the runs, with mount paths normalised.
[`../tests/check_recorded_results.py`](../tests/check_recorded_results.py) checks every result file of version 1.0.0 at
its current path against the SHA-256 recorded in that version's manifest. The files themselves keep the folder names of
the time they were written (for example in `provenance.json` or in `REPRO_PASSED.txt`).

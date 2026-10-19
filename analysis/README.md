# Experiment scripts

The scripts load each other by file name (m3 loads m1; m4 loads m1, m2 and m3; m6 loads m4; m8 loads m6), so
they stay in this folder and are run from it. Each script states its inputs, outputs and options in its header.

| script | run | what it does |
|---|---|---|
| `m1_range_kitti.py` | m1 | statistics core: Eq. 1 per frame (`Cell`), Hoeffding-Bentkus p-value and interval, fixed-sequence selection, splits (`split_frames`), `analyse()` for two conditions; KITTI distance with the blended score; `--selftest` |
| `m2_indicators_kitti.py` | m2 | rebuilds the merged KITTI detections from the four networks, computes u_s and u_e, KITTI distance |
| `m3_range_nuscenes.py` | m3 | the same for nuScenes; `--split scene` draws the parts by recorded scene (variants (i) and (ii)); `--selftest` |
| `m4_dataset_shift.py` | m4 | change of dataset, halves for selection and evaluation |
| `m6_protocol_seeds_weather.py` | m6 | KITTI rule, change of dataset on five splits, nuScenes rain; `--split scene` for rain |
| `m7_scene_split_report.py` | m7 | reproduction gate of the frame split and the side-by-side table of the scene split |
| `m8_kitti_drive_split.py` | m8 | KITTI parts drawn by recorded drive (devkit mapping), with a reproduction gate |

A variant replaces `m1.split_frames` or `m1.Cell` at run time; the statistics in m1 are never edited.
[`SCRIPT_VERSIONS.md`](SCRIPT_VERSIONS.md) names the file behind each recorded run; earlier versions are in
[`recorded_versions/`](recorded_versions/).

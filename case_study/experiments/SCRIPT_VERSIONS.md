# Script versions behind each recorded run

Each run's `provenance.json` records the SHA-256 of the script that produced it. The table names the shipped file with that hash. `experiments/` holds the current versions; `experiments/recorded_versions/` holds earlier versions that produced the first runs. The current m3 and m6 add the option `--split scene`; with `--split frame` they reproduce the recorded m3 and m6 results row by row (`results/division_by_sequence/nuscenes_by_scene/REPRO_PASSED.txt`). The run column names the folder in `results/`.

The two frame runs of the scene split were started with m3-0.3 and m6-0.2, the labels in their `provenance.json`. The versions with the scene-unit loss (m3-0.4, m6-0.3) replaced these files before the runs wrote their provenance, so the hash recorded for them is that of the shipped m3-0.4 and m6-0.3. The two version pairs differ only in the scene-unit loss, which the frame path does not use.

| run | script version | script SHA-256 (first 16) | shipped file |
|---|---|---|---|
| division_by_frame/kitti_distance_pilot | m1-0.2 | `64355a602f1f68d9` | `experiments/m1_range_kitti.py` |
| division_by_frame/kitti_distance | m2-0.1 | `7d9327d85d2f56e4` | `experiments/m2_indicators_kitti.py` |
| division_by_frame/nuscenes_distance | m3-0.2 | `55f69b5a98c6bbb2` | `experiments/recorded_versions/m3_range_nuscenes_m3-0.2.py` |
| division_by_frame/dataset_change_one_split | m4-0.1 | `-` | not recorded in this run |
| division_by_frame/kitti_rule_dataset_change_weather | m6-0.1 | `f3e715e032eed40a` | `experiments/recorded_versions/m6_protocol_seeds_weather_m6-0.1.py` |
| division_by_sequence/nuscenes_by_scene/m3_frame | m3-0.3 | `d270f962e0000eaf` | `experiments/m3_range_nuscenes.py` |
| division_by_sequence/nuscenes_by_scene/m3_scene | m3-0.4 | `d270f962e0000eaf` | `experiments/m3_range_nuscenes.py` |
| division_by_sequence/nuscenes_by_scene/m6_frame | m6-0.2 | `12471263830f08c4` | `experiments/m6_protocol_seeds_weather.py` |
| division_by_sequence/nuscenes_by_scene/m6_scene | m6-0.3 | `12471263830f08c4` | `experiments/m6_protocol_seeds_weather.py` |
| division_by_sequence/kitti_by_drive | m8-0.1 | `bfcfdbcb9f9640e1` | `experiments/m8_kitti_drive_split.py (run version; shipped with an edited docstring)` |

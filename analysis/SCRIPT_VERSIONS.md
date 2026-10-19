# Script versions behind each recorded run

Each run's `provenance.json` records the SHA-256 of the script that produced it. The table names the shipped file with that hash. `analysis/` holds the current versions; `analysis/recorded_versions/` holds earlier versions that produced the first runs. The current m3 and m6 add the option `--split scene`; with `--split frame` they reproduce the recorded m3 and m6 results row by row (`results/m7_scene_split/REPRO_PASSED.txt`).

The two frame runs of the scene split were started with m3-0.3 and m6-0.2, the labels in their `provenance.json`. The versions with the scene-unit loss (m3-0.4, m6-0.3) replaced these files before the runs wrote their provenance, so the hash recorded for them is that of the shipped m3-0.4 and m6-0.3. The two version pairs differ only in the scene-unit loss, which the frame path does not use.

| run | script version | script SHA-256 (first 16) | shipped file |
|---|---|---|---|
| m1_range_kitti | m1-0.2 | `8f0dfc3045ba2d98` | `analysis/m1_range_kitti.py` |
| m2_indicators_kitti | m2-0.1 | `86bf80d773f9c03d` | `analysis/m2_indicators_kitti.py` |
| m3_range_nuscenes | m3-0.2 | `6af341a2b554e715` | `analysis/recorded_versions/m3_range_nuscenes_m3-0.2.py` |
| m4_dataset_shift | m4-0.1 | `-` | not recorded in this run |
| m6_protocol_seeds_weather | m6-0.1 | `7bcb2b6302bbc754` | `analysis/recorded_versions/m6_protocol_seeds_weather_m6-0.1.py` |
| m7_scene_split/m3_frame | m3-0.3 | `b6af3474c51156a9` | `analysis/m3_range_nuscenes.py` |
| m7_scene_split/m3_scene | m3-0.4 | `b6af3474c51156a9` | `analysis/m3_range_nuscenes.py` |
| m7_scene_split/m6_frame | m6-0.2 | `161775194e1d38ff` | `analysis/m6_protocol_seeds_weather.py` |
| m7_scene_split/m6_scene | m6-0.3 | `161775194e1d38ff` | `analysis/m6_protocol_seeds_weather.py` |
| m8_kitti_drive_split | m8-0.1 | `9aadbaa1d0067be5` | `analysis/m8_kitti_drive_split.py (run version; shipped with an edited docstring)` |

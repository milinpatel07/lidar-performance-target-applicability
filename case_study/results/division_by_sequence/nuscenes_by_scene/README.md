# nuScenes, whole scenes in the parts (run m7)

Do the nuScenes outcomes for distance and weather hold when whole scenes are assigned to the parts, and how many outcomes remain applicable or not applicable when scenes are counted as units?

| file | content |
|---|---|
| `m3_frame/` | rerun of the frame-level evaluation of nuScenes distance; must equal [`../../division_by_frame/nuscenes_distance/`](../../division_by_frame/nuscenes_distance/README.md) |
| `m6_frame/` | rerun of the frame-level evaluation of parts A, B and C; must equal [`../../division_by_frame/kitti_rule_dataset_change_weather/`](../../division_by_frame/kitti_rule_dataset_change_weather/README.md) |
| `REPRO_PASSED.txt` | result of the comparison of the reruns with the recorded results |
| `m3_scene/` | nuScenes distance with whole scenes in the parts: third run and sequence-level evaluation |
| `m6_scene/` | nuScenes weather with whole scenes in the parts: third run and sequence-level evaluation |
| `m7_scene_split.csv` | the frame-level evaluation, the third run and the sequence-level evaluation side by side (`variant` = `frame`, `scene_frame_unit`, `scene_scene_unit`) |
| `m7_scene_split_summary.txt` | outcome codes per cell, "(i)" third run, "(ii)" sequence-level evaluation, and scenes per part |

Written by [`../../../experiments/m3_range_nuscenes.py`](../../../experiments/m3_range_nuscenes.py) and [`../../../experiments/m6_protocol_seeds_weather.py`](../../../experiments/m6_protocol_seeds_weather.py) with `--split frame` or `--split scene`, collected by [`../../../experiments/m7_scene_split_report.py`](../../../experiments/m7_scene_split_report.py); each subfolder has its own `provenance.json`; `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

The subfolder names give the script (m3 or m6) and the division (`frame` or `scene`).

# KITTI rule, change of dataset and detector, nuScenes weather (run m6)

Three parts on five splits, frame-level evaluation; together with [`../nuscenes_distance/`](../nuscenes_distance/README.md) they give Fig. 4 of the paper.

| file | content |
|---|---|
| `A_kitti_range_protocol.csv` | KITTI near and far distance, with the KITTI rule (`protocol` = `kitti_ignore`: detections in regions without annotation or on vans left out) and without it (`as_run`) |
| `B_shift_seeds_protocol.csv` | KITTI with its detector against nuScenes with its detector, five splits, with and without the KITTI rule on the KITTI side |
| `C_weather_nuscenes.csv` | nuScenes clear weather against rain, daylight scenes only |
| `summary.txt` | outcome counts over the five splits per cell, and the wrong detections the KITTI rule removes |
| `provenance.json` | script version and SHA-256, input SHA-256, configuration |

Written by [`../../../experiments/recorded_versions/m6_protocol_seeds_weather_m6-0.1.py`](../../../experiments/recorded_versions/m6_protocol_seeds_weather_m6-0.1.py) (version m6-0.1); `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

The file names keep the labels of the run (`range` for distance, `shift` for the change of dataset and detector).

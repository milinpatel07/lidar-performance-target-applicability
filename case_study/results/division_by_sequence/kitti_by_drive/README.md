# KITTI, whole drives in the parts (run m8)

Do the KITTI outcomes for distance and for the change of dataset and detector hold when whole KITTI drives are assigned to the parts (the nuScenes side of the change by whole scenes), and how many remain applicable or not applicable when drives are counted as units?

| file | content |
|---|---|
| `frame/` | rerun of the frame-level evaluation of parts A (KITTI distance) and B (change of dataset and detector) of run m6; must equal [`../../division_by_frame/kitti_rule_dataset_change_weather/`](../../division_by_frame/kitti_rule_dataset_change_weather/README.md) |
| `REPRO_PASSED.txt` | result of that comparison |
| `A_kitti_distance_drive.csv` | KITTI near and far distance with whole drives in the parts: third run (`hb_unit` = `frame`) and sequence-level evaluation (`hb_unit` = `drive`) |
| `B_dataset_drive.csv` | change of dataset and detector, the same two evaluations |
| `summary.txt` | result of the reproduction and outcome counts over the five splits |
| `provenance.json` | script version and SHA-256, input SHA-256, configuration, drives per part |

Written by [`../../../experiments/m8_kitti_drive_split.py`](../../../experiments/m8_kitti_drive_split.py) (version m8-0.1); `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

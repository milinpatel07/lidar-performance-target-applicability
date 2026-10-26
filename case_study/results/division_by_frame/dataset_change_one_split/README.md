# Change of dataset and detector, one split (run m4)

Does a threshold selected on KITTI with the KITTI detector meet its limit on nuScenes with the nuScenes detector, and the reverse, for u_s and u_e on split 0? Data and detector change together; the change does not isolate a triggering condition and serves as an experimental control, against which the changes of distance and of weather can be compared.

| file | content |
|---|---|
| `shift_matrix.csv` | one row per cell: indicator, limit, source and target dataset, threshold, FAP estimate, interval [L, U], frame bootstrap interval, retention, outcome |
| `summary.txt` | quantiles of the indicator values per dataset and the outcome of each cell, as printed by the run |
| `provenance.json` | script version and SHA-256, input SHA-256, configuration |

Written by [`../../../experiments/m4_dataset_shift.py`](../../../experiments/m4_dataset_shift.py) (version m4-0.1; this run recorded no script hash); `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

The same change on five splits, with the KITTI rule, is in [`../kitti_rule_dataset_change_weather/`](../kitti_rule_dataset_change_weather/README.md) (files `B_*`).

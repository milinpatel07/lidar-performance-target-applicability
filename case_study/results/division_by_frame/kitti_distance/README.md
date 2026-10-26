# KITTI distance with the two indicators (run m2)

The question of [`../kitti_distance_pilot/`](../kitti_distance_pilot/README.md) for the spatial indicator u_s and the existence indicator u_e, with the same variants.

| file | content |
|---|---|
| `matrix_all_variants.csv` | one row per cell: variant (overlap, object set, near/far boundary), indicator, split (`seed`), limit, condition of selection (`established`) and of use (`applied`), threshold, FAP estimate, interval [L, U], retention, outcome |
| `tally_all_variants.json` | outcome counts per variant |
| `summary.txt` | consistency check against the detection pipeline and outcome counts, as printed by the run |
| `provenance.json` | script version and SHA-256, input SHA-256, configuration |

Written by [`../../../experiments/m2_indicators_kitti.py`](../../../experiments/m2_indicators_kitti.py) (version m2-0.1); `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

KITTI detections are labelled as run, without the KITTI rule; the frame-level outcomes of the paper for KITTI distance, with the rule, are in [`../kitti_rule_dataset_change_weather/`](../kitti_rule_dataset_change_weather/README.md) (files `A_*`).

# nuScenes distance (run m3)

Does a threshold selected at near distance on nuScenes meet its limit at far distance, and the reverse, for u_s and u_e on five splits? Variants: object set (`car`, `vehicles`) and near/far boundary (quantiles 0.25, 0.5, 0.75); the overlap for a correct detection is IoU 0.5. Fig. 4 of the paper uses the variant `A_iou0.5`, `car`, boundary quantile 0.5.

| file | content |
|---|---|
| `matrix_all_variants.csv` | one row per cell: variant (overlap, object set, near/far boundary), indicator, split (`seed`), limit, condition of selection (`established`) and of use (`applied`), threshold, FAP estimate, interval [L, U], retention, outcome |
| `tally_all_variants.json` | outcome counts per variant |
| `summary.txt` | consistency check against the detection pipeline and outcome counts, as printed by the run |
| `provenance.json` | script version and SHA-256, input SHA-256, configuration |

Written by [`../../../experiments/recorded_versions/m3_range_nuscenes_m3-0.2.py`](../../../experiments/recorded_versions/m3_range_nuscenes_m3-0.2.py) (version m3-0.2); `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

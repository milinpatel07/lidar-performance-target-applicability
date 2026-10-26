# KITTI distance, pilot with the blended score (run m1)

Does a threshold selected at near distance on KITTI meet its limit at far distance, and the reverse? The indicator is the blended score of the detection pipeline, the precursor of the two indicators of the paper; the variants change the overlap for a correct detection (IoU 0.5, or 0.7 for cars), the object set (cars, all classes) and the near/far boundary (quartiles 0.25, 0.5, 0.75).

| file | content |
|---|---|
| `matrix_all_variants.csv` | one row per cell: variant (overlap, object set, near/far boundary), split (`seed`), limit, condition of selection (`established`) and of use (`applied`), threshold, FAP estimate, interval [L, U], frame bootstrap interval, retention, outcome, test and selection frames |
| `frontier_primary.csv` | primary variant (IoU 0.5, cars, median boundary, split 0), one row per condition and candidate threshold: retention, FAP estimate and upper bound on the selection part |
| `tally_all_variants.json` | outcome counts per variant |
| `summary.txt` | consistency check against the detection pipeline and outcome counts, as printed by the run |
| `provenance.json` | script version and SHA-256, input SHA-256, configuration |

Written by [`../../../experiments/m1_range_kitti.py`](../../../experiments/m1_range_kitti.py) (version m1-0.2); `provenance.json` records the script version and SHA-256, the SHA-256 of every input and the configuration ([`../../../experiments/SCRIPT_VERSIONS.md`](../../../experiments/SCRIPT_VERSIONS.md)). Columns: [`../../../docs/results.md`](../../../docs/results.md#columns-of-the-run-files).

KITTI detections are labelled as run, without the KITTI rule.

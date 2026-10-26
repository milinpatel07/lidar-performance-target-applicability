# applicability-test

This package implements the applicability test for anyone who wants to run it on the detections of their own
detector, in scripts or pipelines: a threshold on an uncertainty indicator is selected
with a finite-sample guarantee that the false acceptance proportion (FAP) stays at or below a limit alpha in the
condition of selection, and the same threshold is then tested on independent data of the condition of use. The
outcome is applicable, not applicable, not determined or no threshold selected, and it applies to the outputs of
any detector that gives each detection an indicator value and a correct/wrong label.

The concept is explained in [`../docs/concept.md`](../docs/concept.md). The statistics are those of
[`../case_study/experiments/m1_range_kitti.py`](../case_study/experiments/m1_range_kitti.py), and the tests check that both give the same numbers.

## Install

From the repository root:

```
pip install ./package
```

or directly from GitHub:

```
pip install "git+https://github.com/milinpatel07/lidar-performance-target-applicability#subdirectory=package"
```

The only dependency is numpy. `pip install "./package[pandas]"` adds pandas, whose DataFrames can be passed in
place of dictionaries of arrays. `pip install "./package[test]"` adds pytest for `pytest package/tests`.

## Example (synthetic data)

```python
import numpy as np
import applicability_test as at

rng = np.random.default_rng(0)

def condition(share_wrong, n_frames=3000):
    frame = np.repeat(np.arange(n_frames), 5)                     # 5 detections per frame
    correct = (rng.uniform(size=frame.size) >= share_wrong).astype(int)
    u = np.where(correct == 1, rng.beta(2, 20, frame.size), rng.beta(2, 4, frame.size))
    return {"frame": frame, "u": u, "correct": correct}

selection_c = condition(0.05)                                     # selection part of condition c
test_c2 = condition(0.20)                                         # test part of condition c'
r = at.applicability_test(selection_c, test_c2, candidates=np.linspace(0.01, 1, 100), alpha=0.02, delta=0.05)
print(r.outcome, r.tau, r.L, r.U, r.retention)                    # not applicable 0.17 0.043 0.063 0.895
```

`examples/synthetic_example.py` runs the test with two conditions, a grid part for the candidate thresholds and
two limits. `examples/detections_example.csv` holds a smaller sample of such synthetic detections in the format of the
command line (written by `python examples/synthetic_example.py --csv examples/detections_example.csv`):

```
python -m applicability_test examples/detections_example.csv --selection-condition clear --use-condition rain --alpha 0.05
```

prints, among other lines, `outcome: not applicable`; with `--use-condition clear` the outcome is applicable.

## API

| function | returns |
|---|---|
| `applicability_test(selection, use, candidates, alpha, delta=0.05, unit="frame")` | `ApplicabilityResult`: `outcome`, `tau`, `L`, `U`, `A_hat`, `retention` (in the condition of use), `n_selection`, `n_test`, `selection` |
| `select_threshold(frame_ids, u, correct, candidates, alpha, delta, unit_ids=None)` | `SelectionResult`: `tau` (None if no threshold is selected), `index`, `candidates` (sorted), `p_values`, `n` |
| `test_threshold(frame_ids, u, correct, tau, alpha, delta, unit_ids=None)` | `TestResult`: `L`, `U`, `A_hat`, `n`, `retention`, `outcome` |
| `per_unit_shares(frame_ids, u, correct, tau, unit_ids=None)` | `(ids, values)`: per-frame share a_f, or with `unit_ids` the per-sequence mean of a_f |
| `fap(frame_ids, u, correct, tau, unit_ids=None)` | estimate of the FAP, the mean of the per-unit values |
| `retention(u, correct, tau)` | share of the correct detections with u <= tau |
| `quantile_candidates(u, levels=0.01..1.00)` | distinct quantiles of u, sorted |
| `hb_pvalue(S, n, alpha)` | Hoeffding-Bentkus (HB) p-value for FAP > alpha from n units with sum S |
| `hb_upper(S, n, delta)`, `hb_lower(S, n, delta)` | upper and lower HB confidence bound |
| `n_required(alpha, delta)` | smallest n at which n units without false acceptance give an HB p-value <= delta |
| `zero_failure_bound(alpha, delta)` | smallest n with n >= ln(delta) / ln(1 - alpha) (Eq. 5 of the paper) |
| `lowest_limit(n, delta)` | 1 - delta^(1/n), the lowest limit that n units without false acceptance can show |

The outcome strings are the constants `APPLICABLE`, `NOT_APPLICABLE`, `NOT_DETERMINED` and `NO_THRESHOLD`. The
functions raise `ValueError` if alpha or delta lie outside (0, 1), if the list of candidates is empty, if u holds NaN,
or if correct holds values other than 0 and 1. An empty selection part gives no threshold selected; an empty test part
gives [0, 1] and not determined.

## Input format

`selection` and `use` are mappings (a dict of arrays or a pandas DataFrame) with one entry per detection:

| key | meaning |
|---|---|
| `frame` | frame id |
| `sequence` | recorded sequence id; needed only for `unit="sequence"`. Frame ids then need to be unique only within a sequence |
| `u` | indicator value; a detection is accepted if u <= tau. NaN is rejected as input |
| `correct` | 1 for a correct, 0 for a wrong detection |

`selection` holds the detections of the condition of selection in the selection part, `use` those of the condition
of use in the test part. A frame belongs to a condition if it holds at least one detection of the condition, so
pass only the detections of the condition. The command line reads the same data from one CSV with the columns
`frame`, `sequence` (optional), `condition`, `part` (`grid`, `selection` or `test`), `u` and `correct`:

```
python -m applicability_test detections.csv --selection-condition near --use-condition far --alpha 0.01
python -m applicability_test detections.csv --selection-condition near --use-condition far --alpha 0.01 \
    --unit sequence --candidates values --values 0.01:1.00:0.01 --json
```

With `--candidates quantiles` (default) the candidates are the quantiles of u at levels 0.01 to 1.00 over the
`grid` rows of both conditions. The command stops with a message if the file cannot be read, a column is missing, a
condition has no rows in the needed part (for example a misspelt condition), or alpha or delta lie outside (0, 1).

## What is computed

- **Per-frame share** a_f: the share of wrong detections among the accepted detections of the condition in a frame,
  and 0 for a frame without accepted detections. The **FAP** is its mean over the frames of the condition.
- **Frame-level evaluation** (`unit="frame"`): each frame is one unit. **Sequence-level evaluation**
  (`unit="sequence"`): each sequence is one unit, its value is the mean of a_f over its frames in the condition,
  and n counts sequences.
- **Selection**: a candidate passes if its HB p-value for FAP > alpha is at most delta. Candidates are taken from
  the lowest upwards, and the selected threshold is the last candidate that passes before the first candidate that
  fails. If the lowest candidate fails, no threshold is selected.
- **Test**: U is the HB upper bound at delta/2 of the per-unit values, and L is one minus the HB upper bound at
  delta/2 of the values 1 - a_f, so [L, U] is an interval at confidence level 1 - delta.
- **Retention**: the share of the correct detections of the condition of use (test part) that the threshold
  accepts. It is reported because a threshold that accepts almost nothing meets any limit.

## Outcomes

| outcome | condition | meaning |
|---|---|---|
| applicable | U <= alpha | the FAP in the condition of use is at most alpha, with error probability at most delta/2 |
| not applicable | L > alpha | the FAP in the condition of use exceeds alpha, with error probability at most delta/2 |
| not determined | L <= alpha < U | the data neither show that the limit is met nor that it is exceeded; this makes no claim and can hide an exceeded limit |
| no threshold selected | lowest candidate fails | the selection data of the condition of selection do not show the limit for any candidate |

## Assumptions

- The units (frames or sequences) of each part are independent and identically distributed draws from their
  condition. Frames of one recorded sequence are not independent; then use the sequence-level evaluation.
- The test units are independent of the selection units, for example by dividing whole sequences into the parts.
- The candidates are fixed before the selection data are used, for example from a separate grid part.
- The error probability holds for each outcome on its own. A safety argument that relies on several outcomes at
  once has to divide delta by their number.
- Showing a limit alpha needs at least `zero_failure_bound(alpha, delta')` units per condition and part
  (delta' = delta for selecting, delta/2 for testing); for alpha = 0.01 these are 299 and 368 units at delta = 0.05.

## Licence

MIT.

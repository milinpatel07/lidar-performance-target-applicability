# Guide: applying the test to your own detector

This guide is for perception developers and safety engineers who want to apply the applicability test to detections
of their own detector. The test needs no access to the detector itself. It works on a table of detections in which each
detection has a frame, a condition, an uncertainty value and a label correct or wrong. The guide goes from that table
to an outcome, with the Python package in [`package/`](../../package/) or, without installing anything, in the browser.

## 1. Prepare the table

One row per detection after every rule that already removes detections (for example a vote between ensemble members or
a score cut-off):

| column | content |
|---|---|
| `frame` | frame identifier |
| `sequence` | identifier of the recorded sequence the frame belongs to (needed for the sequence-level evaluation) |
| `condition` | the condition of the detection, assigned by a rule that uses no detector output (for example a rain label of the drive), or by the box position for distance |
| `part` | `grid`, `selection` or `test` (see step 2) |
| `u` | uncertainty indicator value; higher means more uncertain, and a detection is accepted if `u ≤ τ` |
| `correct` | 1 if the detection matches an annotated object under your matching rule, 0 otherwise |

Choices that change the result and are to be recorded with it: the matching rule (for example IoU ≥ 0.5), which object
classes count, how unannotated regions are treated, and the indicator.

## 2. Divide the data into parts

- **grid** (for example 10 %): fixes the candidate thresholds, so that neither the selection nor the test data
  influence them.
- **selection** (for example 45 %): selects the threshold in the condition of selection.
- **test** (for example 45 %): tests it in the condition of use (and in the condition of selection, as a check).

Divide whole recorded sequences, not single frames, so that frames of one sequence do not fall into both the selection
and the test part. Fix the limit α, the error probability δ and the conditions before computing any outcome, and record
them with a date.

## 3. Run the test

Install and run on the command line:

```bash
pip install "git+https://github.com/milinpatel07/lidar-performance-target-applicability#subdirectory=package"
python -m applicability_test detections.csv --selection-condition clear --use-condition rain \
    --alpha 0.01 --delta 0.05 --unit sequence
```

or in Python:

```python
import pandas as pd
import applicability_test as at

d = pd.read_csv("detections.csv")
grid = d[d.part == "grid"]
sel = d[(d.part == "selection") & (d.condition == "clear")]
use = d[(d.part == "test") & (d.condition == "rain")]
r = at.applicability_test(sel, use, candidates=at.quantile_candidates(grid.u), alpha=0.01, delta=0.05,
                          unit="sequence")
print(r.outcome, r.tau, r.L, r.U, r.retention, r.n_selection, r.n_test)
```

Without installing anything, the page
[Run the test on your own detections](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/own-data.html)
reads the same CSV in the browser, runs every ordered pair of conditions and exports the results; the data stay on
your computer.

## 4. Read the result

| field | meaning |
|---|---|
| `outcome` | applicable, not applicable, not determined or no threshold selected |
| `tau` | the threshold selected in the condition of selection (None if no threshold was selected) |
| `L`, `U` | interval of the FAP in the condition of use at confidence level 1 − δ |
| `retention` | share of the correct detections of the condition of use that the threshold accepts |
| `n_selection`, `n_test` | number of independent units counted in each part |

Report every applicable outcome with its retention and the unit counted, and compare `n_selection` and `n_test` with
the zero-failure bound (`at.zero_failure_bound(alpha, delta)` and `at.zero_failure_bound(alpha, delta / 2)`). What each
outcome supports and which measure follows is in
[using an outcome in a safety argument](outcomes-in-a-safety-argument.md); how many units to record is in
[how much data to record per condition](plan-recording.md).

## 5. Checks before relying on a result

- [ ] Run the test of the threshold in its own condition of selection as well. With independent units, the outcome
      not applicable there has probability at most δ + δ/2 (7.5 % at δ = 0.05); a higher frequency over several splits
      points to dependent units or a changed distribution.
- [ ] Repeat with several random divisions (splits). An outcome on all splits has the same error bound as on one split;
      agreement shows only that it does not depend on the split.
- [ ] Compare the frame-level and the sequence-level evaluation. If outcomes appear only with frames counted as units,
      the evidence rests on dependent frames.
- [ ] Look at the four changes in the detections between the two conditions (share of wrong detections, separation,
      shift of the indicator values, spread over frames), not only at AUROC; see [`concept.md`, section 4](../concept.md#4-four-changes-in-the-detections-and-which-one-auroc-shows).

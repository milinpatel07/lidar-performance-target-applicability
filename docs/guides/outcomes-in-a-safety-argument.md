# Guide: using an outcome in a safety argument

The applicability test gives, for a threshold selected in one condition and used in another, one of four outcomes. This
guide states what each outcome supports in a SOTIF analysis according to ISO 21448, what it does not support, and the
measure that follows. It follows Sect. 6.1 and Table 5 of the paper.

## Scope of an outcome

An outcome is an analysis result for the **object detector as one system element**. It is not a classification of
scenarios: tracking, fusion and motion planning lie between the detector and a hazardous behaviour, so a not
applicable outcome does not by itself show that a condition is a triggering condition, and an applicable outcome does
not show that a condition is safe. The vehicle manufacturer supplies how often each condition occurs in operation and
the limit α derived from the risk allocated to the detector.

## The four outcomes

| outcome | rule | what it supports | measure that follows |
|---|---|---|---|
| **applicable** | U ≤ α | evidence that the target is met in the condition of use with the transferred threshold, at error probability at most δ/2 if the units are independent | use the threshold in the condition of use, provided the share of annotated objects that reach the motion planner meets a second target on missed objects |
| **not applicable** | L > α | evidence that the target is not met in the condition of use with the transferred threshold, at error probability at most δ/2 if the units are independent | detector supplier: select a threshold in the condition of use with a run-time signal for it, or a common threshold for several conditions; vehicle manufacturer: restrict the operational design domain or the functionality, or add a measure in tracking, fusion or motion planning |
| **not determined** | L ≤ α < U | no statement: the data do not suffice or the FAP lies close to α | record further independent units (the zero-failure bound gives the minimum) and treat the condition as not verified |
| **no threshold selected** | the lowest candidate threshold fails in the condition of selection | the target cannot be shown to be met even where the threshold would be selected | record further independent units in the condition of selection, or request a reallocation of α at vehicle level |

## Reading an outcome correctly

1. **Report the retention with every applicable outcome.** A threshold that accepts almost nothing meets any limit,
   because frames without accepted detections contribute zero false acceptances (Eq. 3 of the paper). An applicable
   outcome is informative only together with the share of correct detections the threshold accepts. In the case study,
   transferred thresholds with an applicable outcome at 10⁻² accepted at most 29 % of the correct detections.
2. **Report the independent unit and its number.** With dependent frames counted as units, the stated error
   probability is not guaranteed. State whether frames or recorded sequences were counted, and how many.
3. **A not determined outcome makes no claim, but it can hide an exceeded limit.** It is not evidence that the target is
   met.
4. **In the condition of selection, the selection guarantee is the evidence.** A not determined outcome of the test in
   the condition of selection does not withdraw it.
5. **Several outcomes at once need a smaller error probability.** The error probability applies to each outcome on its
   own. An argument that relies on k outcomes together divides δ by k.
6. **AUROC is not a substitute for the test.** AUROC measures how well the indicator separates correct from wrong
   detections. It does not change when wrong detections become more frequent, when they are spread differently over
   frames, or when the indicator values shift, and each of these can make a transferred threshold exceed the limit
   (see [`docs/concept.md`](../concept.md)).

## Threshold per condition or common threshold

- A **threshold per condition** requires the condition to be known at run time. The box position gives the distance
  of a detection; weather requires a rain signal, whose errors have to be included in the allocation of α.
- A **common threshold** for several conditions, which has to pass the selection in each of them at error probability
  δ divided by their number, needs no run-time signal. In the case study, a common threshold for near and far distance
  always gave an applicable or not determined outcome, with a lower retention at near distance than the threshold
  selected there (supplementary material, [`docs/supplementary/`](../supplementary/)).

## A second performance target on missed objects

The FAP limits only the wrong detections that are accepted. A lower threshold also withholds more correct detections,
and a missed object can be a more hazardous error than an accepted wrong one. A safety argument that uses the threshold
therefore needs a second target, a lower limit on the share of annotated objects that reach the motion planner, tested
under the same conditions with the same interval and with the zero-failure bound applied to its own limit.

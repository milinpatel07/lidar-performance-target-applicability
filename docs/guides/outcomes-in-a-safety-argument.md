# Guide: using an outcome in a safety argument

This guide is for safety engineers and assessors who use outcomes of the applicability test as evidence in a SOTIF
analysis according to ISO 21448. It states the scope of an outcome, what it supports and what it does not, and how to
report it. It follows Sect. 6.1 and Table 5 of the paper.

## Scope of an outcome

An outcome is an analysis result for the **object detector as one system element**. It is not a classification of
scenarios: tracking, fusion and motion planning lie between the detector and a hazardous behaviour, so a not
applicable outcome does not by itself show that a condition is a triggering condition, and an applicable outcome does
not show that a condition is safe. The vehicle manufacturer supplies how often each condition occurs in operation and
the limit α derived from the risk allocated to the detector.

## The four outcomes

The test gives one of four outcomes: **applicable** (U ≤ α), **not applicable** (L > α), **not determined**
(L ≤ α < U) and **no threshold selected** (the lowest candidate threshold fails in the condition of selection). What
each outcome means for the performance target and which measure follows (paper Table 5) is listed in
[`concept.md`, section 1](../concept.md#1-from-the-acceptance-criterion-to-a-measure). In short: an applicable outcome
supports using the transferred threshold in the condition of use, together with a second target on missed objects; a
not applicable outcome calls for a measure by the detector supplier or the vehicle manufacturer; a not determined
outcome calls for further independent units in the condition of use, and no threshold selected for further units
in the condition of selection or a reallocation of α at vehicle level.

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
   (see [`concept.md`, section 4](../concept.md#4-four-changes-in-the-detections-and-which-one-auroc-shows)).

## Threshold per condition or common threshold

- A **threshold per condition** requires the condition to be known at run time. The box position gives the distance
  of a detection; weather requires a rain signal, whose errors have to be included in the allocation of α.
- A **common threshold** for several conditions, which has to pass the selection in each of them at error probability
  δ divided by their number, needs no run-time signal. In the case study, a common threshold for near and far distance
  always gave an applicable or not determined outcome, with a lower retention at near distance than the threshold
  selected there (supplementary material, [`../../case_study/docs/supplementary/`](../../case_study/docs/supplementary/)).

## A second performance target on missed objects

The FAP limits only the wrong detections that are accepted. A lower threshold also withholds more correct detections,
and a missed object can be a more hazardous error than an accepted wrong one. A safety argument that uses the threshold
therefore needs a second target, a lower limit on the share of annotated objects that reach the motion planner, tested
under the same conditions with the same interval and with the zero-failure bound applied to its own limit.

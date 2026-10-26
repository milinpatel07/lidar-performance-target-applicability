# Predictions, fixed before any measurement

**FROZEN 2026-10-01, author-final.** Base commit: `bcad5b9`; frozen in the
commit titled "Freeze predictions.md (author-final)" (a file cannot contain the
hash of the commit that adds it; recorded in the project's decision log, 2026-10-01).

Date: 2026-10-01. Once frozen, no entry is
changed. Each prediction states what would be observed if it holds, what would
be observed if it fails, and what either outcome means. A prediction whose
failure carries no meaning is not written down, because it would not be worth
testing.

Fixed parameters, set here and not adjusted afterwards: confidence `1 − δ` with
δ = 0.05; the target `α` on the false acceptance proportion, reported as a sweep
over the set {10⁻², 10⁻³, 10⁻⁴} and not as a single value (`α` is an
element-level performance target allocated from the vehicle-level acceptance
criterion through ISO 21448:2022 7.3.1, and 6.5 fixes no single value; see
`design.md` Section 5), with the feasibility boundary a reported result of this
sweep and not a chosen target; triggering-condition classes C1 to C5; the residual reference class C0
(adopted 2026-09-30, split into clean-nominal and residual-non-nominal per Salay
Section VI; a baseline row and column, not a triggering-condition class); the false
acceptance proportion defined as the per-frame false acceptance proportion in
[0, 1], with the controlled risk the false discovery rate FDR = E[per-frame FAP]
and the frame as the unit of independence (decision 002, option (a), author-final
2026-09-30); two overlap thresholds for the matching criterion; two association
rules; the pre-registered co-occurrence threshold of 20% (if the detections
excluded for co-occurrence exceed 20% of the detections in frames with at least
one mechanism, the five pure classes are declared unrepresentative of adverse
operation).

---

**P1. Indicator response by mechanism.**
*Holds if*: in C1 (airborne scatterers) and C2 (surface water and spray) the
spatial disagreement indicator separates correct from incorrect detections
better than the existence indicator does, measured by area under the receiver
operating characteristic curve with intervals that do not overlap; in C3
(vehicle-like static structure) the ordering is reversed.
*Fails if*: the ordering is the same in all classes, or the intervals overlap.
*Either way*: a mechanism-to-indicator mapping fixed before measurement is
either supported or not. Failure is the more informative outcome, because it
would indicate that ensemble members trained on the same data share the failure
mode the mechanism produces, so disagreement carries no information about it.
That ensemble members share failure modes under distribution shift is
\PH{unverified claim: no citation in the neighbour set; see
02_literature/leads_to_verify.md L6}; if it holds, this prediction is not safe.

**P2. Discrimination is more stable than the operating point.**
*Holds if*: the spread of area under the curve across classes is smaller, in
units of its own interval width, than the spread of the false acceptance
proportion at a fixed threshold.
*Fails if*: discrimination varies as much as the operating point.
*Either way*: this decides which of the two causes in the paper's separation
dominates, and therefore whether a better run-time class estimate would recover
the lost retention or whether a different indicator is required.

**P3. The maximum retention gap is not zero and not total.**
The retention gap is the per-class quantity `R_c(τ_c) − R_c(τ*)`; the maximum
retention gap is its maximum over classes.
*Holds if*: the maximum retention gap lies above the width of its interval
estimate and below the retention `R_c(τ_c)` at the class-known threshold of the
class in which the maximum is attained.
*Fails if*: it is indistinguishable from zero, or it removes nearly all
retention.
*Either way*: zero means class information is not worth acquiring for this
detector and these classes, which is a usable finding and must be reported as
prominently as a positive one. Near-total means a single threshold meeting the
target everywhere leaves the element unusable, which bears on whether the
allocated target is achievable at all.

**P4. Applicability is not symmetric.**
*Holds if*: there exist classes `c`, `c'` where the target established in `c`
applies in `c'` but the target established in `c'` does not apply in `c`.
*Fails if*: the applicability matrix is symmetric within interval estimates.
*Either way*: asymmetry is what makes the matrix worth reporting instead of a
single ranking of class difficulty. If it is symmetric, the matrix reduces to an
ordering, and the paper should say so.

**P5. Some cells return "not determined".**
*Holds if*: at least one ordered pair returns the third outcome for at least one
value of `α` in the sweep.
*Fails if*: every cell is decided.
*Either way*: this is a prediction about the data, not about the detector. Its
purpose is that the three-outcome rule be exercised rather than presented as a
formality. The count of undetermined cells is reported with the required
detection counts that would decide them.

---

## Outcomes defined in advance

Two outcomes are defined here, before any run, so neither can be selected after
seeing results.

**Not determined (per matrix cell).** For the ordered pair (c, c'), with
`[L_{c'}(τ_c), U_{c'}(τ_c)]` the two-sided `1 − δ` interval estimate of the
false acceptance proportion (per-frame FDR, frames resampled): applies if and only
if `U_{c'}(τ_c) ≤ α`; does not apply if `L_{c'}(τ_c) > α`; not determined if
`L_{c'}(τ_c) ≤ α < U_{c'}(τ_c)`. A not-determined cell reports the accepted
detections in c' and the number that would be needed to separate the interval from
α at the same confidence (`sample_size.md`). Expected from `sample_size.md` (not
measured): determination reachable to about α = 10⁻³ to 10⁻⁴; the observed
feasibility boundary is reported from the sweep.

**Co-occurrence unrepresentative (per study).** If the detections excluded for
co-occurrence exceed 20% of the detections in frames with at least one mechanism,
the five pure classes C1 to C5 are declared unrepresentative of adverse operation.
The paper then reports the matrix as conditional on single-mechanism frames,
reports the co-occurrence share as a primary finding, and names combined-condition
evaluation as required further work, without claiming the matrix represents adverse
operation as a whole. Below 20%, the pure classes are treated as representative and
the co-occurrence share is reported as a limitation.

## Predictions the paper does not make

No prediction is made about which classes are hardest, because the paper has no
basis for one and a guess would be presented as expectation. No prediction is
made about absolute values of retention or false acceptance, because these
depend on the detector, the ensemble size and the matching criterion.

## Analyses fixed in advance

Reported whatever the outcome: every cell of the applicability matrix with its
interval and outcome; retention alongside every false acceptance proportion;
both overlap thresholds; both association rules; the count of frames excluded
for mechanism co-occurrence, per pair; the residual class treated as a class and
not discarded.

No cell is omitted for being uninteresting. The order of presentation is fixed
before measurement: classes in the order C0 to C5, pairs in row-major order.

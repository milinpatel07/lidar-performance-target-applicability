# Method: the applicability test

This page describes what the scripts in `analysis/` compute. Symbols follow the paper; every term is defined in
[`glossary.md`](glossary.md).

## 1. Detector, detections and indicators

Each dataset has its own detector ensemble: four PointPillars networks (KITTI) or four class-balanced multi-head
PointPillars networks (nuScenes), trained separately on the training split and differing only in the random seed.
Every network keeps boxes with a score of at least 0.1. The boxes of the four networks are matched greedily at a
rotated three-dimensional intersection over union (IoU) of 0.5, and a merged **detection** is kept when at least three
of the four networks contribute to it. A detection is **correct** (y = 1) if it matches an annotated car at IoU 0.5,
and **wrong** (y = 0) otherwise. Only car detections are evaluated.

Two uncertainty indicators are evaluated; both are larger for a less certain detection:

| indicator | definition | what it measures |
|---|---|---|
| spatial, u_s | one minus the mean pairwise rotated 3D IoU of the networks' boxes | disagreement about where the object is |
| existence, u_e | one minus the mean confidence over the four networks, with zero for a network that did not detect the object | how weakly the networks support that the object is there |

Before any analysis, every run rebuilds the merged detections from the four networks' outputs and compares its
per-frame counts of missed and false detections with those of the detection pipeline (`frame_errors_cache.pkl`). They
agree for all 3,769 KITTI and all 6,019 nuScenes validation frames; the `summary.txt` of m1, m2 and m3 reports the check.

**KITTI rule.** KITTI marks image regions that are not annotated (DontCare) and treats vans as a neighbouring class of
cars. A wrong detection whose image box overlaps a DontCare region by more than half of its own area, or that matches
a van at 3D IoU 0.5, is excluded (neither correct nor wrong): 2,454 detections. Results are reported with the rule
(`kitti_ignore`) and, as a check, without it (`as_run`).

## 2. Conditions

| setting | conditions | assignment |
|---|---|---|
| distance (KITTI, nuScenes) | near, far | a detection is near or far by the distance of its own box, split at the median distance of the car detections in the grid part (34.8 m on KITTI with the rule, 21.4 m on nuScenes, split 0) |
| weather (nuScenes) | clear, rain | a frame takes the class of its recorded scene description ("rain" in the text); night frames are excluded |
| change of dataset and detector (control) | KITTI with the KITTI ensemble, nuScenes with the nuScenes ensemble | the dataset; the detector changes with it |

A condition is assigned without using the detector output, so that no frame is assigned on the basis of the behaviour
under study. Distance is the exception: a wrong detection has no annotated object, so its own box gives the only
distance available. A frame with near and far detections belongs to both distance conditions with different
detections.

## 3. False acceptance proportion and retention

A detection d is **accepted** by threshold τ if u(d) ≤ τ. In frame f, with f_c the car detections of condition c,

    a_f(τ) = |{d in f_c : u(d) ≤ τ, y(d) = 0}| / |{d in f_c : u(d) ≤ τ}|      (0 if nothing is accepted)
    A_c(τ) = mean of a_f(τ) over the frames of condition c                       (Eq. 1)

The performance target requires A_c(τ) ≤ α. The **retention** R_c(τ) is the share of the correct detections of
condition c that τ accepts; every rejected correct detection is an object the following functions do not receive.

## 4. Splits, threshold selection and the decision

The frames of a pair of conditions are divided with a fixed seed into a grid part (10 %), a selection part (45 %) and a
test part (45 %). The grid part fixes 100 candidate thresholds (percentiles of the indicator) and the near/far boundary.
For the change of dataset and detector, each dataset is divided into halves and the candidates are 0.01 to 1.00 in steps of 0.01.
Each division is drawn five times (splits, seeds 0 to 4).

**Selection (Learn then Test).** In condition c, the null hypothesis A_c(τ_j) > α is tested at each candidate with the
Hoeffding-Bentkus p-value, in fixed sequence from the most restrictive candidate upward. τ_c is the largest candidate
rejected before the first non-rejection; with δ = 0.05, A_c(τ_c) ≤ α holds with probability at least 1 − δ over the
draw of the selection frames. If no candidate is rejected, no threshold is selected in c.

**Common threshold.** τ* is selected with the same sequence, testing all K conditions at level δ/K and stopping at the
first candidate at which one of them is not rejected. The **retention gap** G_c = R_c(τ_c) − R_c(τ*) is the share of
correct detections that knowing the condition at run time would keep.

**Decision.** τ_c is applied to the test part of condition c'. The one-sided Hoeffding-Bentkus bounds L and U of
A_c'(τ_c), each at δ/2, give the outcome: applicable if U ≤ α, not applicable if L > α, not determined otherwise. As the
true FAP lies on one side of α, an applicable or not applicable outcome is wrong with probability at most δ/2, provided
the test units are independent of each other and of the selection units. The error probability holds for each outcome
on its own; a safety argument that relies on J outcomes at once divides δ by J.

## 5. Possible causes of an exceeded target

A threshold selected in c can exceed the limit in c' because of four changes in the detections: (a) **weaker
separation**, the indicator orders correct and wrong detections less well in c' (lower AUROC); (b) **more wrong
detections**, c' holds a larger share of wrong detections at unchanged distributions; (c) **shifted values**, the
indicator values in c' lie at another position on the scale; (d) **different spread over frames**, the wrong detections
are distributed differently over the frames, which changes the per-frame mean A_c without changing the pooled share.
AUROC depends only on the order of the values and registers none of (b), (c) and (d). `results/supporting_analyses/wrong_share_and_median_split0.csv` gives the share of
wrong detections and the median indicator value per condition, from which (b) and (c) can be read; (d) is read from the difference between the FAP and the pooled share.

## 6. Units and the number required for a decision

The Hoeffding-Bentkus bound assumes independent units. Frames of one recorded sequence share objects, weather and
road, so the analysis is repeated with the parts drawn by recorded sequence (**division by recorded sequence**; nuScenes
scene in m7, KITTI drive in m8):

- **variant (i)**: sequences are permuted with the original split function and fractions, every frame takes its
  sequence's part, and the frame stays the unit of the selection test and of the interval;
- **variant (ii)**: the same partition with the sequence as the unit; the loss of a sequence is the mean of a_f over
  its frames in the condition, and a sequence without accepted detections contributes zero.

If A_c > α, the probability that n independent units all show no false acceptance is at most (1 − α)^n. A statement
at error level δ′ therefore needs at least

    n ≥ ln δ′ / ln(1 − α)      (Eq. 4)

independent units per condition and part: 299 for selection (δ′ = δ) and 368 for the test (δ′ = δ/2) at α = 10⁻²;
59 and 72 at 0.05†; 29 and 36 at 0.1†. The bound is necessary, not sufficient: any unit with a false acceptance raises the
number further. A post-hoc test that keeps the per-frame target exactly with the sequence as the unit is described in
[`results/post_hoc/README.md`](../results/post_hoc/README.md).

## 7. Parameters fixed in advance

Fixed before the first run and recorded in [`study_protocol/predictions_frozen_2026-10-01.md`](study_protocol/predictions_frozen_2026-10-01.md):
δ = 0.05, the target limits 10⁻², 10⁻³ and 10⁻⁴, the conditions, Eq. 1, and five predictions with the outcome that would
count as their failure. The exploratory limits 0.05† and 0.1† were fixed at the same time to show which outcomes the
data can decide. The division by recorded sequence (m7, m8) was added after the parameters had been fixed.

## Terms

All terms, symbols, outcome codes and column names: [`glossary.md`](glossary.md).

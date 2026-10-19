# Method: the applicability test

This page describes what the scripts in `analysis/` compute. Symbols follow the paper.

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
agree for all 3,769 KITTI and all 6,019 nuScenes validation frames; each run's `summary.txt` reports the check.

**KITTI rule.** KITTI marks image regions that are not annotated (DontCare) and treats vans as a neighbouring class of
cars. A wrong detection whose image box overlaps a DontCare region by more than half of its own area, or that matches
a van at 3D IoU 0.5, is excluded (neither correct nor wrong): 2,454 detections. Results are reported with the rule
(`kitti_ignore`) and, as a check, without it (`as_run`).

## 2. Conditions

| setting | conditions | assignment |
|---|---|---|
| distance (KITTI, nuScenes) | near, far | a detection is near or far by the distance of its own box, split at the median distance of the car detections in the grid part (34.8 m on KITTI with the rule, 21.4 m on nuScenes, split 0) |
| rain (nuScenes) | clear, rain | a frame takes the class of its recorded scene description; night frames are excluded |
| change of dataset | KITTI, nuScenes | the dataset |

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

The frames of a setting are split with a fixed seed into a grid part (10 %), a selection part (45 %) and an evaluation
part (45 %). The grid part fixes 100 candidate thresholds (percentiles of the indicator) and the near/far boundary.
For the change of dataset, each dataset is split into halves and the candidates are 0.01 to 1.00 in steps of 0.01.
Each setting is repeated on five splits (seeds 0 to 4).

**Selection (Learn then Test).** In condition c, the null hypothesis A_c(τ_j) > α is tested at each candidate with the
Hoeffding-Bentkus p-value, in fixed sequence from the most restrictive candidate upward. τ_c is the largest candidate
rejected before the first non-rejection; with δ = 0.05, A_c(τ_c) ≤ α holds with probability at least 1 − δ over the
draw of the selection frames. If no candidate is rejected, no threshold is selected in c.

**Common threshold.** τ* is selected with the same sequence, testing all K conditions at level δ/K and stopping at the
first candidate at which one of them is not rejected. The **retention gap** G_c = R_c(τ_c) − R_c(τ*) is the share of
correct detections that knowing the condition at run time would keep.

**Decision.** τ_c is applied to the evaluation part of condition c'. The two-sided Hoeffding-Bentkus interval [L, U] of
A_c'(τ_c) at confidence 1 − δ gives the outcome: applicable if U ≤ α, not applicable if L > α, not determined
otherwise. Each outcome is decided at confidence 1 − δ on its own; there is no joint statement over all pairs.

## 5. Possible causes of an exceeded target

A threshold selected in c can exceed the target in c' because (a) the indicator separates correct from wrong
detections less well in c' (lower AUROC), (b) c' holds a larger share of wrong detections at unchanged separation, or
(c) the indicator values in c' lie at a different position on the scale. AUROC depends only on the order of the values
and registers neither (b) nor (c). `results/supporting_analyses/wrong_share_and_median_split0.csv` gives the share of
wrong detections and the median indicator value per condition, from which (b) and (c) can be read.

## 6. Units and the number required for a decision

The Hoeffding-Bentkus bound assumes independent units. Frames of one recorded sequence share objects, weather and
road, so the analysis is repeated with the parts drawn by recorded sequence (nuScenes scene in m7, KITTI drive in m8):

- **variant (i)**: sequences are permuted with the original split function and fractions, every frame takes its
  sequence's part, and the frame stays the unit of the selection test and of the interval;
- **variant (ii)**: the same partition with the sequence as the unit; the loss of a sequence is the mean of a_f over
  its frames in the condition, and a sequence without accepted detections contributes zero.

If A_c > α, the probability that n independent units all show no false acceptance is at most (1 − α)^n. A statement
at error level δ′ therefore needs at least

    n ≥ ln δ′ / ln(1 − α)      (Eq. 4)

independent units per condition and part: 299 for selection (δ′ = δ) and 368 for evaluation (δ′ = δ/2) at α = 10⁻²;
59 and 72 at 0.05†; 29 and 36 at 0.1†.

## 7. Parameters fixed in advance

Fixed before the first run and recorded in [`study_protocol/predictions_frozen_2026-10-01.md`](study_protocol/predictions_frozen_2026-10-01.md):
δ = 0.05, the target values 10⁻², 10⁻³ and 10⁻⁴, the conditions, Eq. 1, and five predictions with the outcome that would
count as their failure. The target values 0.05† and 0.1† were added before the first run to show which outcomes the
data can decide. The splits by recorded sequence (m7, m8) were added after the parameters had been fixed.

## Terms

| term | meaning |
|---|---|
| acceptance criterion | ISO 21448 criterion on the residual risk, specified at vehicle level |
| performance target | element-level target allocated from an acceptance criterion; here A_c(τ) ≤ α |
| triggering condition | ISO 21448 term for a condition that can initiate a hazardous behaviour of the function |
| rejection threshold | threshold on an uncertainty indicator above which detections are rejected |
| false acceptance proportion (A) | share of accepted detections that are wrong, averaged over frames (Eq. 1); a proportion, not a rate |
| retention (R) | share of correct detections accepted |
| applicable | a target established in condition c holds in condition c' by the decision rule of Section 4 |
| discrimination | ordering an indicator induces between correct and wrong detections; measured by AUROC |
| split | one random partition of the frames (seed 0 to 4) into grid, selection and evaluation parts |

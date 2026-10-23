# Method: what the scripts compute

This page describes what the scripts in `experiments/` compute and where, for readers who check or rerun the case
study. The idea behind the test (performance target,
outcomes, the four changes in the detections, the independent unit) is explained once in [`concept.md`](concept.md);
single terms are in [`glossary.md`](glossary.md). Section numbers, equations and tables refer to the submitted paper.

## 1. Detector, detections and indicators (paper Sect. 3.1, 4.1)

Each dataset has its own ensemble of four PointPillars networks, trained with different random seeds (KITTI: the
three-class configuration of OpenPCDet; nuScenes: the class-balanced multi-head configuration). Each network keeps the
car boxes with a confidence of at least 0.1. The boxes of the first network are taken in descending order of
confidence, and each other network contributes its unused car box with the highest rotated 3D intersection over union
(IoU) with that box, if the IoU is at least 0.5. A **detection** is formed only if at least three of the four networks
contribute (the **vote**). A detection is **correct** (y = 1) if one-to-one matching assigns it to an annotated car at
IoU ≥ 0.5, and **wrong** (y = 0) otherwise. Only car detections are evaluated.

| indicator | definition | what it measures |
|---|---|---|
| spatial, u_s | one minus the mean pairwise rotated 3D IoU of the contributing boxes (paper Eq. 1) | disagreement about where the object is and how large it is |
| existence, u_e | one minus the mean confidence over the four networks, with zero for a network without a box | how weakly the networks support that the object is there |

Because a missing network contributes confidence 0, a detection with three networks has u_e ≥ 0.25.

Before any analysis, every run rebuilds the merged detections from the four networks' outputs and compares its
per-frame counts of missed and false detections with those of the detection pipeline (`frame_errors_cache.pkl`). They
agree for all 3,769 KITTI and all 6,019 nuScenes validation frames; the `summary.txt` of m1, m2 and m3 reports the check.

**KITTI rule** (paper Sect. 4.2). A wrong KITTI detection whose image box overlaps a DontCare region by more than half
of its own area, or that matches a van at 3D IoU 0.5, is excluded (neither correct nor wrong): 2,454 detections.
Results are reported with the rule (`kitti_ignore`) and, as a check, without it (`as_run`).

## 2. Conditions (paper Sect. 4.2, Table 3)

| pair of conditions | conditions | assignment |
|---|---|---|
| distance (KITTI, nuScenes) | near, far | a detection is near or far by the ground-plane distance of its own box centre from the LiDAR origin, split at the median distance of the car detections in the grid part (split 0: 34.8 m on KITTI with the rule, 21.4 m on nuScenes) |
| weather (nuScenes) | clear, rain | a frame takes the label of its scene description (the word "rain"); scenes whose description contains "night" are excluded |
| change of dataset and detector (control) | KITTI with the KITTI ensemble, nuScenes with the nuScenes ensemble | the dataset; the detector changes with it |

Weather and dataset are assigned per frame without any detector output. Distance is assigned per detection from the
detector's own box, because a wrong detection has no annotated car whose distance could be used; a frame with near and
far detections contributes to both distance conditions.

## 3. Per-frame share, FAP and retention (paper Sect. 3.1, Eq. 2)

`Cell` in `experiments/m1_range_kitti.py` holds the detections of one condition in one part. With f_c the car detections
of condition c in frame f:

    a_f(τ) = |{d in f_c : u(d) ≤ τ, y(d) = 0}| / |{d in f_c : u(d) ≤ τ}|      (0 if nothing is accepted)
    A_c(τ) = mean of a_f(τ) over the frames of condition c                       (estimate of Eq. 2)

A frame belongs to c if it holds at least one car detection of c. `Cell.retention` gives R_c(τ), the share of the
correct detections of c that τ accepts. Why the FAP is per frame and why retention accompanies every applicable
outcome: [`concept.md`, section 2](concept.md#2-what-is-measured-per-frame-share-fap-and-pooled-share).

## 4. Parts, selection and test (paper Sect. 3.2, 3.3, 4.3)

`split_frames` divides the frames of a pair of conditions with a fixed seed into a grid part (10 %), a selection part
(45 %) and a test part (45 %). The grid part fixes 100 candidate thresholds (the quantiles of the indicator at levels
0.01 to 1.00 over the car detections of both conditions) and the near/far boundary. For the change of dataset and
detector (m4, m6 part B), each dataset is divided into halves and the candidates are 0.01 to 1.00 in steps of 0.01.
Each division is drawn with seeds 0 to 4 (five splits).

- **Selection.** `hb_pvalue` gives the Hoeffding-Bentkus p-value of each candidate on the selection part of c;
  `chain_index` takes the candidates from the lowest upwards and returns the last one that passes (p ≤ δ) before the
  first that fails. If the lowest candidate fails, no threshold is selected.
- **Common threshold.** τ* is selected with the same order, and a candidate passes only if it passes in each of the K
  conditions at δ/K. The **retention gap** G_c = R_c(τ_c) − R_c(τ*) is the share of correct detections that knowing the
  condition at run time would keep.
- **Test.** `hb_upper` and `hb_lower` give U and L of A_c′(τ_c) on the test part of c′, each at δ/2; the outcome
  follows from [the rule in `concept.md`](concept.md#3-selecting-a-threshold-and-testing-it).

## 5. Changes in the detections (paper Sect. 3.4, Table 4)

The four changes and which one AUROC shows are explained in
[`concept.md`, section 4](concept.md#4-four-changes-in-the-detections-and-which-one-auroc-shows). The files to read
them from: [`wrong_share_and_median_split0.csv`](../results/supporting_analyses/wrong_share_and_median_split0.csv)
(share of wrong detections and median indicator value of correct and wrong detections per condition: more wrong
detections, shifted values); [`fig_separation_curves.csv`](../results/supporting_analyses/fig_separation_curves.csv)
(ROC curves and operating points: separation). A different spread over frames is read from the FAP (`A_hat` in the run
files) against the pooled share; for clear weather and rain, the pooled share at the clear-weather thresholds follows
from the counts and operating points in [`roc_clear_rain_points.csv`](../results/supporting_analyses/roc_clear_rain_points.csv).
Different spread over frames can change the FAP at an unchanged pooled share; in rain both rose, the FAP more
(paper Table 4).

## 6. Division by recorded sequence and the unit of the test (paper Sect. 3.5, 4.3)

The frame-level evaluation uses `split_frames` and `Cell` as above. The third run and the sequence-level evaluation
replace them at run time (the statistics in m1 are never edited):

- **third run**: recorded sequences (nuScenes scenes in m3 and m6 with `--split scene`, KITTI drives in m8) are
  permuted with the original fractions, every frame takes its sequence's part, and the frame stays the unit;
- **sequence-level evaluation**: the same parts with the sequence as unit; the value of a sequence is the mean of a_f
  over its frames in the condition, a sequence without accepted detections contributes 0, and n counts sequences.

The file labels of the frame-level evaluation, the sequence-level evaluation and the third run are listed in [`concept.md`, section 5](concept.md#5-the-independent-unit-frame-or-recorded-sequence),
together with the zero-failure bound of Eq. 5 (`n_required` in `experiments/m1_range_kitti.py`). A post-hoc test that
keeps the per-frame target with the sequence as unit is described in
[`results/post_hoc/README.md`](../results/post_hoc/README.md).

## 7. Parameters fixed in advance (paper Sect. 4.4)

Fixed and recorded before any outcome was computed:
[`study_protocol/predictions_frozen_2026-10-01.md`](study_protocol/predictions_frozen_2026-10-01.md). The sequence-level
evaluation and the third run (m7, m8) were added afterwards; deviations are listed in
[`study_protocol/outcomes_and_deviations.md`](study_protocol/outcomes_and_deviations.md).

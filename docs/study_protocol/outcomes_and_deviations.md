# Outcomes of the predictions and deviations from the protocol

[`predictions_frozen_2026-10-01.md`](predictions_frozen_2026-10-01.md) was fixed before the first evaluation run. This
page states how each prediction turned out, with the evidence file, and every point where the study departed from the
frozen protocol. It was written after the outcomes were known.

## Predictions

| prediction | outcome | reason | evidence |
|---|---|---|---|
| P1. Indicator response by mechanism | not tested | the prediction compares classes C1 and C2 with C3; C1 and C2 were measured only together, as recorded rain, and C3 was not measured | |
| P2. Separation is more stable than the operating point | not tested | how to compare the spread of AUROC with the spread of the FAP in units of interval width was not fixed in advance, so no comparison was computed | |
| P3. The maximum retention gap is not zero and not total | held | the retention gap G of the common threshold lies above zero and below the retention at the threshold of the condition (KITTI, u_s, split 0) | [`common_threshold_outcomes.csv`](../../results/supporting_analyses/common_threshold_outcomes.csv) |
| P4. Applicability is not symmetric | held | nuScenes → KITTI is not applicable on all splits for u_s, KITTI → nuScenes is applicable; KITTI near → far is not applicable and far → near applicable on all splits at 0.1† | [`docs/results.md`](../results.md#outcomes-over-the-five-splits) |
| P5. Some cells return "not determined" | held | not determined outcomes occur in every pair of conditions | [`docs/results.md`](../results.md#outcomes-over-the-five-splits) |

## Mapping of the frozen condition classes to the conditions studied

| frozen class | process | studied as |
|---|---|---|
| C0 (reference) | residual class, not a triggering condition | not used; near distance, clear weather and the KITTI data with the KITTI detector serve as conditions of comparison |
| C1 airborne scatterers | droplets in the air | together with C2 as nuScenes rain (scene description contains "rain", daylight only) |
| C2 surface water and spray | water on the road | together with C1 as nuScenes rain |
| C3 vehicle-like static structure | geometry like a vehicle where none is | not measured (no label in either dataset) |
| C4 occluding object present | partial evidence | not measured (no label in either dataset) |
| C5 long range | fewer returns per object | far distance on KITTI and nuScenes (boundary: median distance of the car detections in the grid part) |

## Deviations from the frozen protocol

| frozen | done | when and why | effect |
|---|---|---|---|
| limits {10⁻², 10⁻³, 10⁻⁴} | the same, plus 0.05† and 0.1† as exploratory limits | fixed at the same time as the target limits, before any outcome was computed, to show at which limits the test reaches the outcome applicable or not applicable | the exploratory limits are marked † everywhere and define no performance target |
| interval with "frames resampled" | one-sided Hoeffding–Bentkus bounds at δ/2 each give the outcome | used from the first run (m1) on; HB holds for any distribution of per-frame values in [0, 1] and finite samples, the bootstrap does not give that guarantee | the frame bootstrap interval is reported beside HB as a description (m1, m4) |
| frame as the unit of independence | frame-level evaluation (division by frame, frame as unit), and in addition the sequence-level evaluation (division by recorded sequence, sequence as unit) and the third run (division by recorded sequence, frame as unit) | the sequence-level evaluation and the third run were added after the parameters were fixed and the first outcomes were known (m7, m8), because frames of one sequence are dependent | reported side by side; Fig. 4 of the paper shows the frame-level evaluation, and the paper's answers to the research questions state the sequence-level evaluation first |
| co-occurrence threshold of 20 % for mixed mechanisms | not applied | the datasets label no mechanism per detection, so co-occurrence cannot be counted | rain is reported as recorded rain, not as one physical process |
| two overlap thresholds, two association rules | IoU 0.5 in the main results; IoU 0.7 for cars as a variant in m1 and m2 (KITTI); one association rule (greedy matching) | the second association rule was not implemented | stated as a limitation |
| change of dataset | dataset and detector change together (each dataset with its own ensemble) | the ensembles were trained per dataset | called the change of dataset and detector, and used as a control |
| (none) | KITTI rule (wrong detections in DontCare regions or on vans excluded) | added after the first runs, from the KITTI evaluation conventions | results reported with the rule; without it in m6 (`as_run`) |
| — | post-hoc analyses in [`results/post_hoc/`](../../results/post_hoc/README.md): the post-hoc sequence test (Methods A and B), AUROC bootstrap intervals, an epoch check | added after the outcomes were known | labelled post hoc everywhere; the sequence test and the AUROC intervals are not reported in the paper |

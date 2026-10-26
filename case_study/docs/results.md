# Guide to the results

This page is for readers who check or reuse the recorded results of the KITTI and nuScenes case study: the
outcome table, the folders and columns of `results/`, and where each value of the paper comes from.

Every folder in [`../results/`](../results/) holds the files one run wrote, unchanged, with its `provenance.json`
(script version, SHA-256 of the script and of every input, configuration) and a `summary.txt`. Each CSV row is one
**cell**: a threshold selected in the condition of selection (`established`, or `source`) and tested in the condition
of use (`applied`, or `target`), for one indicator, limit α and split. The files keep the names they were written with;
[`../../docs/glossary.md`](../../docs/glossary.md) maps them to the terms used here, and [`../../docs/concept.md`](../../docs/concept.md) explains the outcomes.
The [index at the end of this page](#paper-section-to-repository-index) lists, for each section, table and figure of the
paper, the files that hold its values.

## Outcomes over the five splits

Frame-level evaluation (division by frame, frame as the unit; Fig. 4 of the paper). Frames of one recorded sequence
are not independent, so the stated error probability is not guaranteed for these outcomes ([`concept.md`, section
5](../../docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence)). Counts over splits 0 to 4: **A** applicable, **N** not
applicable, **?** not determined, **-** no threshold selected; `?2 N3` means not determined on two and not applicable on
three splits. KITTI with the KITTI rule. The [results browser](https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/)
shows the same cells per split, together with the third run, the sequence-level evaluation and the post-hoc sequence
test (Method A). At 10⁻³ and 10⁻⁴ no threshold could be selected in any pair of conditions.
Sources: `division_by_frame/kitti_rule_dataset_change_weather/A_kitti_range_protocol.csv` (protocol `kitti_ignore`),
`division_by_frame/nuscenes_distance/matrix_all_variants.csv` (iou `A_iou0.5`, objects `car`, cut_q 0.5),
`division_by_frame/kitti_rule_dataset_change_weather/C_weather_nuscenes.csv`, `division_by_frame/kitti_rule_dataset_change_weather/B_shift_seeds_protocol.csv`
(protocol `kitti_ignore`).

| setting | transfer | u_s 10⁻² | u_s 0.05† | u_s 0.1† | u_e 10⁻² | u_e 0.05† | u_e 0.1† |
|---|---|---|---|---|---|---|---|
| KITTI distance | near → far | A1 ?3 N1 | N5 | N5 | A5 | ?3 N2 | N5 |
| KITTI distance | far → near | A4 ?1 | A5 | A5 | ?5 | A5 | A5 |
| nuScenes distance | near → far | A5 | A4 ?1 | N5 | A5 | A5 | N5 |
| nuScenes distance | far → near | ?5 | A2 ?3 | A5 | ?2 N3 | ?5 | A5 |
| nuScenes weather | clear → rain | ?2 -3 | ?5 | ?4 N1 | ?5 | ?4 N1 | ?1 N4 |
| nuScenes weather | rain → clear | -5 | A5 | A5 | A5 | A5 | A5 |
| change of dataset and detector | nuScenes → KITTI | N5 | N5 | N5 | A5 | A5 | A5 |
| change of dataset and detector | KITTI → nuScenes | A5 | A5 | A5 | ?5 | ?5 | ?5 |

`results/earlier_summaries/outcome_counts.csv` counts the outcomes over every variant of m2, m3 and m4, and
`results/earlier_summaries/failing_cells_primary.csv` lists every not applicable transfer of their primary variants. Both were written
before the KITTI rule and the five splits of the change of dataset and detector (m6): KITTI labels as run, the change of
dataset and detector on one split. The table above supersedes them.

## Runs

The folder names before version 2.0 are listed in [`../results/README.md`](../results/README.md).

| folder | run | content |
|---|---|---|
| `division_by_frame/kitti_distance_pilot` | m1 | KITTI distance with the blended score of the detection pipeline; variants of overlap (IoU 0.5, 0.7 for cars), object set (cars, all classes) and near/far boundary (quartiles 0.25, 0.5, 0.75); `frontier_primary.csv`: retention and bound against τ on the selection part |
| `division_by_frame/kitti_distance` | m2 | as m1, for the indicators u_s and u_e |
| `division_by_frame/nuscenes_distance` | m3 | nuScenes distance, u_s and u_e; overlap IoU 0.5 only; object set `car` or `vehicles`; boundary quantiles 0.25, 0.5, 0.75 |
| `division_by_frame/dataset_change_one_split` | m4 | change of dataset and detector, split 0, both indicators |
| `division_by_frame/kitti_rule_dataset_change_weather` | m6 | A: KITTI distance with (`kitti_ignore`) and without (`as_run`) the KITTI rule; B: change of dataset and detector on five splits, both label versions; C: nuScenes rain against clear weather |
| `division_by_sequence/nuscenes_by_scene` | m7 | nuScenes: `m3_frame`, `m6_frame`: reruns of the frame-level evaluation that reproduce m3 and m6 (`REPRO_PASSED.txt`); `m3_scene`, `m6_scene`: parts drawn by recorded scene, third run (`hb_unit` = `frame`) and sequence-level evaluation (`hb_unit` = `scene`); `m7_scene_split.csv`: the frame-level evaluation, the third run and the sequence-level evaluation side by side (`variant` = `frame`, `scene_frame_unit` = third run, `scene_scene_unit` = sequence-level evaluation); `m7_scene_split_summary.txt`: outcome codes per cell, with "(i)" for the third run and "(ii)" for the sequence-level evaluation, and scenes per part |
| `division_by_sequence/kitti_by_drive` | m8 | KITTI: `frame/`: rerun of the frame-level evaluation, equal to m6 A and B byte for byte (`REPRO_PASSED.txt`); `A_kitti_distance_drive.csv`, `B_dataset_drive.csv`: parts drawn by recorded drive (nuScenes side of B by scene), third run (`hb_unit` = `frame`) and sequence-level evaluation (`hb_unit` = `drive`); drives per part in `provenance.json` |
| `supporting_analyses` | tools | tables computed from the cached per-detection tables, listed below |
| `post_hoc` | post hoc | added after the parameters were fixed and the outcomes were known; not in the paper: [`../results/post_hoc/README.md`](../results/post_hoc/README.md) |

## Columns of the run files

| column | meaning |
|---|---|
| `indicator` | `u_s` spatial or `u_e` existence indicator (m1: the blended score `u`) |
| `iou` | overlap setting for correctness: `A_iou0.5` (IoU 0.5 for every class) or `B_car0.7` (0.7 for cars) |
| `objects` | evaluated object set: `Car`/`car`, `All` (KITTI) or `vehicles` (nuScenes) |
| `cut_q`, `cut_m` | quantile and distance (m) of the near/far boundary, from the grid part |
| `seed` | split 0 to 4 |
| `alpha` | limit α; `frozen_sweep` / `frozen` is true for the target limits 10⁻², 10⁻³, 10⁻⁴, false for the exploratory limits 0.05† and 0.1† |
| `established`, `applied` / `source`, `target` | condition of selection / condition of use |
| `protocol` | `kitti_ignore` with the KITTI rule, `as_run` without |
| `tau` | selected threshold τ (empty if none) |
| `A_hat` | estimate of the FAP (paper Eq. 2) on the test part of the condition of use |
| `hb_L`, `hb_U` | Hoeffding-Bentkus bounds L and U of the FAP, each at δ/2 = 0.025 (together an interval at confidence 0.95) |
| `boot_lo`, `boot_hi` | frame bootstrap percentile interval of A (descriptive, m1 and m4 only) |
| `R_hat` | retention: share of the correct detections of the condition of use that τ accepts |
| `outcome` | `applies` (applicable), `does not apply` (not applicable), `not determined`, `no threshold established` (no threshold selected) |
| `n_eval_frames`, `frames_eval` | frames of the condition of use in the test part (`eval`) |
| `frames_select`, `frames_select_near`, `frames_select_far` | frames of the selection part |
| `split`, `hb_unit` | how the parts were drawn (`frame`, `scene`, `drive`) and the unit of the test (`frame`, `scene`, `drive`); `split` ≠ `frame` with `hb_unit` = `frame` is the third run, `hb_unit` = `scene` or `drive` the sequence-level evaluation; files without these columns hold the frame-level evaluation |
| `n_select_units`, `n_eval_units` | units (frames, scenes or drives) of the selection and test parts |
| `setting`, `variant` (m7) | `distance` or `rain` (nuScenes weather); `frame` = frame-level evaluation, `scene_frame_unit` = third run, `scene_scene_unit` = sequence-level evaluation |

## Supporting analyses

Written by the scripts in [`../tools/supporting/`](../tools/supporting/) from the per-detection tables; each script
first checks the split-0 cells against the recorded run files.

| file | content |
|---|---|
| `retention_applicable_cells.csv` | every applicable cell of all pairs of conditions and splits with its retention; `in_fig_outcomes` / `in_fig_pairs` mark the cells of the outcome table above / of split 0 at 0.1† |
| `applicable_cells_1e-2.csv` | applicable cells at 10⁻² for the own, transferred and common thresholds, sorted by retention |
| `wrong_share_and_median_split0.csv` | per condition: detections, share of wrong ones, median indicator value of all, correct and wrong detections; all parts and test part of split 0 |
| `intervals_clear_to_rain.csv` | A, [L, U], R and outcome of every clear → rain cell in the frame-level evaluation, the third run and the sequence-level evaluation (`variant` as in m7) |
| `frames_per_condition.csv` | selection and test frames per condition and split |
| `common_threshold_outcomes.csv` | the common threshold τ* on the test part of each distance condition: A, [L, U], outcome, R(τ*), R(τ_c) and the retention gap G |
| `common_threshold_recorded.txt` | where τ* and G appear in the recorded run summaries |
| `merge_recall.csv`, `recall_denominators.json` | recall after the vote (correct car detections / annotated cars, before any uncertainty threshold), merge parameters, detector score cut-off per configuration; annotated nuScenes cars with and without a range and LiDAR-point filter |
| `roc_clear_rain_points.csv` | ROC operating points of the clear-weather thresholds (α = 10⁻², 0.1†) in clear weather and rain, with AUROC |
| `retention_vs_false_acceptance_curve.csv`, `..._selected.csv` | R against A over τ for nuScenes near distance, u_e, test part of split 0, and the thresholds selected at 10⁻², 0.05†, 0.1† |
| `unannotated_wrong_boxes.csv` | accepted wrong KITTI car detections (split-0 near threshold, 0.1†) with no annotated car within 3D IoU 0.1, fully inside the camera image |
| `frame_rule_candidates.csv`, `frame_rule_choice.txt`, `frame_candidates_ranked.csv`, `nuscenes_frame_wrong_boxes.csv`, `blind_sample_50.csv` | selection of frames by a fixed rule for `tools/figures/frame_figure.py` (KITTI 004289, nuScenes 703ac7e5), and the ranked KITTI candidates from which the authors chose frame 005345 for Fig. 1 of the paper (`frame_candidates_ranked.csv`); the nuScenes frame of Fig. 1 is in `fig1b_candidates.csv` |
| `fig_separation_curves.csv` | data of Fig. 5 of the paper: ROC curves, operating points of the transferred thresholds, A against τ and the HB bounds at the 0.1† threshold, per condition; written by `tools/figures/paper/separation_curves.py` |
| `fig1_two_panel_facts.txt`, `fig1b_candidates.csv` | facts of the two frames of Fig. 1 (KITTI 005345, nuScenes scene-0626) and the ranked nuScenes candidates; written by `tools/figures/paper/frame_figure/` |
| `m8_outcome_counts.csv`, `m8_drives_per_part.csv` | outcome counts of the third run and the sequence-level evaluation on KITTI drives, and drives and frames per part and condition; written by `tools/supporting/m8_tables.py` |
| `distance_bins_log.txt` | accepted correct and wrong detections per 5 m distance bin under the near-distance threshold (split 0, 0.1†); console output of `tools/figures/make_figures.py causes` |
| `table_and_figure_values.json` | frame counts per condition and part, shares of wrong detections, split-0 values of the pair figure |
| `*_log.txt` | console output of each script |

## Paper section to repository index

Where each part of the submitted paper is explained and which files hold its values. Paths are relative to the
repository root. [`paper_map.md`](paper_map.md) lists single numbers with their file and filter.

| paper | explained in | files |
|---|---|---|
| Sect. 1, Fig. 1 (two frames) | [`concept.md`, section 1](../../docs/concept.md#1-from-the-acceptance-criterion-to-a-measure) | `results/supporting_analyses/fig1_two_panel_facts.txt`, `fig1b_candidates.csv`, `frame_candidates_ranked.csv`; scripts in `tools/figures/paper/frame_figure/` |
| Sect. 3.1, Eq. 1 to 3 (indicators, per-frame share, FAP, retention) | [`concept.md`, section 2](../../docs/concept.md#2-what-is-measured-per-frame-share-fap-and-pooled-share); [`method.md`, sections 1 and 3](method.md#3-per-frame-share-fap-and-retention-paper-sect-31-eq-2) | `experiments/m2_indicators_kitti.py`, `experiments/m3_range_nuscenes.py` (u_s, u_e); `Cell` in `experiments/m1_range_kitti.py` |
| Sect. 3.2, Eq. 4 (HB p-value, fixed-sequence selection, recording mix) | [`concept.md`, sections 2 and 3](../../docs/concept.md#3-selecting-a-threshold-and-testing-it) | `hb_pvalue`, `chain_index` in `experiments/m1_range_kitti.py` |
| Sect. 3.3 (interval, outcome, own-condition check) | [`concept.md`, sections 3 and 6](../../docs/concept.md#6-the-own-condition-check) | `hb_upper`, `hb_lower` in `experiments/m1_range_kitti.py` |
| Sect. 3.4 (four changes in the detections) | [`concept.md`, section 4](../../docs/concept.md#4-four-changes-in-the-detections-and-which-one-auroc-shows) | see Table 4 below |
| Sect. 3.5, Eq. 5 (zero-failure bound) | [`concept.md`, section 5](../../docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence) | `n_required` in `experiments/m1_range_kitti.py` |
| Fig. 2, Fig. 3 (schematics) | [`../tools/figures/paper/README.md`](../tools/figures/paper/README.md) | `tools/figures/paper/fig_concept.tex`, `fig_parts.tex` |
| Sect. 4.1 (detectors, vote) | [`method.md`, section 1](method.md#1-detector-detections-and-indicators-paper-sect-31-41) | `results/supporting_analyses/merge_recall.csv`, `recall_denominators.json`; `results/post_hoc/epoch_check.txt` (post hoc) |
| Sect. 4.2 (conditions, KITTI rule) | [`method.md`, section 2](method.md#2-conditions-paper-sect-42-table-3) | `results/division_by_frame/kitti_rule_dataset_change_weather/provenance.json` (`A.ignored_total`); `results/post_hoc/ns_per_condition.csv` (rain scenes) |
| Table 3 (pairs of conditions) | [`method.md`, section 2](method.md#2-conditions-paper-sect-42-table-3) | frames per part: `results/supporting_analyses/frames_per_condition.csv`; car detections: `wrong_share_and_median_split0.csv`; annotated cars and recall after the vote: `merge_recall.csv`; boundaries: `table_and_figure_values.json`; validation frames: `results/division_by_sequence/kitti_by_drive/provenance.json`, `results/post_hoc/provenance.json` |
| Sect. 4.3 (division, unit, the two evaluations and the third run) | [`concept.md`, section 5](../../docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence); [`method.md`, section 6](method.md#6-division-by-recorded-sequence-and-the-unit-of-the-test-paper-sect-35-43) | `results/division_by_sequence/nuscenes_by_scene/m7_scene_split_summary.txt` (scenes per part), `results/supporting_analyses/m8_drives_per_part.csv` (drives per part) |
| Sect. 4.4 (limits, error probability, predictions) | [`study_protocol/`](study_protocol/README.md) | `docs/study_protocol/predictions_frozen_2026-10-01.md`, `outcomes_and_deviations.md` |
| Sect. 5.1, Fig. 4 (RQ1) | [outcome table above](#outcomes-over-the-five-splits); [results browser](https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/) | frame-level evaluation: `results/division_by_frame/kitti_rule_dataset_change_weather/A_kitti_range_protocol.csv`, `B_shift_seeds_protocol.csv`, `C_weather_nuscenes.csv`, `results/division_by_frame/nuscenes_distance/matrix_all_variants.csv`; retention: `results/supporting_analyses/retention_applicable_cells.csv`; third run, sequence-level evaluation and own-condition check: `results/division_by_sequence/nuscenes_by_scene/m7_scene_split.csv`, `results/division_by_sequence/kitti_by_drive/*.csv`; KITTI rule check: `protocol` = `as_run` in m6; figure source: `tools/figures/paper/make_fig_outcomes.py` |
| Table 4, Sect. 5.2 (RQ2) | [`concept.md`, section 4](../../docs/concept.md#4-four-changes-in-the-detections-and-which-one-auroc-shows) | shares of wrong detections and medians: `results/supporting_analyses/wrong_share_and_median_split0.csv`; AUROC (point estimates) of KITTI distance, weather and datasets: column `point` of `results/post_hoc/auroc_bootstrap.csv`, and `fig_separation_curves.csv`; AUROC of nuScenes distance: `results/division_by_frame/nuscenes_distance/summary.txt`; FAP in clear weather and rain: `results/division_by_frame/kitti_rule_dataset_change_weather/C_weather_nuscenes.csv`; pooled share in clear weather and rain: from the counts and operating points in `roc_clear_rain_points.csv`; accepted correct and wrong detections per distance bin: `distance_bins_log.txt` |
| Fig. 5 (separation) | [`../tools/figures/paper/README.md`](../tools/figures/paper/README.md) | `results/supporting_analyses/fig_separation_curves.csv`; `tools/figures/paper/make_fig_separation.py` |
| Sect. 5.3, Fig. 6 (RQ3, units) | [`concept.md`, section 5](../../docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence) | `results/supporting_analyses/frames_per_condition.csv`, `results/division_by_sequence/nuscenes_by_scene/m7_scene_split_summary.txt`, `results/supporting_analyses/m8_drives_per_part.csv`; splits without a threshold: `C_weather_nuscenes.csv`; figure source: `tools/figures/paper/fig_units.tex` |
| Sect. 6.1, Table 5 (outcome, meaning, measure; common threshold) | [`concept.md`, section 1](../../docs/concept.md#1-from-the-acceptance-criterion-to-a-measure) | `results/supporting_analyses/common_threshold_outcomes.csv` |
| Sect. 6.2 (limits of the study) | [`concept.md`, section 7](../../docs/concept.md#7-what-the-study-does-not-show) | `results/supporting_analyses/unannotated_wrong_boxes.csv`, `frame_candidates_log.txt`; `results/post_hoc/epoch_check.txt` (post hoc) |
| supplementary material | | [`supplementary/supplementary.pdf`](supplementary/supplementary.pdf) |

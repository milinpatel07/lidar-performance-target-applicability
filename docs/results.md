# Guide to the results

Every folder in [`results/`](../results/) holds the files one run wrote, unchanged, with its `provenance.json`
(script version, SHA-256 of the script and of every input, configuration) and a `summary.txt`. Each CSV row is one
**cell**: a threshold selected in the condition of selection (`established`, or `source`) and tested in the condition
of use (`applied`, or `target`), for one indicator, limit α and split. The files keep the names they were written with;
[`glossary.md`](glossary.md) maps them to the terms used here.

## Outcomes over the five splits

Division by frame, frame as the unit (Fig. 4 of the paper). Counts over splits 0 to 4: **A** applicable, **N** not
applicable, **?** not determined, **-** no threshold selected; `?2 N3` means not determined on two and not applicable on
three splits. KITTI with the KITTI rule. The [results browser](https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/)
shows the same cells per split, with the division by recorded sequence and the post-hoc test. At 10⁻³ and 10⁻⁴ no threshold could be selected in any setting.
Sources: `m6_protocol_seeds_weather/A_kitti_range_protocol.csv` (protocol `kitti_ignore`),
`m3_range_nuscenes/matrix_all_variants.csv` (iou `A_iou0.5`, objects `car`, cut_q 0.5),
`m6_protocol_seeds_weather/C_weather_nuscenes.csv`, `m6_protocol_seeds_weather/B_shift_seeds_protocol.csv`
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

`results/outcome_counts.csv` counts the outcomes over every variant of m2, m3 and m4, and
`results/failing_cells_primary.csv` lists every not applicable transfer of their primary variants. Both were written
before the KITTI rule and the five splits of the change of dataset and detector (m6): KITTI labels as run, the change of
dataset and detector on one split. The table above supersedes them.

## Runs

| folder | run | content |
|---|---|---|
| `m1_range_kitti` | m1 | KITTI distance with the blended score of the detection pipeline; variants of overlap (IoU 0.5, 0.7 for cars), object set (cars, all classes) and near/far boundary (quartiles 0.25, 0.5, 0.75); `frontier_primary.csv`: retention and bound against τ on the selection part |
| `m2_indicators_kitti` | m2 | as m1, for the indicators u_s and u_e |
| `m3_range_nuscenes` | m3 | nuScenes distance, u_s and u_e; overlap IoU 0.5 only; object set `car` or `vehicles`; boundary quantiles 0.25, 0.5, 0.75 |
| `m4_dataset_shift` | m4 | change of dataset and detector, split 0, both indicators |
| `m6_protocol_seeds_weather` | m6 | A: KITTI distance with (`kitti_ignore`) and without (`as_run`) the KITTI rule; B: change of dataset and detector on five splits, both label versions; C: nuScenes rain against clear weather |
| `m7_scene_split` | m7 | `m3_frame`, `m6_frame`: frame-split reruns that reproduce m3 and m6 (`REPRO_PASSED.txt`); `m3_scene`, `m6_scene`: parts drawn by recorded scene, variants (i) and (ii); `m7_scene_split.csv`: all three side by side; `m7_scene_split_summary.txt`: outcome codes per cell and scenes per part |
| `m8_kitti_drive_split` | m8 | `frame/`: frame-split rerun equal to m6 A and B byte for byte (`REPRO_PASSED.txt`); `A_kitti_distance_drive.csv`, `B_dataset_drive.csv`: KITTI parts drawn by recorded drive (nuScenes side of B by scene), variants (i) and (ii); drives per part in `provenance.json` |
| `supporting_analyses` | tools | tables computed from the cached per-detection tables, listed below |
| `post_hoc` | post-hoc | added after the parameters were fixed: [`results/post_hoc/README.md`](../results/post_hoc/README.md) |

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
| `A_hat` | false acceptance proportion A of Eq. 1 on the test part of the condition of use |
| `hb_L`, `hb_U` | one-sided Hoeffding-Bentkus bounds L and U of A, each at δ/2 = 0.025 (together an interval at confidence 0.95) |
| `boot_lo`, `boot_hi` | frame bootstrap percentile interval of A (descriptive, m1 and m4 only) |
| `R_hat` | retention: share of the correct detections of the condition of use that τ accepts |
| `outcome` | `applies` (applicable), `does not apply` (not applicable), `not determined`, `no threshold established` (no threshold selected) |
| `n_eval_frames`, `frames_eval` | frames of the condition of use in the test part (`eval`) |
| `frames_select`, `frames_select_near`, `frames_select_far` | frames of the selection part |
| `split`, `hb_unit` | how the parts were drawn (`frame`, `scene`, `drive`) and the unit of the test (`frame`, `scene`, `drive`) |
| `n_select_units`, `n_eval_units` | units (frames, scenes or drives) of the selection and test parts |
| `setting`, `variant` (m7) | `distance` or `rain`; `frame`, `scene_frame_unit` (i), `scene_scene_unit` (ii) |

## Supporting analyses

Written by the scripts in [`tools/supporting/`](../tools/supporting/) from the per-detection tables; each script
first checks the split-0 cells against the recorded run files.

| file | content |
|---|---|
| `retention_applicable_cells.csv` | every applicable cell of all settings and splits with its retention; `in_fig_outcomes` / `in_fig_pairs` mark the cells of the outcome table above / of split 0 at 0.1† |
| `applicable_cells_1e-2.csv` | applicable cells at 10⁻² for the own, transferred and common thresholds, sorted by retention |
| `wrong_share_and_median_split0.csv` | per condition: detections, share of wrong ones, median indicator value of all, correct and wrong detections; all parts and test part of split 0 |
| `intervals_clear_to_rain.csv` | A, [L, U], R and outcome of every clear → rain cell, frame split and both scene variants |
| `frames_per_condition.csv` | selection and test frames per condition and split |
| `common_threshold_outcomes.csv` | the common threshold τ* on the test part of each distance condition: A, [L, U], outcome, R(τ*), R(τ_c) and the retention gap G |
| `common_threshold_recorded.txt` | where τ* and G appear in the recorded run summaries |
| `merge_recall.csv`, `recall_denominators.json` | recall of the 3-of-4 merge before thresholding (correct car detections / annotated cars), merge parameters, detector score cut-off per configuration; annotated nuScenes cars with and without a range and LiDAR-point filter |
| `roc_clear_rain_points.csv` | ROC operating points of the clear-weather thresholds (α = 10⁻², 0.1†) in clear weather and rain, with AUROC |
| `retention_vs_false_acceptance_curve.csv`, `..._selected.csv` | R against A over τ for nuScenes near distance, u_e, test part of split 0, and the thresholds selected at 10⁻², 0.05†, 0.1† |
| `unannotated_wrong_boxes.csv` | accepted wrong KITTI car detections (split-0 near threshold, 0.1†) with no annotated car within 3D IoU 0.1, fully inside the camera image |
| `frame_rule_candidates.csv`, `frame_rule_choice.txt`, `frame_candidates_ranked.csv`, `nuscenes_frame_wrong_boxes.csv`, `blind_sample_50.csv` | selection of frames by a fixed rule for `tools/figures/frame_figure.py` (KITTI 004289, nuScenes 703ac7e5), and the ranked KITTI candidates from which the authors chose frame 005345 for Fig. 1 of the paper (`frame_candidates_ranked.csv`); the nuScenes frame of Fig. 1 is in `fig1b_candidates.csv` |
| `fig_separation_curves.csv` | data of Fig. 5 of the paper: ROC curves, operating points of the transferred thresholds, A against τ and the HB bounds at the 0.1† threshold, per condition; written by `tools/figures/paper/separation_curves.py` |
| `fig1_two_panel_facts.txt`, `fig1b_candidates.csv` | facts of the two frames of Fig. 1 (KITTI 005345, nuScenes scene-0626) and the ranked nuScenes candidates; written by `tools/figures/paper/frame_figure/` |
| `m8_outcome_counts.csv`, `m8_drives_per_part.csv` | outcome counts of the division by KITTI drive, and drives and frames per part and condition; written by `tools/supporting/m8_tables.py` |
| `distance_bins_log.txt` | accepted correct and wrong detections per 5 m distance bin under the near-distance threshold (split 0, 0.1†); console output of `tools/figures/make_figures.py causes` |
| `table_and_figure_values.json` | frame counts per condition and part, shares of wrong detections, split-0 values of the pair figure |
| `*_log.txt` | console output of each script |

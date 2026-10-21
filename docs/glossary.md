# Glossary

One vocabulary for the whole repository. The left column is the term used in the documentation and in the paper; the
right column gives the name the term has in the result files and scripts, which were written before the final wording
was fixed and keep their original names so that their SHA-256 hashes stay valid.

## Safety terms (ISO 21448, SOTIF)

| term | meaning | in the files |
|---|---|---|
| acceptance criterion | criterion representing the absence of an unreasonable level of risk, set at vehicle level (ISO 21448) | not used |
| performance target | element-level requirement on the detector, here A_c(τ) ≤ α (see FAP) | not used |
| limit α | the value a performance target must not exceed | `alpha` |
| target limit | α = 10⁻², 10⁻³ or 10⁻⁴, fixed before the first run | `frozen_sweep` / `frozen` = true; `limit` = `target` |
| exploratory limit, marked † | α = 0.05 or 0.1, fixed at the same time to show which outcomes the data can decide; **not a safety target** | `frozen_sweep` / `frozen` = false; `limit` = `exploratory` |
| triggering condition (TC) | ISO 21448 term for a specific condition of a scenario that can initiate a hazardous behaviour. Far distance and rain are treated as potential TCs because both act on the point cloud; near distance and clear weather are **not** TCs, they are the conditions the thresholds are compared with. The study does not show that any condition initiates a hazardous behaviour | not used |
| condition | one value of a property that divides the data: near / far distance, clear / rain weather, KITTI / nuScenes | `near`, `far`, `clear`, `rain`, `kitti`/`KITTI`, `nuscenes`/`nuScenes` |
| pair of conditions | the two conditions of one change: KITTI distance, nuScenes distance, nuScenes weather, change of dataset and detector | `setting` (m7: `distance`, `rain`) |
| change of dataset and detector, also **control** | KITTI with the ensemble trained on KITTI against nuScenes with the ensemble trained on nuScenes; both the data and the detector change | m4, m6 part B, m8 part B; older names "change of dataset", "dataset shift" |

## Detections and indicators

| term | meaning | in the files |
|---|---|---|
| ensemble member | one of four PointPillars networks of one dataset, trained separately with a different random seed | `seed1` … `seed4` in configuration names |
| detection | merged box: the member boxes matched at 3D IoU 0.5, kept if at least 3 of 4 members contribute | one row of the per-detection table |
| correct / wrong detection | matched one-to-one to an annotated car at 3D IoU ≥ 0.5 / not matched | `y` = 1 / 0 (`y_A_iou0.5`) |
| spatial indicator u_s | 1 − mean pairwise rotated 3D IoU of the member boxes | `u_s` |
| existence indicator u_e | 1 − mean member confidence, 0 for a member without a box | `u_e` |
| blended score u | weighted sum of box and confidence spread from the detection pipeline; used only in m1 | `u` (m1) |
| threshold τ | a detection is **accepted** if u ≤ τ and **rejected** if u > τ | `tau` |
| τ_c | the threshold selected in condition c | `tau` |
| false acceptance | accepted wrong detection | — |
| withheld detection | rejected correct detection | — |
| KITTI rule | wrong KITTI detections whose image box lies more than half inside a DontCare region, or that match a van at 3D IoU 0.5, are excluded (2,454 detections) | `protocol` = `kitti_ignore` (with the rule) / `as_run` (without) |

## Quantities

| term | meaning | in the files |
|---|---|---|
| per-frame FAP a_f(τ) | in frame f, the share of accepted detections of the condition that are wrong; 0 if nothing is accepted | — |
| FAP A_c(τ) | false acceptance proportion: the mean of a_f(τ) over the frames of condition c (Eq. 1 of the paper). A proportion, not a rate | `A_hat` (estimate on the test part) |
| pooled share | share of wrong detections among all accepted detections of a condition taken together; differs from the FAP | — |
| share of wrong detections | wrong detections / all car detections of a condition, before any threshold | `share_wrong` |
| retention R_c(τ) | share of the correct detections of condition c that τ accepts | `R_hat` |
| separation, AUROC | how well the indicator orders wrong above correct detections; area under the ROC curve with wrong detections as the positive class | `auroc` |
| operating point | the pair (share of correct detections withheld, share of wrong detections rejected) that a threshold marks on the ROC curve | `correct_rejected`, `wrong_rejected` |
| common threshold τ* | one threshold selected for both distance conditions at once (each tested at δ/2) | `star`, `tau_star` |
| retention gap G | R_c(τ_c) − R_c(τ*): correct detections that knowing the condition at run time would keep | `G` |

## Data division and units

| term | meaning | in the files |
|---|---|---|
| grid part | 10 % of the data; fixes the 100 candidate thresholds (percentiles of the indicator) and the near/far boundary | code 0 |
| selection part | 45 % of the data; selects τ_c | `select`, code 1 |
| test part | 45 % of the data; decides the outcome | `eval`, `evaluation part`, code 2 |
| halves | for the change of dataset and detector each dataset is divided into a selection half and a test half; candidates 0.01, 0.02, …, 1.00 | m4 `frac_select` 0.5 |
| split | one of five random divisions of the same data, drawn with seed 0 to 4 | `seed` |
| division by frame | each frame is drawn into a part on its own | `split` = `frame`, m7 `variant` = `frame` |
| division by recorded sequence | whole recorded sequences are drawn into parts | `split` = `scene` / `drive`; m7 `variant` = `scene_frame_unit` or `scene_scene_unit` |
| recorded sequence | a nuScenes scene (150 in the validation set) or a KITTI drive (45 in the validation frames) | `scene`, `drive` |
| independent unit | what the test treats as one independent draw: the frame, or the recorded sequence | `hb_unit` = `frame` / `scene` / `drive`; `n_select_units`, `n_eval_units` |
| variant (i) | division by recorded sequence, frame as unit | `scene_frame_unit`, `hb_unit` = `frame` |
| variant (ii) | division by recorded sequence, sequence as unit; the loss of a sequence is the mean of a_f over its frames in the condition | `scene_scene_unit`, `hb_unit` = `scene`/`drive` |
| minimum number of units | n ≥ ln δ′ / ln(1 − α): units without any false acceptance needed to show a limit met at error probability δ′ (Eq. 4); δ′ = δ for selection, δ/2 for the test | — |

## Statistics and outcomes

| term | meaning | in the files |
|---|---|---|
| δ | error probability, 0.05 | `delta` |
| LTT | Learn then Test (Angelopoulos et al., Ann. Appl. Stat. 2025): selection of a threshold by multiple testing with a guarantee on the family-wise error | — |
| HB | Hoeffding–Bentkus p-value and bounds for the mean of losses in [0, 1] | `hb_*` |
| fixed sequence | candidates are tested from the lowest upwards; τ_c is the last candidate that passes before the first that fails | — |
| [L, U] | one-sided HB bounds of A_{c'}(τ_c) at δ/2 each, together an interval at confidence 1 − δ | `hb_L`, `hb_U` |
| condition of selection c | the condition in which τ_c was selected | `established`, `source` |
| condition of use c′ | the condition in which τ_c is tested | `applied`, `target` |
| transfer | a threshold used in a condition of use other than its condition of selection (c′ ≠ c) | `established` ≠ `applied` |
| own condition | the threshold tested in its own condition of selection (c′ = c); a check of the selection | `established` = `applied`, `own_condition` |
| **applicable** | U ≤ α: the target is met in c′, wrong with probability at most δ/2 | `applies` (older files), `applicable` |
| **not applicable** | L > α: the target is exceeded in c′, wrong with probability at most δ/2 | `does not apply`, `not applicable` |
| **not determined** | L ≤ α < U: the data do not decide | `not determined` |
| **no threshold selected** | no candidate passed in c | `no threshold established`, `no threshold selected` |
| outcome codes | **A** applicable, **N** not applicable, **?** not determined, **-** no threshold selected; one character per split, e.g. `?2 N3` = not determined on 2 and not applicable on 3 of 5 splits | `A`, `N`, `?`, `-` |
| post-hoc | added after the parameters were fixed and the outcomes known; see [`results/post_hoc/`](../results/post_hoc/) | — |

## Names of runs and versions

| name | meaning |
|---|---|
| m1 … m8 | the experiment runs in the order they were made: m1 KITTI distance with the blended score (precursor); m2 KITTI distance with u_s, u_e; m3 nuScenes distance; m4 change of dataset and detector, one split; m6 KITTI rule, five splits of the control, nuScenes weather; m7 division by nuScenes scene; m8 division by KITTI drive. **m5** was the frame figure and has no result folder |
| `seq_ratio` | the post-hoc sequence-level test (Methods A and B) |
| `SCRIPT_VERSION` (e.g. `m3-0.4`) | version label inside each script, recorded in each run's `provenance.json`; [`analysis/SCRIPT_VERSIONS.md`](../analysis/SCRIPT_VERSIONS.md) maps runs to shipped files |
| `export-v13.1`, `export-1.1` | version labels of the per-detection table cache: `export-v13.1` on the recorded cache from which the supporting analyses, the figure data and the post-hoc analysis were computed; `export-1.1` on `tools/export_tables.py`, the repository version of the same builder. Each tool checks its split-0 values against `results/` before it writes anything |
| v24, v25 | labels of internal analysis rounds that appear in some script headers and logs (for example `v25f5-0.2`); they carry no meaning beyond the date order |
| `RUM`, `/rum` | folder of the detector outputs and dataset files that the scripts read (named after the runtime-monitoring project that produced the detector outputs) |

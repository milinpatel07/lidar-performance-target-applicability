# Glossary

One vocabulary for the whole repository, for looking up a term or the name of a column. The left column is the term of the paper and of this documentation; the
right column gives the name the term has in the result files and scripts, which were written before the final wording
was fixed and keep their original names so that their SHA-256 hashes stay valid. How the terms fit together:
[`concept.md`](concept.md).

## Safety terms (ISO 21448, SOTIF)

| term | meaning | in the files |
|---|---|---|
| acceptance criterion | criterion representing the absence of an unreasonable level of risk, set at vehicle level (ISO 21448) | not used |
| performance target | element-level requirement on the detector, here A_c(τ) ≤ α (see FAP) | not used |
| limit α | the value the FAP must not exceed under a performance target | `alpha` |
| target limit | α = 10⁻², 10⁻³ or 10⁻⁴; these define the performance targets. Fixed and recorded with a date in version control before any outcome was computed | `frozen_sweep` / `frozen` = true; `limit` = `target` |
| exploratory limit, marked † | α = 0.05 or 0.1, fixed at the same time to show at which limits the test reaches the outcome applicable or not applicable; an exploratory limit **defines no performance target** | `frozen_sweep` / `frozen` = false; `limit` = `exploratory` |
| triggering condition (TC) | ISO 21448 term for a specific condition of a scenario that initiates a system reaction contributing to a hazardous behaviour. Far distance and rain are treated as potential TCs because both act on the point cloud; near distance and clear weather are not treated as TCs. The study does not show that any condition initiates a hazardous behaviour | not used |
| condition | near or far distance, clear weather or rain, or one dataset together with its trained detector | `near`, `far`, `clear`, `rain`, `kitti`/`KITTI`, `nuscenes`/`nuScenes` |
| pair of conditions | the two conditions of one change: KITTI distance, nuScenes distance, nuScenes weather, change of dataset and detector | `setting` (m7: `distance`, `rain`) |
| change of dataset and detector, also **control** | KITTI with the ensemble trained on KITTI against nuScenes with the ensemble trained on nuScenes; data and detector change together | m4, m6 part B, m8 part B; older names "change of dataset", "dataset shift" |

## Detections and indicators

| term | meaning | in the files |
|---|---|---|
| ensemble member | one of four PointPillars networks of one dataset, trained with a different random seed | `seed1` … `seed4` in configuration names |
| detection | merged box: the car boxes of the first member, in descending order of confidence, each joined by the unused car box of every other member with the highest IoU, if that IoU is at least 0.5 | one row of the per-detection table |
| vote | the rule that a detection is formed only if at least three of the four members contribute a box; itself a rejection rule applied before any uncertainty threshold | `consensus_threshold` = 3 of `members_K` = 4 in `case_study/results/supporting_analyses/merge_recall.csv` |
| recall after the vote | share of all annotated cars (no distance or visibility filter) that a detection after the vote matches; 0.858 on KITTI, 0.398 on nuScenes (paper, Table 3) | `recall` in `merge_recall.csv` |
| correct / wrong detection | assigned one-to-one to an annotated car at 3D IoU ≥ 0.5 / not assigned | `y` = 1 / 0 (`y_A_iou0.5`) |
| spatial indicator u_s | 1 − mean pairwise rotated 3D IoU of the contributing member boxes (Eq. 1 of the paper) | `u_s` |
| existence indicator u_e | 1 − mean member confidence, 0 for a member without a box | `u_e` |
| blended score u | weighted sum of box and confidence spread from the detection pipeline; used only in m1 | `u` (m1) |
| threshold τ | a detection is **accepted** if u ≤ τ and **rejected** if u > τ | `tau` |
| τ_c | the threshold selected in condition c | `tau` |
| false acceptance | accepted wrong detection | |
| withheld | a rejected correct detection | |
| KITTI rule | wrong KITTI detections whose image box lies more than half inside a DontCare region, or that match a van at 3D IoU 0.5, are excluded (2,454 detections) | `protocol` = `kitti_ignore` (with the rule) / `as_run` (without) |

## Quantities

| term | meaning | in the files |
|---|---|---|
| per-frame share a_f(τ) | in frame f, the share of false acceptances among the accepted detections of the condition; 0 if nothing is accepted (Eq. 2 of the paper) | |
| FAP A_c(τ) | false acceptance proportion: the expectation of a_f(τ) over the frames of condition c (Eq. 2 of the paper); a proportion, not a rate | `A_hat` (estimate on the test part) |
| pooled share | share of wrong detections among all accepted detections of a condition taken together; every accepted detection has equal weight, whereas the FAP gives every frame equal weight | |
| share of wrong detections | wrong detections / all car detections of a condition, before any threshold | `share_wrong` |
| retention R_c(τ) | share of the correct detections of condition c that τ accepts; reported with every applicable outcome because of Eq. 3 ([concept](concept.md#2-what-is-measured-per-frame-share-fap-and-pooled-share)) | `R_hat` |
| separation, AUROC | how well the indicator orders wrong above correct detections; area under the ROC curve with wrong detections as the positive class. The paper reports point estimates; the intervals in `case_study/results/post_hoc/auroc_bootstrap.csv` are post hoc | `auroc` |
| operating point | the pair (share of correct detections withheld, share of wrong detections rejected) that a threshold marks on the ROC curve | `correct_rejected`, `wrong_rejected` |
| common threshold τ* | one threshold that passes the selection in both distance conditions, each at δ/2 | `star`, `tau_star` |
| retention gap G | R_c(τ_c) − R_c(τ*): correct detections that knowing the condition at run time would keep | `G` |

## Data division and units

| term | meaning | in the files |
|---|---|---|
| grid part | 10 % of the data; fixes the 100 candidate thresholds (quantiles of the indicator) and the near/far boundary | code 0 |
| selection part | 45 % of the data; selects τ_c | `select`, code 1 |
| test part | 45 % of the data; gives the outcome | `eval`, `evaluation part`, code 2 |
| halves | for the change of dataset and detector each dataset is divided into a selection half and a test half; candidates 0.01, 0.02, …, 1.00 | m4 `frac_select` 0.5 |
| split | one of five random assignments of the same frames to the parts, drawn with seeds 0 to 4 | `seed` |
| recorded sequence | a continuous recording: a nuScenes scene (150 in the validation set) or a KITTI drive (45 in the validation frames) | `scene`, `drive` |
| unit | what the test treats as one independent draw: a frame or a recorded sequence | `hb_unit`; `n_select_units`, `n_eval_units` |
| frame-level evaluation | division by frame, each frame one unit; shown in Fig. 4 of the paper | run files of m1 to m6 (no `split` column); m7 `variant` = `frame`; `division_by_sequence/kitti_by_drive/frame/` |
| sequence-level evaluation | division by recorded sequence, each sequence one unit; the value of a sequence is the mean of a_f over its frames in the condition | m7 `variant` = `scene_scene_unit` (printed "(ii)" in `m7_scene_split_summary.txt`); `hb_unit` = `scene` (m3, m6 under `division_by_sequence/nuscenes_by_scene/`) or `drive` (m8) |
| third run | division by recorded sequence, frame as unit; separates the effect of the division from that of the unit | m7 `variant` = `scene_frame_unit` (printed "(i)"); `split` = `scene` or `drive` with `hb_unit` = `frame` |
| zero-failure bound (rule of three) | n ≥ ln δ′ / ln(1 − α): independent units without any false acceptance needed to show a limit met at error probability δ′ (Eq. 5 of the paper); δ′ = δ for selecting, δ/2 for testing; about 3/α at δ′ = 0.05 | `n_required` in `case_study/experiments/m1_range_kitti.py` |

## Statistics and outcomes

| term | meaning | in the files |
|---|---|---|
| δ | error probability, 0.05 | `delta` |
| LTT | Learn then Test (Angelopoulos et al.): selection of a threshold by multiple testing with a finite-sample guarantee | |
| HB | Hoeffding–Bentkus p-value and bounds for the mean of per-unit values in [0, 1] | `hb_pvalue`, `hb_upper`, `hb_lower`; columns `hb_*` |
| passes / fails | a candidate threshold passes if its HB p-value for the null hypothesis A_c(τ_j) > α is at most δ, and fails otherwise | |
| fixed sequence | candidates are taken from the lowest upwards; τ_c is the last candidate that passes before the first that fails | `chain_index` |
| [L, U] | lower and upper HB bound of A_{c'}(τ_c), each at δ/2, together an interval at confidence 1 − δ | `hb_L`, `hb_U` |
| condition of selection c | the condition in which τ_c was selected | `established`, `source` |
| condition of use c′ | the condition in which τ_c is tested | `applied`, `target` |
| transfer | a threshold used in a condition of use other than its condition of selection (c′ ≠ c) | `established` ≠ `applied` |
| own condition | the threshold tested in its own condition of selection (c′ = c); a check of the selection | `established` = `applied`, `own_condition` |
| outcome | applicable, not applicable, not determined or no threshold selected; meaning and measure: [concept](concept.md#1-from-the-acceptance-criterion-to-a-measure) | `outcome` |
| **applicable** | U ≤ α; erroneous with probability at most δ/2 if the test units are independent | `applies` (older files), `applicable` |
| **not applicable** | L > α; erroneous with probability at most δ/2 if the test units are independent | `does not apply`, `not applicable` |
| **not determined** | L ≤ α < U; makes no claim, and an exceeded limit can lie behind it | `not determined` |
| **no threshold selected** | the lowest candidate fails in the condition of selection | `no threshold established`, `no threshold selected` |
| outcome codes | **A** applicable, **N** not applicable, **?** not determined, **-** no threshold selected; counts over the five splits, e.g. `?2 N3` = not determined on 2 and not applicable on 3 splits | `A`, `N`, `?`, `-` |
| post hoc | added after the parameters were fixed and the outcomes known; not in the paper unless stated. See [`case_study/results/post_hoc/`](../case_study/results/post_hoc/README.md) | |
| post-hoc sequence test (Method A) | post-hoc test with the recorded sequence as unit that keeps the per-frame target through a transformed per-sequence value; not the sequence-level evaluation of the paper | `seq_ratio`, `method` = `A`; REPORT.md calls it "sequence-level test" |
| Method B | post-hoc check of the test step of Method A with a betting confidence interval | `method` = `B` |

## Names of runs and versions

The scripts, file headers and `provenance.json` files of the case study name the runs by an ID; the result folders
are named by content ([`../case_study/README.md`](../case_study/README.md#where-each-result-is) maps one to the other).

| name | meaning |
|---|---|
| m1 … m8 | the experiment runs in the order they were made: m1 KITTI distance with the blended score (precursor); m2 KITTI distance with u_s, u_e; m3 nuScenes distance; m4 change of dataset and detector, one split; m6 KITTI rule, five splits of the control, nuScenes weather; m7 third run and sequence-level evaluation on nuScenes scenes; m8 the same on KITTI drives. **m5** was the frame figure and has no result folder |
| `seq_ratio` | the post-hoc sequence test (Methods A and B) and the post-hoc AUROC intervals |
| `SCRIPT_VERSION` (e.g. `m3-0.4`) | version label inside each script, recorded in each run's `provenance.json`; [`../case_study/experiments/SCRIPT_VERSIONS.md`](../case_study/experiments/SCRIPT_VERSIONS.md) maps runs to shipped files |
| `export-v13.1`, `export-1.1` | version labels of the per-detection table cache: `export-v13.1` on the recorded cache from which the supporting analyses, the figure data and the post-hoc analysis were computed; `export-1.1` on `case_study/tools/export_tables.py`, the repository version of the same builder. Each tool checks its split-0 values against `case_study/results/` before it writes anything |
| v24, v25 | labels of internal analysis rounds that appear in some script headers and logs (for example `v25f5-0.2`); they carry no meaning beyond the date order |
| `RUM`, `/data/inputs` | folder of the detector outputs and dataset files that the scripts read (option `--rum`, environment variable `RUM`) |

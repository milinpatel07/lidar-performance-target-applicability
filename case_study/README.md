# Case study: PointPillars ensembles on KITTI and nuScenes

This folder holds the case study of the paper

> Milin Patel and Rolf Jung. *Uncertainty Evaluation to Support Safety of the Intended Functionality Analysis for
> Determining the Applicability of Performance Targets Across Triggering Conditions in ML-Based LiDAR Object
> Detection.* Submitted, 2026.

with its experiment scripts, recorded results, checks, configurations and documentation. The test itself and how to
use it on other detectors are described outside this folder: [`../README.md`](../README.md),
[`../docs/concept.md`](../docs/concept.md) and [`../package/`](../package/README.md). Paths on this page and in the files
of this folder are relative to `case_study/`.

## What was studied

Two ensembles of four PointPillars detectors, one trained on KITTI and one on nuScenes, and three changes of condition,
each in both directions:

- near and far distance (KITTI and nuScenes);
- clear weather and rain (nuScenes, daylight);
- KITTI with its detector and nuScenes with its detector (a control: a change of both data and detector).

Far distance and rain are treated as potential triggering conditions. Two uncertainty indicators are compared: the
spatial indicator u_s (one minus the mean overlap of the member boxes of a detection) and the existence indicator u_e
(one minus the mean confidence of the members). The limits 10⁻², 10⁻³ and 10⁻⁴
define the performance targets (**target limits**); 0.05† and 0.1† (**exploratory limits**, marked †) show at which
limit the test reaches the outcome applicable or not applicable and define no performance target. All five limits,
δ = 0.05 and the conditions were recorded with a date before any outcome was computed
([`docs/study_protocol/`](docs/study_protocol/README.md)). KITTI results apply the KITTI rule: detections in regions
without annotation or on vans are left out.

The frames of each condition are divided into a grid part (candidate thresholds), a selection part and a test part, in
two ways ([`docs/method.md`](docs/method.md)):

- **division by frame**: frames are assigned to the parts at random, on five splits (random seeds). Counting frames as
  independent units gives the **frame-level evaluation**.
- **division by recorded sequence**: whole nuScenes scenes or KITTI drives are assigned to the parts, because frames of
  one sequence are not independent. Counting sequences gives the **sequence-level evaluation**; counting frames on this
  division gives the **third run**.

## Findings

1. **Counted in recorded sequences, almost no outcome was applicable or not applicable.** In the sequence-level
   evaluation, 5 of the 240 transfer outcomes were applicable or not applicable, all on nuScenes and applicable at
   0.1†, and no transfer was not applicable. A KITTI selection part holds 20 drives (22 for the change of dataset and
   detector) and a nuScenes rain part 9 to 12 scenes, while selecting a threshold at 10⁻² needs at least 299
   independent units ([nuScenes scenes](results/division_by_sequence/nuscenes_by_scene/m7_scene_split_summary.txt),
   [KITTI drives](results/division_by_sequence/kitti_by_drive/summary.txt)).
2. **Counted in frames, some transfers were not applicable.** In the frame-level evaluation, the threshold for the
   spatial indicator selected with the nuScenes detector on nuScenes was not applicable with the KITTI detector on KITTI
   on all five splits at 10⁻², 0.05† and 0.1†. After transfers into far distance and into rain, the outcome was not
   applicable on at least four of five splits at 0.1† for at least one indicator
   ([outcome table](docs/results.md#outcomes-over-the-five-splits)). The paper reports these with the caveat that the
   stated error probability is not guaranteed with dependent frames.
3. **A transferred threshold that met 10⁻² rejected most correct detections.** A limit on accepted wrong detections can
   be met by accepting almost nothing, so every applicable outcome is reported with its retention, the share of correct
   detections accepted: at most 29 % (28.5 %) for a transferred threshold at 10⁻²
   ([retention](results/supporting_analyses/retention_applicable_cells.csv)).
4. **Unchanged separation did not mean an unchanged FAP (rain).** In rain the AUROC of the existence indicator did not
   decrease (0.844 clear, 0.856 rain, test part of split 0), yet the threshold transferred from clear weather at 0.1†
   was not applicable in rain on four of five splits. Rain holds more wrong detections, and they are spread differently
   over frames ([shares](results/supporting_analyses/wrong_share_and_median_split0.csv)). A post-hoc sequence
   bootstrap, not part of the paper, gives the AUROC difference rain minus clear, 0.012, the 95 % interval [−0.030, 0.051]
   ([`results/post_hoc/`](results/post_hoc/README.md)).
5. **The number of independent units needed can be computed before recording.** Showing a limit met at error
   probability δ′ needs at least n ≥ ln δ′ / ln(1 − α) units without a false acceptance: 299 for selecting (δ′ = δ) and
   368 for testing (δ′ = δ/2) at 10⁻², 2,995 for selecting at 10⁻³
   ([`../docs/concept.md`](../docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence)).

## Where each result is

Each folder of [`results/`](results/README.md) holds the files one run wrote, with a `provenance.json` (script version
and SHA-256, SHA-256 of every input, configuration). The run ID in the last column is the label that the scripts, file
headers and `provenance.json` files use; [`../docs/glossary.md`](../docs/glossary.md#names-of-runs-and-versions)
explains it.

| question | folder | run ID |
|---|---|---|
| Does a KITTI threshold selected at near distance hold at far distance, and the reverse? Pilot with the blended score (a weighted sum of box and confidence spread from the detection pipeline) | [`results/division_by_frame/kitti_distance_pilot/`](results/division_by_frame/kitti_distance_pilot/) | m1 |
| The same with the indicators u_s and u_e | [`results/division_by_frame/kitti_distance/`](results/division_by_frame/kitti_distance/) | m2 |
| Does a nuScenes threshold selected at near distance hold at far distance, and the reverse? (five splits; Fig. 4) | [`results/division_by_frame/nuscenes_distance/`](results/division_by_frame/nuscenes_distance/) | m3 |
| Does a threshold selected on one dataset with its detector hold on the other? (one split) | [`results/division_by_frame/dataset_change_one_split/`](results/division_by_frame/dataset_change_one_split/) | m4 |
| On five splits (Fig. 4): KITTI distance with and without the KITTI rule (files `A_*`), change of dataset and detector (`B_*`), nuScenes clear weather and rain (`C_*`) | [`results/division_by_frame/kitti_rule_dataset_change_weather/`](results/division_by_frame/kitti_rule_dataset_change_weather/) | m6 |
| Do the outcomes hold when whole nuScenes scenes are assigned to the parts? (third run and sequence-level evaluation) | [`results/division_by_sequence/nuscenes_by_scene/`](results/division_by_sequence/nuscenes_by_scene/) | m7 |
| The same for KITTI drives, for KITTI distance and the change of dataset and detector | [`results/division_by_sequence/kitti_by_drive/`](results/division_by_sequence/kitti_by_drive/) | m8 |
| How much do the thresholds retain, which changes in the detections accompany a not applicable outcome, and the data of the figures | [`results/supporting_analyses/`](results/supporting_analyses/) | - |
| Analyses added after the outcomes were known, not in the paper (sequence test of the per-frame FAP, betting interval, AUROC intervals, epoch check) | [`results/post_hoc/`](results/post_hoc/README.md) | - |
| Outcome counts of the first runs, superseded by the tables of `docs/results.md` | [`results/earlier_summaries/`](results/earlier_summaries/) | - |

The run ID m5 is the frame figure script and has no result folder. [`docs/results.md`](docs/results.md) explains every
column; [`docs/supplementary/supplementary.pdf`](docs/supplementary/supplementary.pdf) holds every result table in one
document.

## Check and reproduce

Three levels, from the cheapest ([`docs/reproduce.md`](docs/reproduce.md) has every command):

1. **Checks, no data** (Python 3.10, from this folder):

   ```bash
   pip install -r environment/requirements.txt
   python checks/check_paper_numbers.py --check-fresh       # every number of the paper against the recorded files
   python checks/check_recorded_results.py                  # every recorded result file at its path
   python tools/supplementary/make_supplementary.py --check # every number of the supplementary material
   ```

   [`docs/paper_map.md`](docs/paper_map.md) lists each number of the paper with its file, filter and script.
2. **Figures from the recorded results, no data**: [`tools/figures/paper/README.md`](tools/figures/paper/README.md).
3. **Experiment runs**: need the datasets and the detector outputs ([`docs/data.md`](docs/data.md),
   [`docs/provenance.md`](docs/provenance.md)); a rerun reproduces a recorded run if its result files and input hashes
   equal the recorded ones.

## Folders

```
experiments/   experiment scripts; they load each other by file name, so run them from case_study/experiments/
                 recorded_versions/   earlier versions that produced the first runs
                 SCRIPT_VERSIONS.md   which script file produced which recorded run
results/       recorded results (see above); INPUT_HASHES.md lists the input files of every run
checks/        checks of the recorded results and of every number of the paper
tools/         export of the per-detection tables, supporting analyses, figures, supplementary material,
               data of the browser pages
docs/          method as implemented, data, provenance, reproduction, pipeline, paper map, results index,
               study protocol, supplementary material
configs/       configuration of each run; detectors/ holds the detector configurations (OpenPCDet)
notebooks/     notebook that rebuilds the outcome tables from results/
environment/   Dockerfile and pinned requirements of the recorded runs
```

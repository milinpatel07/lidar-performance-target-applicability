# Applicability of performance targets across triggering conditions in LiDAR object detection

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23495356.svg)](https://doi.org/10.5281/zenodo.23495356)
[![checks](https://github.com/milinpatel07/lidar-performance-target-applicability/actions/workflows/checks.yml/badge.svg)](https://github.com/milinpatel07/lidar-performance-target-applicability/actions/workflows/checks.yml)
[![site](https://img.shields.io/badge/interactive-pages-1f6feb)](https://milinpatel07.github.io/lidar-performance-target-applicability/)

This repository addresses one question of a SOTIF analysis (ISO 21448): does a performance target that an object
detector meets with an uncertainty threshold under one condition also hold under a triggering condition? It provides a
statistical test for this question (the **applicability test**), browser pages and a Python package to apply it, guides
for safety engineers, perception developers and assessors, and a case study with PointPillars ensembles on KITTI and
nuScenes, with code, recorded results and detector provenance. The case study is that of the paper

> Milin Patel and Rolf Jung. *Uncertainty Evaluation to Support Safety of the Intended Functionality Analysis for
> Determining the Applicability of Performance Targets Across Triggering Conditions in ML-Based LiDAR Object
> Detection.* Submitted, 2026.

The paper itself is not part of this repository. Its numbers are listed with their source files in
[`docs/paper_map.md`](docs/paper_map.md), and a check recomputes them from the files on every push.

## The problem

A machine-learning object detector can meet a performance target derived for SOTIF analysis, here a limit α on the
share of wrong detections among the detections it passes on, by rejecting detections whose uncertainty exceeds a
threshold τ. A threshold selected with a statistical guarantee on data of one condition carries that guarantee only for
data distributed like its selection data. A SOTIF analysis, however, has to establish whether the target is met under
every **triggering condition**, for example at far distance or in rain.

## The idea: the applicability test

The threshold selected in the *condition of selection* is used unchanged in the *condition of use*. An interval of the
false acceptance proportion (FAP) there decides, at a stated error probability, whether the target is **applicable**,
**not applicable** or **not determined**. A lower bound (the zero-failure bound) gives the number of independent
recorded units that an applicable outcome needs.

```mermaid
flowchart LR
  AC["acceptance criterion<br/>(vehicle level)"] --> PT["performance target<br/>A_c(τ) ≤ α<br/>(detector)"]
  PT --> SEL["threshold τ_c selected<br/>with Learn then Test<br/>in the condition of selection c"]
  SEL -->|"transfer, unchanged"| TEST["interval [L, U] of the FAP<br/>in the condition of use c'"]
  TEST --> O1["applicable<br/>U ≤ α"]
  TEST --> O2["not determined<br/>L ≤ α < U"]
  TEST --> O3["not applicable<br/>L > α"]
```

[`docs/concept.md`](docs/concept.md) explains the test in one page: the statistics, the four changes in the detections
that can make a transferred threshold exceed its limit, the independent unit, and the measure that follows from each
outcome in the safety argument.

## Try it in the browser

The pages run in the browser without installation. Start page:
https://milinpatel07.github.io/lidar-performance-target-applicability/

| page | what it does |
|---|---|
| [Walk-through](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/walkthrough.html) | the test in seven steps, each with one figure on schematic data |
| [Applicability test calculator](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/test.html) | from the number of units, the estimated FAP, α and δ: the selection p-value, the interval [L, U], the outcome and the minimum number of units; also recomputes a recorded interval of the sequence-level evaluation |
| [Run the test on your own detections](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/own-data.html) | the test on a CSV file of detections, computed in the browser; the file is not uploaded |
| [Independent units needed](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/units.html) | the zero-failure bound (Eq. 5 of the paper) with the recorded test units of every condition, counted as frames, scenes and drives |
| [Four changes in the detections](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/concept.html) | a schematic (no data) showing why AUROC can stay unchanged while the FAP at a transferred threshold rises |
| [Separation and FAP](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/separation.html) | a threshold moved along the recorded ROC and FAP curves of the condition of selection and of use |
| [Results browser](https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/) | every recorded outcome of the case study by pair of conditions, indicator, limit, split and evaluation, with its source row |

The sources of the pages are in [`site/`](site/) ([`site/interactive/`](site/interactive/README.md),
[`site/explorer/`](site/explorer/README.md)). To serve them locally: `python3 -m http.server -d site 8000`, then open
http://localhost:8000/.

## Use it on your own detector

The test needs a table of detections with frame, condition, indicator value and a correct/wrong label; it needs no
access to the detector itself.

- [`package/`](package/README.md): the test as a Python package (`applicability_test`), with a command line, tested
  against the experiment scripts.
- [`docs/guides/apply-to-your-detector.md`](docs/guides/apply-to-your-detector.md): from a table of detections to an
  outcome.
- [`docs/guides/plan-recording.md`](docs/guides/plan-recording.md): how many independent units each condition needs
  before a recording campaign.
- [`docs/guides/outcomes-in-a-safety-argument.md`](docs/guides/outcomes-in-a-safety-argument.md): what an outcome
  supports in a SOTIF analysis and what it does not.

## Case study: PointPillars ensembles on KITTI and nuScenes

The study examines three changes of condition in both directions on two datasets: near and far distance (KITTI and
nuScenes), clear weather and rain (nuScenes), and, as a control, KITTI with its detector against nuScenes with its
detector. Far distance and rain are treated as potential triggering conditions. The limits 10⁻², 10⁻³ and 10⁻⁴ define the
performance targets (**target limits**); 0.05† and 0.1† (**exploratory limits**) show at which limits the test reaches
the outcome applicable or not applicable and define no performance target. All five limits, δ = 0.05 and the conditions
were recorded with a date before any outcome was computed. KITTI results apply the KITTI rule (detections in unannotated
regions or on vans are left out).

1. **Counted in recorded sequences, almost no outcome was applicable or not applicable.** Frames of one recorded sequence (a nuScenes scene
   or a KITTI drive) are not independent. In the **sequence-level evaluation**, with the sequence as the independent unit,
   5 of the 240 transfer outcomes were applicable or not applicable, all on nuScenes and applicable at 0.1†, and no
   transfer was not applicable. A KITTI selection part holds 20 drives (22 for the change of dataset and detector) and a
   nuScenes rain part 9 to 12 scenes, while selecting a threshold at 10⁻² needs at least 299 independent units
   ([m7](results/m7_nuscenes_by_scene/m7_scene_split_summary.txt), [m8](results/m8_kitti_by_drive/summary.txt)).
2. **Counted in frames, some transfers were not applicable.** In the **frame-level evaluation**, the threshold for the
   spatial indicator selected with the nuScenes detector on nuScenes was not applicable with the KITTI detector on KITTI
   on all five splits at 10⁻², 0.05† and 0.1†. After transfers into far distance and into rain, the outcome was not
   applicable on at least four of five splits at 0.1† for at least one indicator
   ([outcome table](docs/results.md#outcomes-over-the-five-splits)). The paper reports these with the caveat that the
   stated error probability is not guaranteed with dependent frames.
3. **A transferred threshold that met 10⁻² rejected most correct detections.** A limit on accepted wrong detections can be
   met by accepting almost nothing (Eq. 3 of the paper), so every applicable outcome is reported with its **retention**,
   the share of correct detections accepted: at most 29 % (28.5 %) for a transferred threshold at 10⁻²
   ([retention](results/supporting_analyses/retention_applicable_cells.csv)).
4. **Unchanged separation did not mean an unchanged FAP (rain).** In rain the AUROC of the existence indicator did not
   decrease (0.844 clear, 0.856 rain, test part of split 0), yet the threshold transferred from clear weather at 0.1† was
   not applicable in rain on four of five splits. Rain holds more wrong detections, and they are spread differently over
   frames ([shares](results/supporting_analyses/wrong_share_and_median_split0.csv)). A post-hoc sequence bootstrap, not
   part of the paper, gives the difference 0.012 the 95 % interval [−0.030, 0.051] ([`results/post_hoc/`](results/post_hoc/)).
5. **The number of independent units needed can be computed before recording.** Showing a limit met at error probability
   δ′ needs at least n ≥ ln δ′ / ln(1 − α) units without a false acceptance: 299 for selecting (δ′ = δ) and 368 for
   testing (δ′ = δ/2) at 10⁻², 2,995 for selecting at 10⁻³ ([`docs/concept.md`](docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence)).

| run | what it computes | results |
|---|---|---|
| m1 | KITTI distance with the blended score of the detection pipeline (precursor of m2) | [`results/m1_kitti_distance_pilot`](results/m1_kitti_distance_pilot/) |
| m2 | KITTI distance with the spatial indicator u_s and the existence indicator u_e | [`results/m2_kitti_distance`](results/m2_kitti_distance/) |
| m3 | nuScenes distance with u_s and u_e | [`results/m3_nuscenes_distance`](results/m3_nuscenes_distance/) |
| m4 | change of dataset and detector, one split | [`results/m4_dataset_change`](results/m4_dataset_change/) |
| m5 | frame figure only; no result folder | (none) |
| m6 | KITTI distance with and without the KITTI rule; change of dataset and detector on five splits; nuScenes weather | [`results/m6_five_splits`](results/m6_five_splits/) |
| m7 | nuScenes distance and weather divided by recorded scene: third run and sequence-level evaluation | [`results/m7_nuscenes_by_scene`](results/m7_nuscenes_by_scene/) |
| m8 | KITTI distance and change of dataset and detector divided by recorded KITTI drive | [`results/m8_kitti_by_drive`](results/m8_kitti_by_drive/) |
| supporting | retention, changes in the detections, intervals, common threshold, recall, annotation checks, figure data | [`results/supporting_analyses`](results/supporting_analyses/) |
| post hoc | not in the paper: a sequence test of the per-frame FAP (Method A), a betting interval (Method B), sequence-bootstrap AUROC intervals, the epoch check | [`results/post_hoc`](results/post_hoc/) |

What each result file holds: [`docs/results.md`](docs/results.md). All result tables in one document:
[`docs/supplementary/supplementary.pdf`](docs/supplementary/supplementary.pdf).

## Reproduce

The checks need only this repository; the full list with what each one compares is in
[`docs/reproduce.md`](docs/reproduce.md#0-checks-without-data). For example:

```bash
pip install -r environment/requirements.txt
python3 tests/check_paper_numbers.py --check-fresh    # numbers of the paper against the files; docs/paper_map.md fresh
python3 tests/check_recorded_results.py               # every recorded file of version 1.0.0 unchanged at its path
```

GitHub Actions runs all checks on every push ([`.github/workflows/checks.yml`](.github/workflows/checks.yml)) and
publishes `site/` to GitHub Pages from the main branch ([`.github/workflows/pages.yml`](.github/workflows/pages.yml)).
Rerunning the experiments needs the datasets and the detector outputs ([`docs/reproduce.md`](docs/reproduce.md));
[`docs/pipeline.md`](docs/pipeline.md) shows which script reads and writes which file.

```mermaid
flowchart LR
  D[("KITTI and nuScenes data,<br/>detector outputs<br/>(not included)")] --> A["experiments/<br/>experiment runs m1 to m8"]
  A --> R["results/&lt;run&gt;/<br/>CSV, summary, provenance.json"]
  D --> X["tools/export_tables.py<br/>per-detection cache (work/)"]
  X --> T["tools/supporting, tools/figures,<br/>results/post_hoc/code"]
  R --> T
  T --> S["results/supporting_analyses<br/>results/post_hoc"]
  R --> V["docs/, site/explorer/, site/interactive/,<br/>notebooks/"]
  S --> V
```

```
docs/              documentation; docs/README.md lists every page in reading order
  guides/            applying the test to another detector, planning a recording, outcomes in a safety argument
  supplementary/     supplementary material (PDF and its sources table)
  study_protocol/    predictions fixed before any outcome was computed, outcomes and deviations
site/              everything GitHub Pages serves
  index.html         start page of the pages
  interactive/       browser pages: walk-through, test calculator, own data, units, separation, schematic
  explorer/          results browser
experiments/       experiment scripts m1 to m8 and the statistics they share (they load each other by file name)
  recorded_versions/ earlier script versions that produced the first runs (hash-checked)
  SCRIPT_VERSIONS.md which script file produced which recorded run
results/           recorded results, one folder per run, each with provenance.json (script version, input SHA-256);
                   results/README.md lists the folders and their names before version 2.0
  supporting_analyses/ tables computed by tools/ from the per-detection cache
  post_hoc/          analyses added after the paper's analyses, with the scripts that produced them
tools/             export of the per-detection cache, supporting analyses, figure scripts, supplementary material,
                   builders of the data of the pages
tests/             checks of the numbers of the paper and of the recorded results, tests of the page scripts
package/           the applicability test as a Python package (applicability_test), with tests
configs/           configuration of each run; detectors/ holds the detector configurations (OpenPCDet)
notebooks/         notebook that rebuilds the outcome tables from results/
environment/       Dockerfile and pinned requirements of the recorded runs
MANIFEST.sha256    SHA-256 of every file
```

## Where to find what

| I want to | go to |
|---|---|
| see every documentation page in reading order | [`docs/README.md`](docs/README.md) |
| look up a term or a column name | [`docs/glossary.md`](docs/glossary.md) |
| follow the method step by step, as implemented | [`docs/method.md`](docs/method.md) |
| find the file behind a number, table or figure of the paper | [`docs/paper_map.md`](docs/paper_map.md), [`docs/results.md`](docs/results.md#paper-section-to-repository-index) |
| know which data, detectors, checkpoints and software were used | [`docs/data.md`](docs/data.md), [`docs/provenance.md`](docs/provenance.md) |
| check the predictions fixed before any outcome was computed | [`docs/study_protocol/`](docs/study_protocol/README.md) |
| work with the results in Python | [`notebooks/explore_results.ipynb`](notebooks/explore_results.ipynb) |
| see what changed between versions | [`CHANGELOG.md`](CHANGELOG.md) |

## Data and detectors

No KITTI or nuScenes data is included: no point clouds, images, annotations, detector outputs, per-detection tables or
checkpoints, and no figure that shows dataset images. The scripts read the datasets under their own licences and the
outputs of the detector ensembles ([`docs/data.md`](docs/data.md)). [`results/INPUT_HASHES.md`](results/INPUT_HASHES.md)
gives the SHA-256 of every input file, and [`docs/provenance.md`](docs/provenance.md) the toolbox version, detector
configurations, training runs and the SHA-256 of every checkpoint that inference loaded.

## Versions and citation

The repository is archived on Zenodo; the concept DOI [10.5281/zenodo.23495356](https://doi.org/10.5281/zenodo.23495356)
resolves to the latest archived version. The recorded results of version 1.0.0 are unchanged, byte for byte, in every
later version. Since the layout of version 2.0, some run folders carry new names, and
[`tests/check_recorded_results.py`](tests/check_recorded_results.py) checks every file at its current path.
[`CHANGELOG.md`](CHANGELOG.md) lists what each version added. Citation metadata: [`CITATION.cff`](CITATION.cff).

## Licence

Code (`experiments/`, `tools/`, `tests/`, `package/`, `environment/`, the pages and scripts in `site/`, notebook code,
`results/post_hoc/code/`, `.github/`): MIT, see [`LICENSE`](LICENSE). Results, data files of the pages, configurations
and documentation: CC BY-NC-SA 4.0, see [`LICENSE-results`](LICENSE-results), as required by the dataset licences.
Detector configurations in `configs/detectors/`: Apache License 2.0 (OpenPCDet).

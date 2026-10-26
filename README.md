# Applicability of performance targets across triggering conditions

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23495356.svg)](https://doi.org/10.5281/zenodo.23495356)
[![checks](https://github.com/milinpatel07/lidar-performance-target-applicability/actions/workflows/checks.yml/badge.svg)](https://github.com/milinpatel07/lidar-performance-target-applicability/actions/workflows/checks.yml)
[![site](https://img.shields.io/badge/interactive-pages-1f6feb)](https://milinpatel07.github.io/lidar-performance-target-applicability/)

An object detector can meet a performance target, for example "at most 1 % of the detections it passes on are wrong",
by rejecting detections whose uncertainty lies above an **uncertainty threshold**. A threshold chosen on data of one
condition (near distance, clear weather) carries its statistical guarantee only for data like those. A safety analysis
according to ISO 21448 (safety of the intended functionality, SOTIF) has to know whether the target also holds under
each **triggering condition**; for a LiDAR detector, far distance and rain are examples of potential triggering
conditions.

This repository provides a statistical test for that question, the **applicability test**: it takes the threshold
selected in one condition, applies it unchanged in another, and decides at a stated error probability whether the
target is met there. It is meant for safety engineers who build the argument, perception developers who choose the
threshold, and assessors who review the evidence. It contains

- [`package/`](package/README.md): the test as a Python package (`applicability_test`) for the detections of any
  detector;
- [`site/`](https://milinpatel07.github.io/lidar-performance-target-applicability/): browser pages that run the test
  without installation;
- [`docs/`](docs/README.md): the idea of the test, questions and answers, a glossary and guides;
- [`case_study/`](case_study/README.md): the case study of the paper below (PointPillars ensembles on KITTI and
  nuScenes), with its code, recorded results, checks and detector provenance.

> Milin Patel and Rolf Jung. *Uncertainty Evaluation to Support Safety of the Intended Functionality Analysis for
> Determining the Applicability of Performance Targets Across Triggering Conditions in ML-Based LiDAR Object
> Detection.* Submitted, 2026.

How to cite the paper and this repository: [Citation](#citation).

## What a result means

The performance target is a limit α on the **false acceptance proportion (FAP)**: the share of wrong detections among
the detections that the threshold accepts, averaged over frames. A threshold τ is selected in the **condition of
selection** c and tested, unchanged, in the **condition of use** c′. The test gives an interval [L, U] for the FAP in
c′ at confidence level 1 − δ and one of four outcomes:

| outcome | rule | meaning for the target in c′ | measure that follows |
|---|---|---|---|
| **applicable** | U ≤ α | evidence that the target is met in c′ with the transferred threshold | use the threshold in c′ if the share of annotated objects that still reach the motion planner meets a second target on missed objects |
| **not applicable** | L > α | evidence that the target is not met in c′ with the transferred threshold | select a threshold in c′ (needs a run-time signal for c′) or a common threshold for several conditions, or restrict the operational design domain or add a measure in tracking, fusion or motion planning |
| **not determined** | L ≤ α < U | no statement: the data of c′ do not suffice or the FAP lies close to α | record further independent units and treat c′ as not verified |
| **no threshold selected** | the lowest (strictest) candidate threshold fails in c | the data of c do not show the limit for any candidate threshold | record further independent units in c or request a new allocation of α |

An applicable or not applicable outcome is wrong with probability at most δ/2, but only if the units of the data
(frames, or recorded sequences when frames of one sequence depend on each other) are independent. The table follows
Table 5 of the paper. Every applicable outcome is reported with its
**retention**, the share of correct detections that the threshold accepts, because a threshold that accepts almost
nothing meets any limit. The number of independent units needed to show a limit can be computed before recording:
n ≥ ln δ′ / ln(1 − α) units without a false acceptance, with δ′ = δ for selecting and δ′ = δ/2 for testing a threshold;
for example 368 units to test α = 10⁻² at δ = 0.05.
[`docs/concept.md`](docs/concept.md) explains the test in one page.

## Quick start

Python 3.9 or later; the package needs only NumPy.

```bash
git clone https://github.com/milinpatel07/lidar-performance-target-applicability
cd lidar-performance-target-applicability
pip install ./package
python package/examples/synthetic_example.py
```

The example generates detections of two conditions (no dataset involved) and prints one outcome per limit and
condition of use, for example `0.01   rain   0.3700   0.1072   [0.0933, 0.1220]   0.999   not applicable`. The same
test from the command line, on a CSV file with one row per detection (columns `frame`, `condition`, `part`, `u`,
`correct`; a synthetic sample is in `package/examples/`):

```bash
python -m applicability_test package/examples/detections_example.csv --selection-condition clear --use-condition rain --alpha 0.05
```

It prints the selected threshold, the interval [L, U], the retention and `outcome: not applicable`. Replace the file
by a table of your own detections.

The input format, the Python API and the assumptions are in [`package/README.md`](package/README.md); the steps from a
detector to an outcome are in [`docs/guides/apply-to-your-detector.md`](docs/guides/apply-to-your-detector.md).

## Try it in the browser

The pages run in the browser without installation ([start page](https://milinpatel07.github.io/lidar-performance-target-applicability/)):

| page | what it does |
|---|---|
| [Walk-through](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/walkthrough.html) | the test in seven steps, each with one figure on schematic data |
| [Test calculator](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/test.html) | from the number of units, the estimated FAP, α and δ: the interval [L, U], the outcome and the minimum number of units |
| [Your own detections](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/own-data.html) | the test on a CSV file of detections, computed in the browser; the file is not uploaded |
| [Independent units needed](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/units.html) | the lowest limit that n independent units can show, with the units of the case study |
| [Four changes in the detections](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/concept.html) | a schematic of why the separation (AUROC) can stay the same while the FAP at a transferred threshold rises |
| [Separation and FAP](https://milinpatel07.github.io/lidar-performance-target-applicability/interactive/separation.html) | a threshold moved along the recorded ROC and FAP curves of the case study |
| [Results browser](https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/) | every recorded outcome of the case study, with its source row |

## Guides

- [`docs/guides/apply-to-your-detector.md`](docs/guides/apply-to-your-detector.md): from a table of detections to an
  outcome.
- [`docs/guides/plan-recording.md`](docs/guides/plan-recording.md): how many independent units each condition needs
  before a recording campaign.
- [`docs/guides/outcomes-in-a-safety-argument.md`](docs/guides/outcomes-in-a-safety-argument.md): what an outcome
  supports in a SOTIF analysis and what it does not.
- [`docs/faq.md`](docs/faq.md): short answers to the questions a first reader asks most.
- [`docs/concept.md`, section 7](docs/concept.md#7-limitations-of-the-study): the limitations of the case study.

## The case study of the paper

PointPillars ensembles on KITTI and nuScenes, three changes of condition in both directions: near and far distance,
clear weather and rain, and KITTI with its detector against nuScenes with its detector. In short: counted in recorded
sequences (the independent unit when frames of one sequence depend on each other), neither dataset held enough
sequences to show any target limit, and no transfer was not applicable; counted in frames, transfers into far distance,
into rain and between the two detectors gave not applicable outcomes, and thresholds that met 10⁻² after a transfer
rejected most correct detections. [`case_study/README.md`](case_study/README.md) gives the findings with their files, the
folders, and how to check every number of the paper.

To check the numbers of the paper against the recorded results (no dataset needed, Python 3.10):

```bash
cd case_study
pip install -r environment/requirements.txt
python checks/check_paper_numbers.py --check-fresh    # every number of the paper against the recorded files
python checks/check_recorded_results.py               # every recorded result file at its path
```

## Repository layout

```
package/          the applicability test as a Python package, with examples and tests
docs/             the idea of the test, questions and answers, glossary, guides
site/             browser pages (published on GitHub Pages): walk-through, calculator, own data, results browser
tests/            tests of the browser pages against the Python code, and the link check
case_study/       the case study of the paper (its own README)
  experiments/      experiment scripts of the runs
  results/          recorded results, grouped by how the frames were divided into parts:
    division_by_frame/      frames assigned to parts at random
    division_by_sequence/   whole recorded sequences (nuScenes scenes, KITTI drives) assigned to parts
    supporting_analyses/    retention, changes in the detections, figure data
    post_hoc/               analyses added after the outcomes were known, not in the paper
  checks/           checks of the recorded results and of every number of the paper
  tools/            exports, supporting analyses, figures, supplementary material, data of the pages
  docs/             method as implemented, data, provenance, reproduction, paper map, study protocol, supplementary
  configs/  notebooks/  environment/
CHANGELOG.md  CITATION.cff  LICENSE  LICENSE-results  MANIFEST.sha256
```

Versions up to 1.2.0 used other paths; [`CHANGELOG.md`](CHANGELOG.md#layout) maps each old path to the current one.
GitHub Actions runs every check on each push ([`.github/workflows/checks.yml`](.github/workflows/checks.yml)).

## Data

No KITTI or nuScenes data is included: no point clouds, images, annotations, detector outputs, per-detection tables or
checkpoints. The case study reads the datasets under their own licences
([`case_study/docs/data.md`](case_study/docs/data.md)); [`case_study/results/INPUT_HASHES.md`](case_study/results/INPUT_HASHES.md)
gives the SHA-256 of every input file.

## Citation

Paper (submitted, 2026; no DOI yet):

```
M. Patel and R. Jung. Uncertainty Evaluation to Support Safety of the Intended Functionality Analysis for Determining
the Applicability of Performance Targets Across Triggering Conditions in ML-Based LiDAR Object Detection. Submitted, 2026.
```

Code and results: the concept DOI [10.5281/zenodo.23495356](https://doi.org/10.5281/zenodo.23495356) resolves to the
latest archived version; [`CITATION.cff`](CITATION.cff) holds the metadata (GitHub shows it under "Cite this
repository"). [`CHANGELOG.md`](CHANGELOG.md) lists what each version changed. No number, outcome or input hash of the
recorded results of version 1.0.0 has changed in any later version.

## Licence

Code (`package/`, `site/`, `tests/`, `.github/`, and in `case_study/` the folders `experiments/`, `tools/`, `checks/`,
`environment/`, `results/post_hoc/code/` and the notebook code): MIT, see [`LICENSE`](LICENSE). Results, data files of
the pages, configurations and documentation: CC BY-NC-SA 4.0, see [`LICENSE-results`](LICENSE-results), as required by
the dataset licences. Detector configurations in `case_study/configs/detectors/`: Apache License 2.0 (OpenPCDet).

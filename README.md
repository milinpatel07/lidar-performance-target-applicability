# Applicability of performance targets across triggering conditions in LiDAR object detection

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23495356.svg)](https://doi.org/10.5281/zenodo.23495356)
[![checks](https://github.com/milinpatel07/lidar-performance-target-applicability/actions/workflows/checks.yml/badge.svg)](https://github.com/milinpatel07/lidar-performance-target-applicability/actions/workflows/checks.yml)

Code, recorded results and supplementary material of the paper

> Milin Patel and Rolf Jung. *Uncertainty Evaluation to Support Safety of the Intended Functionality Analysis for
> Determining the Applicability of Performance Targets Across Triggering Conditions in ML-Based LiDAR Object
> Detection.* Submitted, 2026.

The paper is not part of this repository. Every number it states is listed with its source file in
[`docs/paper_map.md`](docs/paper_map.md), and a check recomputes each of them from the files on every push.

## Where to start

| I want to | go to |
|---|---|
| understand the question and the answer | the two sections below |
| look up a term or a column name | [`docs/glossary.md`](docs/glossary.md) |
| see how the test works, step by step | [`docs/method.md`](docs/method.md) |
| browse every outcome by pair, indicator, limit and split | [results browser](https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/) ([`explorer/`](explorer/)) or the notebook [`notebooks/explore_results.ipynb`](notebooks/explore_results.ipynb) |
| find the file behind a number or figure of the paper | [`docs/paper_map.md`](docs/paper_map.md) |
| read all tables in one document | [`docs/supplementary/supplementary.pdf`](docs/supplementary/supplementary.pdf) |
| know what each result file holds | [`docs/results.md`](docs/results.md) |
| rerun an experiment or a figure | [`docs/reproduce.md`](docs/reproduce.md), [`docs/pipeline.md`](docs/pipeline.md) |
| know what data and detectors were used | [`docs/data.md`](docs/data.md) |
| check the predictions fixed before the first run | [`docs/study_protocol/`](docs/study_protocol/) |
| see what changed between versions | [`CHANGELOG.md`](CHANGELOG.md) |

## The question

ISO 21448 (safety of the intended functionality, SOTIF) asks that the residual risk of an automated driving function be
shown acceptable against an acceptance criterion at vehicle level. For a perception element, a **performance target**
is derived from it: here, a limit α on the **false acceptance proportion (FAP)**, the mean over frames of the share of
wrong detections among the detections that the threshold accepts.

A LiDAR object detector built as an ensemble of four networks gives each detection an uncertainty value. A **threshold**
τ on this value rejects uncertain detections. Selected with the Learn then Test procedure on data of one condition (for
example near distance or clear weather), τ meets the limit there with a stated error probability. A SOTIF analysis covers
every **triggering condition** (here far distance and rain are treated as potential triggering conditions). The
repository answers, for each pair of conditions: **does the target still hold when the same threshold is used in
another condition?**

The threshold selected in the **condition of selection** is tested on held-out data of the **condition of use**. The
Hoeffding–Bentkus bounds [L, U] of the FAP there decide one of three outcomes, each wrong with probability at most δ/2
(δ = 0.05):

| outcome | rule | meaning |
|---|---|---|
| applicable | U ≤ α | the target is met in the condition of use |
| not applicable | L > α | the target is exceeded in the condition of use |
| not determined | L ≤ α < U | the data do not decide |

A fourth result, **no threshold selected**, means that no candidate threshold met the limit in the condition of
selection.

## What the recorded results show

Limits 10⁻², 10⁻³ and 10⁻⁴ (target limits) were fixed before the first run. The limits 0.05† and 0.1† were fixed at the
same time to show which outcomes the data can decide; they are marked † and are **not safety targets**. KITTI results
apply the KITTI rule (wrong detections in unannotated regions or on vans are not counted).

1. **Counted in recorded sequences, few outcomes were decided.** Frames of one recorded sequence (a nuScenes scene or a
   KITTI drive) are not independent. With the sequence as the independent unit, 5 of the 120 nuScenes transfer outcomes
   were decided, all applicable at 0.1†, and no transfer had a not applicable outcome; for KITTI distance no threshold was
   selected. A nuScenes selection part holds 67 or 68 scenes per distance condition and 9 to 11 rain scenes, and a KITTI
   selection part 20 drives, fewer than the 299 units needed to select a threshold at 10⁻²; 20 units cannot show a limit
   below 0.139 to be met ([m7](results/m7_scene_split/m7_scene_split_summary.txt),
   [m8](results/m8_kitti_drive_split/summary.txt)). A post-hoc
   test that keeps the per-frame target with the sequence as the unit gives the same picture
   ([`results/post_hoc/`](results/post_hoc/)).
2. **Counted in frames, transfers gave not applicable outcomes.** With the frame as the unit, the threshold for the
   spatial indicator selected with the nuScenes detector on nuScenes was not applicable with the KITTI detector on KITTI
   on all five splits at 10⁻², 0.05† and 0.1†. After transfers into far distance and into rain, outcomes were not
   applicable on at least four of five splits at 0.1† for at least one indicator
   ([outcome table](docs/results.md#outcomes-over-the-five-splits)).
3. **A transferred threshold that met 10⁻² rejected most correct detections.** A limit on false acceptance can be met by
   rejecting almost everything, so every applicable outcome is reported with its **retention**, the share of correct
   detections accepted: at most 28.5 % for a transferred threshold at 10⁻²
   ([retention](results/supporting_analyses/retention_applicable_cells.csv)).
4. **Unchanged separation did not imply applicability (rain).** In rain the area under the ROC curve of the existence indicator did not
   decrease (0.844 clear, 0.856 rain, test part of split 0; difference 0.012, 95 % sequence-bootstrap interval
   [−0.030, 0.051]), yet the threshold transferred from clear weather at 0.1† was not applicable in rain on four of five
   splits; rain holds more wrong detections ([AUROC intervals](results/post_hoc/auroc_bootstrap.csv),
   [shares](results/supporting_analyses/wrong_share_and_median_split0.csv)).
5. **The number of independent units needed can be computed before recording.** Showing a limit met at error probability
   δ′ needs at least n ≥ ln δ′ / ln(1 − α) units without a false acceptance: 299 for selecting and 368 for testing at
   10⁻², 2,995 for selecting at 10⁻³ ([`docs/method.md`](docs/method.md#6-units-and-the-number-required-for-a-decision)).

## How the repository is organised

```mermaid
flowchart LR
  D[("KITTI and nuScenes data,<br/>detector outputs<br/>(not included)")] --> A["analysis/<br/>experiment runs m1 to m8"]
  A --> R["results/&lt;run&gt;/<br/>CSV, summary, provenance.json"]
  D --> X["tools/export_tables.py<br/>per-detection cache (work/)"]
  X --> T["tools/supporting, tools/figures,<br/>results/post_hoc/code"]
  R --> T
  T --> S["results/supporting_analyses<br/>results/post_hoc"]
  R --> V["docs/paper_map.md, docs/supplementary,<br/>explorer/, notebooks/"]
  S --> V
```

```
analysis/          experiment scripts m1 to m8 and the statistics they share (they load each other by file name)
  recorded_versions/   earlier script versions that produced the first runs (hash-checked)
  SCRIPT_VERSIONS.md   which script file produced which recorded run
results/           recorded results, one folder per run, each with provenance.json (script version, input SHA-256)
  supporting_analyses/ tables computed by tools/ from the per-detection cache
  post_hoc/            analyses added after the parameters were fixed, with the scripts that produced them
tools/             export of the per-detection cache, supporting analyses, figures of the paper and of the supplementary,
                   the paper-number check, the supplementary generator, the browser data
docs/              method, glossary, paper map, results guide, data, reproduction, pipeline, supplementary, study protocol
configs/           configuration of each run, as recorded in its provenance
explorer/          static results browser (served by GitHub Pages)
notebooks/         notebook that rebuilds the outcome tables from results/
MANIFEST.sha256    SHA-256 of every file
```

| run | what it computes | results |
|---|---|---|
| m1 | KITTI distance with the blended score of the detection pipeline (precursor of m2) | [`results/m1_range_kitti`](results/m1_range_kitti/) |
| m2 | KITTI distance with the spatial indicator u_s and the existence indicator u_e | [`results/m2_indicators_kitti`](results/m2_indicators_kitti/) |
| m3 | nuScenes distance with u_s and u_e | [`results/m3_range_nuscenes`](results/m3_range_nuscenes/) |
| m4 | change of dataset and detector, one split | [`results/m4_dataset_shift`](results/m4_dataset_shift/) |
| m5 | frame figure only; no result folder | — |
| m6 | KITTI distance with and without the KITTI rule; change of dataset and detector on five splits; nuScenes weather | [`results/m6_protocol_seeds_weather`](results/m6_protocol_seeds_weather/) |
| m7 | nuScenes distance and weather, division by recorded scene | [`results/m7_scene_split`](results/m7_scene_split/) |
| m8 | KITTI distance and change of dataset and detector, division by recorded KITTI drive | [`results/m8_kitti_drive_split`](results/m8_kitti_drive_split/) |
| supporting | retention, causes, intervals, common threshold, recall, annotation checks, figure data | [`results/supporting_analyses`](results/supporting_analyses/) |
| post hoc | sequence-level test of the per-frame FAP (Method A), betting interval (Method B), sequence-bootstrap AUROC intervals, epoch check | [`results/post_hoc`](results/post_hoc/) |

## Checks that run without data

```bash
pip install -r requirements.txt
python3 tools/check_paper_numbers.py                     # every number of the paper against the files
python3 tools/supplementary/make_supplementary.py --check # every number of the supplementary against the files
python3 tools/build_explorer_data.py --check             # the browser data against the files
sha256sum -c MANIFEST.sha256                             # every file against the manifest
cd analysis && python3 m1_range_kitti.py --selftest && python3 m3_range_nuscenes.py --selftest
```

GitHub Actions runs the same checks on every push ([`.github/workflows/checks.yml`](.github/workflows/checks.yml)).
Rerunning the experiments needs the datasets and the detector outputs: [`docs/reproduce.md`](docs/reproduce.md).

## Data

No KITTI or nuScenes data is included: no point clouds, images, annotations, detector outputs or per-detection tables,
and no figure that shows dataset images. The scripts read the datasets under their own licences and the outputs of the
detector ensembles; see [`docs/data.md`](docs/data.md). [`results/INPUT_HASHES.md`](results/INPUT_HASHES.md) gives the
SHA-256 of every input file, so a rerun can show that it used the same inputs.

## Versions and citation

The repository is archived on Zenodo. The concept DOI
[10.5281/zenodo.23495356](https://doi.org/10.5281/zenodo.23495356) always resolves to the latest version. The paper
cites version 1.0.1 ([10.5281/zenodo.23495357](https://doi.org/10.5281/zenodo.23495357)); the recorded results of that
version are unchanged in every later version, and [`CHANGELOG.md`](CHANGELOG.md) lists what each version added. Citation
metadata: [`CITATION.cff`](CITATION.cff).

## Licence

Code (`analysis/`, `tools/`, `explorer/`, `notebooks/`, `results/post_hoc/code/`, `.github/`): MIT, see
[`LICENSE`](LICENSE). Results and documentation (`results/` except `results/post_hoc/code/`, `configs/`, `docs/`): CC
BY-NC-SA 4.0, see [`LICENSE-results`](LICENSE-results), as required by the dataset licences.

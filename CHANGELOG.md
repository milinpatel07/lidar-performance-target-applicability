# Changelog

The recorded results of version 1.0.0 are unchanged in every later version: no number, outcome or input hash in a result
file of `results/` that existed in 1.0.0 has changed. Up to version 1.2.0 each file also kept its path and SHA-256.
Since version 2.0 the results are in `case_study/results/`, grouped by how the frames were divided and named by
content (see the layout table of 2.0), and dataset and container mount paths are normalised, which changes the SHA-256
of the files that name such a path (the `provenance.json` files). `case_study/checks/check_recorded_results.py` checks
every result file of 1.0.0 at its current path against `case_study/checks/recorded_results_v1.0.0.sha256`: the SHA-256
of the manifest of 1.0.0, updated for the normalised files. Not checked: `case_study/results/README.md`, a description
that was extended, and `case_study/results/INPUT_HASHES.md`, a list that the build writes from the `provenance.json`
files and whose headings name the run folders. Later versions add files and documentation.

## 2.0 (unreleased; not yet archived on Zenodo)

Terms of the submitted paper, detector provenance, interactive pages, a Python package, guides and a new folder layout;
no recorded result changed.

- Dataset mount paths normalised to /data/nuscenes; no change to code logic or results. Container paths are normalised
  in the same way: `/data/inputs` for the input folder (its project name is written `inputs`), `/data/work` for the
  working folder of the runs (including its subfolder for released code and results, and the folder of the experiment
  scripts, written `code/experiments`), `/data/OpenPCDet` for the training container, `/opt/repo` for the repository
  in the Docker example, and `file:///data/build/` for the build folders of two packages in `pip_freeze.txt`. The SHA-256 recorded for the files concerned (script hashes in `provenance.json`, the list of
  version 1.0.0 in `tests/`) are those of the normalised files.

### Layout

The repository is divided into the method (`package/`, `docs/`, `site/`) and the case study of the paper
(`case_study/`), which holds its experiments, recorded results, tools, checks, configurations, notebook, environment and
documentation with the same layout inside as the repository had before. Recorded results are grouped by how the frames
were divided into parts and named by what they hold. Paths up to version 1.2.0 and since version 2.0:

| path since 2.0 | path up to 1.2.0 | content |
|---|---|---|
| `site/index.html`, `site/interactive/`, `site/explorer/` | `index.html`, `interactive/`, `explorer/` | everything GitHub Pages serves; published by `.github/workflows/pages.yml`, the public URLs are unchanged |
| `case_study/experiments/` | `analysis/` | experiment scripts (file names unchanged), `recorded_versions/`, `SCRIPT_VERSIONS.md` |
| `case_study/results/division_by_frame/kitti_distance_pilot/` | `results/m1_range_kitti/` | recorded files (mount paths normalised) |
| `case_study/results/division_by_frame/kitti_distance/` | `results/m2_indicators_kitti/` | recorded files (mount paths normalised) |
| `case_study/results/division_by_frame/nuscenes_distance/` | `results/m3_range_nuscenes/` | recorded files (mount paths normalised) |
| `case_study/results/division_by_frame/dataset_change_one_split/` | `results/m4_dataset_shift/` | recorded files (mount paths normalised) |
| `case_study/results/division_by_frame/kitti_rule_dataset_change_weather/` | `results/m6_protocol_seeds_weather/` | recorded files (mount paths normalised) |
| `case_study/results/division_by_sequence/nuscenes_by_scene/` | `results/m7_scene_split/` | recorded files (mount paths normalised) |
| `case_study/results/division_by_sequence/kitti_by_drive/` | `results/m8_kitti_drive_split/` | recorded files (mount paths normalised) |
| `case_study/results/earlier_summaries/` | `results/outcome_counts.csv`, `results/failing_cells_primary.csv` | outcome counts of the first runs, superseded by the tables of `case_study/docs/results.md` |
| `case_study/results/supporting_analyses/`, `case_study/results/post_hoc/` | `results/supporting_analyses/`, `results/post_hoc/` | unchanged |
| `case_study/checks/` | `tools/check_paper_numbers.py`, `tools/check_export.py` | checks of the recorded results and of the numbers of the paper; new: `check_recorded_results.py` |
| `tests/` | `tools/test_stats_js.py`, `tools/test_own_data_js.py`, `tools/test_explorer.mjs` | tests of the browser pages against the Python code; new: `check_links.py` |
| `case_study/tools/` | `tools/` | exports, supporting analyses, figures, supplementary material, builders of the data of the pages; `build_interactive_data.py` was `interactive/build_data.py` |
| `case_study/configs/`, `case_study/notebooks/` | `configs/`, `notebooks/` | unchanged inside |
| `case_study/environment/` | `Dockerfile`, `requirements.txt`, `requirements-posthoc.txt` | build the image from the repository root with `docker build -f case_study/environment/Dockerfile .` |
| `case_study/docs/` | `docs/` (method, results, paper map, reproduction, data, provenance, pipeline, study protocol, supplementary material) | documentation of the case study |
| `docs/` | `docs/` (concept, glossary, guides) | documentation of the method; `docs/README.md` (new) lists every page in reading order |

Every generator, check, page, notebook path and document refers to the new paths. The data files of the pages and the
supplementary sources table name the new paths of their source files. Files written by the runs keep the folder names of
the time they were written.

### Content

- `docs/concept.md`: one explanation of the idea (target chain, statistics, the four changes in the detections, frame and
  sequence as independent unit, outcome and the measure that follows); `case_study/docs/results.md`: an index from paper sections
  to files.
- `case_study/docs/provenance.md` and `case_study/configs/detectors/`: OpenPCDet version and local changes, the eight member configurations,
  training runs, the checkpoint each member's inference loaded with its SHA-256, and the software environment.
- `site/interactive/`: browser pages for the applicability test (walk-through, calculator that reproduces recorded
  intervals of the sequence-level evaluation, the test on own detections), the independent units, separation and FAP
  along the recorded curves, and a schematic of the four changes in the detections; `tests/test_stats_js.py` and
  `tests/test_own_data_js.py` check the browser statistics against the Python code.
- Terms of the submitted paper throughout (frame-level evaluation, sequence-level evaluation, third run, no threshold
  selected when the lowest candidate fails); equation, table and section numbers of the submitted paper in
  `case_study/docs/paper_map.md`, which a check now also compares with a fresh generation.
- Results browser: paper terms, a notice on frame-unit views, the interval against the limit, links to source rows,
  shareable view state and CSV export.
- Licence scope stated for the data of the pages, the notebook outputs and the detector configurations.
- `package/`: the applicability test as a Python package (`applicability_test`), tested against
  `case_study/experiments/m1_range_kitti.py`; `docs/guides/`: applying the test to another detector, planning a recording, outcomes
  in a safety argument.

## 1.2.0 (2026-10-21)

Navigation, checks and the supplementary material; no recorded result changed.

- `docs/paper_map.md` and `tools/check_paper_numbers.py`: every number of the paper with its source file, filter and
  producing script, recomputed and compared on every push; three notes where the paper text and the files disagree.
- `docs/glossary.md`: one vocabulary, mapped to the column names of the files.
- `docs/supplementary/`: the supplementary material, generated from repository files only by
  `tools/supplementary/make_supplementary.py`, with a sources table of every printed value and a `--check` option.
- `docs/pipeline.md`: which script reads and writes what, with diagrams.
- `docs/study_protocol/outcomes_and_deviations.md`: outcome of each prediction and every deviation from the frozen
  protocol.
- `explorer/`: static results browser (GitHub Pages), with `tools/build_explorer_data.py`.
- `notebooks/explore_results.ipynb`: rebuilds the outcome tables from `results/`, with outputs.
- `tools/figures/paper/`: sources of the figures of the paper; `tools/figures/supplementary/`; `tools/supporting/m8_tables.py`.
- `results/supporting_analyses/`: data of Fig. 5 (`fig_separation_curves.csv`), facts and candidates of the frames of
  Fig. 1, the m8 tables, the counts per distance bin (`distance_bins_log.txt`).
- `.github/workflows/checks.yml`: manifest, paper numbers, supplementary numbers, browser data and self-tests on every push.
- `requirements-posthoc.txt`; the Dockerfile names the environment of the recorded runs; README, method, results and
  reproduction pages use the terms of the paper.

## 1.1.0 (2026-10-21)

- `results/post_hoc/`: analyses added after the parameters were fixed: sequence-level test of the per-frame FAP
  (Method A), betting interval (Method B), sequence-bootstrap AUROC intervals, check of the training epochs, with the
  scripts that produced them.
- `docs/data.md`: the nuScenes members were trained for about 10 epochs (the configured 20 were not completed).

## 1.0.1 (2026-10-20)

- `CITATION.cff` simplified (DOI 10.5281/zenodo.23495357).

## 1.0.0 (2026-10-20)

- Analysis scripts, configurations, recorded results of every run with input hashes, supporting analyses, frozen
  predictions, documentation.

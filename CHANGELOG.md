# Changelog

The recorded results of version 1.0.0 are unchanged in every later version: each result file of `results/` that existed
in 1.0.0 has the same SHA-256 in every later version. Up to version 1.2.0 each file also kept its path. Since the layout
of version 2.0, seven run folders carry names that describe their content; the files in them are byte
for byte the same, and `tests/check_recorded_results.py` checks every result file of 1.0.0 at its current path against
the SHA-256 in the manifest of 1.0.0 (kept as `tests/recorded_results_v1.0.0.sha256`). Not checked: `results/README.md`, a
description that was extended, and `results/INPUT_HASHES.md`, a list that the build writes from the `provenance.json`
files and whose headings name the run folders. Later versions add files and documentation.

## 2.0 (unreleased; not yet archived on Zenodo)

Terms of the submitted paper, detector provenance, interactive pages, a Python package, guides and a new folder layout;
no recorded result changed.

### Layout

| new path | path up to 1.2.0 | content |
|---|---|---|
| `site/index.html`, `site/interactive/`, `site/explorer/` | `index.html`, `interactive/`, `explorer/` | everything GitHub Pages serves; published by `.github/workflows/pages.yml`, the public URLs are unchanged |
| `experiments/` | `analysis/` | experiment scripts m1 to m8, `recorded_versions/`, `SCRIPT_VERSIONS.md` (file names unchanged) |
| `results/m1_kitti_distance_pilot/` | `results/m1_range_kitti/` | recorded files, byte for byte |
| `results/m2_kitti_distance/` | `results/m2_indicators_kitti/` | recorded files, byte for byte |
| `results/m3_nuscenes_distance/` | `results/m3_range_nuscenes/` | recorded files, byte for byte |
| `results/m4_dataset_change/` | `results/m4_dataset_shift/` | recorded files, byte for byte |
| `results/m6_five_splits/` | `results/m6_protocol_seeds_weather/` | recorded files, byte for byte |
| `results/m7_nuscenes_by_scene/` | `results/m7_scene_split/` | recorded files, byte for byte |
| `results/m8_kitti_by_drive/` | `results/m8_kitti_drive_split/` | recorded files, byte for byte |
| `tests/` | `tools/check_paper_numbers.py`, `tools/check_export.py`, `tools/test_stats_js.py`, `tools/test_own_data_js.py`, `tools/test_explorer.mjs` | checks and tests; new: `check_recorded_results.py`, `check_links.py` |
| `tools/build_interactive_data.py` | `interactive/build_data.py` | writes `site/interactive/data/` |
| `environment/` | `Dockerfile`, `requirements.txt`, `requirements-posthoc.txt` | build the image from the repository root with `docker build -f environment/Dockerfile .` |
| `docs/README.md` | (new) | the documentation pages in reading order |

Every generator, check, page, notebook path and document refers to the new paths. The data files of the pages and the
supplementary sources table name the new paths of their source files. Files written by the runs keep the folder names of
the time they were written.

### Content

- `docs/concept.md`: one explanation of the idea (target chain, statistics, the four changes in the detections, frame and
  sequence as independent unit, outcome and the measure that follows); `docs/results.md`: an index from paper sections
  to files.
- `docs/provenance.md` and `configs/detectors/`: OpenPCDet version and local changes, the eight member configurations,
  training runs, the checkpoint each member's inference loaded with its SHA-256, and the software environment.
- `site/interactive/`: browser pages for the applicability test (walk-through, calculator that reproduces recorded
  intervals of the sequence-level evaluation, the test on own detections), the independent units, separation and FAP
  along the recorded curves, and a schematic of the four changes in the detections; `tests/test_stats_js.py` and
  `tests/test_own_data_js.py` check the browser statistics against the Python code.
- Terms of the submitted paper throughout (frame-level evaluation, sequence-level evaluation, third run, no threshold
  selected when the lowest candidate fails); equation, table and section numbers of the submitted paper in
  `docs/paper_map.md`, which a check now also compares with a fresh generation.
- Results browser: paper terms, a notice on frame-unit views, the interval against the limit, links to source rows,
  shareable view state and CSV export.
- Licence scope stated for the data of the pages, the notebook outputs and the detector configurations.
- `package/`: the applicability test as a Python package (`applicability_test`), tested against
  `experiments/m1_range_kitti.py`; `docs/guides/`: applying the test to another detector, planning a recording, outcomes
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

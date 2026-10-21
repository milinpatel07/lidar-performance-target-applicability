# Changelog

The recorded results of version 1.0.0 are unchanged in every later version: each result file of `results/` that existed
in 1.0.0 has the same SHA-256 in every later `MANIFEST.sha256` (only `results/README.md`, a description, was extended).
Later versions add files and documentation.

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

- `CITATION.cff` simplified. This is the version the paper cites (DOI 10.5281/zenodo.23495357).

## 1.0.0 (2026-10-20)

- Analysis scripts, configurations, recorded results of every run with input hashes, supporting analyses, frozen
  predictions, documentation.

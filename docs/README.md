# Documentation

The documentation pages in reading order. Readers who want to understand the test start with the concept; readers who
want to apply it to their own detector go to the guides; readers who want to check or rerun the KITTI and nuScenes case
study go to the case study and reproduction pages. The browser pages (walk-through, calculator, own data, results
browser) are listed on the [start page of the site](https://milinpatel07.github.io/lidar-performance-target-applicability/);
their sources are in [`../site/`](../site/).

## Concept

- [`concept.md`](concept.md): the applicability test in one page, from the acceptance criterion to the measure that
  follows from an outcome.
- [`glossary.md`](glossary.md): every term of the paper with the name it has in the result files and scripts.

## Guides

- [`guides/apply-to-your-detector.md`](guides/apply-to-your-detector.md): from a table of your own detections to an
  outcome, with the Python package or in the browser.
- [`guides/plan-recording.md`](guides/plan-recording.md): how many independent units each condition needs before a
  recording campaign, and what counts as an independent unit.
- [`guides/outcomes-in-a-safety-argument.md`](guides/outcomes-in-a-safety-argument.md): what each outcome supports in a
  SOTIF analysis, what it does not support, and how to report it.

## Case study: KITTI and nuScenes

- [`method.md`](method.md): what the experiment scripts in `experiments/` compute, step by step.
- [`results.md`](results.md): every folder and column of `results/`, the outcome table, and an index from each section,
  table and figure of the paper to the files that hold its values.
- [`data.md`](data.md): datasets, splits, detector outputs and their licences.
- [`provenance.md`](provenance.md): toolbox version, detector configurations, training runs and the checkpoints that
  inference loaded.
- [`paper_map.md`](paper_map.md): every checked number of the paper with its source file and the result of the check
  (written by `tests/check_paper_numbers.py`).
- [`supplementary/`](supplementary/supplementary.pdf): the supplementary material, generated from the repository files
  only, with a sources table of every printed value.
- [`study_protocol/`](study_protocol/README.md): the predictions fixed before any outcome was computed, their outcomes
  and every deviation from the protocol.

## Reproduce

- [`reproduce.md`](reproduce.md): the checks, the tables and figures from the recorded results, and the experiment
  runs, with the commands.
- [`pipeline.md`](pipeline.md): which script reads which file and writes which file.

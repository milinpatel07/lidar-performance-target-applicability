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

- [`../case_study/docs/method.md`](../case_study/docs/method.md): what the experiment scripts in `case_study/experiments/` compute, step by step.
- [`../case_study/docs/results.md`](../case_study/docs/results.md): every folder and column of `case_study/results/`, the outcome table, and an index from each section,
  table and figure of the paper to the files that hold its values.
- [`../case_study/docs/data.md`](../case_study/docs/data.md): datasets, splits, detector outputs and their licences.
- [`../case_study/docs/provenance.md`](../case_study/docs/provenance.md): toolbox version, detector configurations, training runs and the checkpoints that
  inference loaded.
- [`../case_study/docs/paper_map.md`](../case_study/docs/paper_map.md): every checked number of the paper with its source file and the result of the check
  (written by `case_study/checks/check_paper_numbers.py`).
- [`supplementary/`](../case_study/docs/supplementary/supplementary.pdf): the supplementary material, generated from the repository files
  only, with a sources table of every printed value.
- [`study_protocol/`](../case_study/docs/study_protocol/README.md): the predictions fixed before any outcome was computed, their outcomes
  and every deviation from the protocol.

## Reproduce

- [`../case_study/docs/reproduce.md`](../case_study/docs/reproduce.md): the checks, the tables and figures from the recorded results, and the experiment
  runs, with the commands.
- [`../case_study/docs/pipeline.md`](../case_study/docs/pipeline.md): which script reads which file and writes which file.

# Documentation

Pages in reading order. To understand the test, start with the concept; to apply it to your own detector, go to the
guides; to check or rerun the KITTI and nuScenes case study of the paper, go to
[`../case_study/`](../case_study/README.md). The browser pages (walk-through, calculator, own data, results browser)
are on the [start page of the site](https://milinpatel07.github.io/lidar-performance-target-applicability/); their
sources are in [`../site/`](../site/).

## The test

- [`concept.md`](concept.md): the applicability test in one page, from the acceptance criterion to the measure that
  follows from an outcome; section 7 lists the limitations of the case study.
- [`faq.md`](faq.md): short answers to the questions a first reader asks most.
- [`glossary.md`](glossary.md): every term with its meaning and the name it has in the result files and scripts.

## Guides

- [`guides/apply-to-your-detector.md`](guides/apply-to-your-detector.md): from a table of your own detections to an
  outcome, with the Python package or in the browser.
- [`guides/plan-recording.md`](guides/plan-recording.md): how many independent units each condition needs before a
  recording campaign, and what counts as an independent unit.
- [`guides/outcomes-in-a-safety-argument.md`](guides/outcomes-in-a-safety-argument.md): what each outcome supports in a
  SOTIF analysis, what it does not support, and how to report it.
- [`../package/README.md`](../package/README.md): installation, input format, API and assumptions of the Python package.

## Case study of the paper

The documentation of the case study is in [`../case_study/docs/`](../case_study/docs/README.md): the method as
implemented, data and detector provenance, reproduction, the map from every number of the paper to its file, the study
protocol and the supplementary material.

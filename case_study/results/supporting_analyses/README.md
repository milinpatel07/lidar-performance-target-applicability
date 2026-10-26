# Supporting analyses

Tables computed from the per-detection tables of the case study by the scripts in
[`../../tools/supporting/`](../../tools/supporting/) and [`../../tools/figures/`](../../tools/figures/): the retention
of applicable thresholds, the changes in the detections that accompany a not applicable outcome, intervals, the common
threshold, recall after the vote, annotation checks, the choice of the frames of Fig. 1 and the data of the figures.
`retention_and_causes.py` first recomputes the split-0 cells from the per-detection tables and stops unless they equal the recorded run files, and `common_threshold_and_recall.py` checks that the retention of each own-condition cell equals the one the experiment code computes. Every file is described in [`../../docs/results.md`](../../docs/results.md#supporting-analyses); `*_log.txt`
files are the console output of each script.

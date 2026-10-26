# Tools

Scripts that compute the supporting analyses, the figures, the supplementary material and the data of the pages from
the recorded results and the per-detection tables. The tools read the recorded results, the inputs (`RUM`, `NUSC_META`) and one cache of the per-detection tables in
`work/` (not versioned); [`layout.py`](layout.py) defines these locations. They use the analysis code in
`../experiments/` unchanged. Run order and commands: [`../docs/reproduce.md`](../docs/reproduce.md#3-tools-export-supporting-analyses-figures).

| tool | output |
|---|---|
| `export_tables.py build` | `work/cache/tables.pkl`: per-detection tables of both datasets, checked against the detection pipeline |
| `export_tables.py export` | `work/data/`: split-0 detections per condition and the selected thresholds |
| `../checks/check_export.py` | AUROC, A and R recomputed from the export with independent code |
| `table_and_figure_values.py` | frame counts per condition and part, shares of wrong detections, split-0 values |
| `outcome_counts.py` | outcome counts over every cell of m2, m3, m4 (labels as run, before the KITTI rule) |
| `../checks/check_paper_numbers.py` | every number of the paper recomputed from `results/`; `--write` writes `docs/paper_map.md` |
| `build_explorer_data.py` | `../site/explorer/data/outcomes.json` for the results browser; `--check` compares it with `results/` |
| `build_interactive_data.py` | `../site/interactive/data/units.json` and `separation.json` for the interactive pages; `--check` compares them with `results/` |
| `supplementary/make_supplementary.py` | `docs/supplementary/supplementary.tex` and its sources table; `--check` re-reads every value |
| `supporting/retention_and_causes.py` | retention per applicable cell, changes in the detections (share of wrong detections, medians), intervals, frame counts, recall after the vote, ROC and retention curves |
| `supporting/common_threshold_and_recall.py` | the common threshold τ* per distance condition; recall denominators |
| `supporting/annotation_checks.py` | accepted wrong KITTI boxes without an annotated car nearby |
| `supporting/frame_candidates.py` | frame candidates for the frame figure; blind sample for a visual check; applicable cells at 10⁻² |
| `supporting/m8_tables.py` | outcome counts of the third run and the sequence-level evaluation on KITTI drives, and drives per part |
| `figures/make_figures.py` | figures of the changes in the detections that accompany an exceeded limit, and of the change of dataset and detector |
| `figures/frame_figure.py` | one KITTI and one nuScenes frame with every detection, its acceptance and correctness (frames of the earlier fixed rule: KITTI 004289, nuScenes 703ac7e5; the paper's Fig. 1 is drawn by `figures/paper/frame_figure/`) |
| `figures/paper/` | sources of the figures of the paper as of 21 October 2026 (label wording differs from the submitted figures): [`figures/paper/README.md`](figures/paper/README.md) |
| `figures/supplementary/supplementary_figures.py` | figures of the supplementary material, from `results/` only |

Figures and contact sheets that show dataset images are written to `work/figures/` and are not part of the repository.

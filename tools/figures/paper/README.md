# Figures of the paper

The sources of the figures of the paper as of 21 October 2026. The figures of the submitted paper differ from what
these sources produce in the label wording listed below. The paper itself is not part of the repository;
[`../../../docs/paper_map.md`](../../../docs/paper_map.md) lists the numbers each figure shows.

| figure | label in these sources | label in the submitted figure |
|---|---|---|
| Fig. 2 (`fig_concept.tex`) | "no candidate passes the selection in c" (row no threshold selected) | "lowest candidate fails in c" |
| Fig. 3 (`fig_parts.tex`) | "drawn by frame", "drawn by recorded sequence", "Each division is drawn with five random seeds" | "division by frame", "division by recorded sequence", "Each division is carried out with five random seeds" |
| Fig. 4 (`make_fig_outcomes.py`) | "transferred threshold, one marker per applicable split" | "transferred threshold, one marker per split" |
| Fig. 5 (`make_fig_separation.py`) | y axis "FAP A_c(τ)" | y axis "estimated FAP" |

| figure | content | source | input | data needed |
|---|---|---|---|---|
| Fig. 1 | one KITTI and one nuScenes frame with the transferred and the own threshold | [`frame_figure/fig1_two_panel.py`](frame_figure/fig1_two_panel.py), candidates [`frame_figure/fig1b_candidates.py`](frame_figure/fig1b_candidates.py), drawing helpers [`frame_figure/render_frames.py`](frame_figure/render_frames.py) | per-detection cache, detector outputs, dataset images | yes; the figure shows dataset images and is not published here. Its facts: [`results/supporting_analyses/fig1_two_panel_facts.txt`](../../../results/supporting_analyses/fig1_two_panel_facts.txt) |
| Fig. 2 | the applicability test, schematic | [`fig_concept.tex`](fig_concept.tex) | none | no |
| Fig. 3 | division of the frames into parts, schematic | [`fig_parts.tex`](fig_parts.tex) | none | no |
| Fig. 4 | outcome of every transfer on the five splits, and retention at 10⁻² | [`make_fig_outcomes.py`](make_fig_outcomes.py) writes `fig_outcomes.tex` | `results/supporting_analyses/retention_applicable_cells.csv` | no |
| Fig. 5 | ROC curves and FAP against the threshold, split 0 | [`make_fig_separation.py`](make_fig_separation.py) | `results/supporting_analyses/fig_separation_curves.csv` (written by [`separation_curves.py`](separation_curves.py) from the per-detection cache) | no for the plot, yes for the curves |
| Fig. 6 | lowest limit that n independent units can show to be met | [`fig_units.tex`](fig_units.tex) | Eq. 5 of the paper, and the units per condition of split 0 from `results/supporting_analyses/frames_per_condition.csv`, `results/m7_nuscenes_by_scene/m7_scene_split_summary.txt` and `results/supporting_analyses/m8_drives_per_part.csv` | no |

Compile a TikZ figure with `pdflatex fig_concept.tex` in this folder (`preamble.tex` holds the shared packages and
colours). Run the Python scripts from the repository root:

```bash
mkdir -p work/figures
python3 tools/figures/paper/make_fig_outcomes.py results/supporting_analyses/retention_applicable_cells.csv work/figures/fig_outcomes.tex
python3 tools/figures/paper/make_fig_separation.py results/supporting_analyses/fig_separation_curves.csv work/figures/fig_separation.pdf
python3 tools/figures/paper/separation_curves.py      # needs work/cache/tables.pkl (tools/export_tables.py build)
```

**Values written into the sources.** `make_fig_outcomes.py` holds the outcome counts of Fig. 4 as literals (list
`rows`), and `fig_units.tex` holds the curve of Eq. 5 and the marker positions as coordinates. `tests/check_paper_numbers.py`
compares every count of `make_fig_outcomes.py` with the result files on every push.

**Fig. 1 scripts.** The three scripts in `frame_figure/` are published as they ran, with mount paths normalised. Their path constants are container
paths: `REL / "cache/tables.pkl"` is the cache that `tools/export_tables.py build` writes to
`work/cache/tables.pkl`; `REL / "results/v25"` and `REL / "figures/v25"` are output folders; `/data/inputs` and the nuScenes
metadata folder are the inputs described in [`docs/data.md`](../../../docs/data.md). Adapt these constants to rerun them.
The KITTI frame 005345 was chosen by the authors from
[`results/supporting_analyses/frame_candidates_ranked.csv`](../../../results/supporting_analyses/frame_candidates_ranked.csv);
the nuScenes frame follows the rule in the header of `fig1b_candidates.py` (rank 2 of 2 in
[`fig1b_candidates.csv`](../../../results/supporting_analyses/fig1b_candidates.csv); rank 1 was not used because its wrong
detection lies 1.9 m below an annotated car on a ramp, so its overlap of 0 comes from the height).

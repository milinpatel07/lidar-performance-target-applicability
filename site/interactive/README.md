# Interactive pages

Browser pages that explain the applicability test, compute it and show recorded results of the case study. Static
pages (HTML, CSS, JavaScript, inline SVG; no build step, no external library) served with the repository on
GitHub Pages under `site/interactive/`. They read their data with `fetch`, so open them over HTTP, for example with
`python3 -m http.server -d site` in the repository root and `http://localhost:8000/interactive/`.

| page | what it does | data |
|---|---|---|
| `index.html` | lists the pages | none |
| `walkthrough.html` | Walk-through: the test in seven steps, each with one figure on schematic data from a seeded random number generator; step 6 shows the recorded test units of the case study | `data/units.json` |
| `test.html` | Applicability test calculator: HB p-value for the selection at δ, interval [L, U] at confidence 1 − δ (δ/2 on each side), outcome, minimum number of units of Eq. 5 for selecting (δ′ = δ) and testing (δ′ = δ/2), lowest limit that n units without a false acceptance can show to be met. Loads a recorded row of the sequence-level evaluation and recomputes its L and U | `../explorer/data/outcomes.json` |
| `units.html` | Independent units needed, Fig. 6 of the paper: lowest limit 1 − δ′^(1/n) against n for δ′ = δ and δ/2, target and exploratory limits, an own limit, and the recorded units of each condition per split and part. Marker heights are computed from n, not measured | `data/units.json` |
| `separation.html` | Separation and FAP, Fig. 5 of the paper: ROC curves and estimated FAP against τ for KITTI distance (u_s), nuScenes weather (u_e) and the change of dataset and detector (u_s), test part of split 0, with the recorded operating points and the interval at the threshold selected at 0.1† | `data/separation.json` |
| `own-data.html` | Run the test on your own detections: runs the applicability test on a CSV file of detections (columns `frame`, optional `sequence`, `condition`, optional `part`, `u`, `correct`) or on a seeded synthetic example (`own-data.html#synthetic`): random division into selection and test part if the file has none, candidate thresholds (quantiles or a list), selection by fixed sequence, outcome, [L, U], retention, own-condition check, Eq. 5 warnings, p-value chart, outcome matrix of all ordered pairs, export as CSV and JSON. The file is read locally; nothing is uploaded | the user's file |
| `concept.html` | Four changes in the detections: schematic simulator of the four changes in the detections of Sect. 3.4 (weaker separation, more wrong detections, shifted values, different spread over frames). Invented distributions, not data | none |

Shared code: `apptest.js` (the computation of `own-data.html`; mirrors `analyse()` and `Cell` in
`experiments/m1_range_kitti.py` and `package/src/applicability_test/core.py`; usable in node with `require`), `stats.js` (port of `hb_pvalue`, `hb_upper`, `hb_lower` and `n_required` in
`experiments/m1_range_kitti.py`, plus Eq. 5 and its inverse), `common.js` (SVG and number helpers), `style.css` (same
tokens as `site/explorer/style.css`).

## Provenance of the numbers

Every recorded number on the pages is read from one of these files; each entry in the JSON files names its source
file and line (line 1 is the header).

| JSON | entries | source file |
|---|---|---|
| `data/units.json` | frames per condition, selection and test part | `results/supporting_analyses/frames_per_condition.csv` |
| | nuScenes scenes per condition and part, distance and weather | `results/m7_nuscenes_by_scene/m7_scene_split.csv`, variant `scene_scene_unit` (`n_select_units` in the rows of the condition of selection, `n_eval_units` in the rows of the condition of use with a selected threshold) |
| | nuScenes scenes per part, change of dataset and detector | `results/m8_kitti_by_drive/B_dataset_drive.csv`, `hb_unit` drive, protocol `kitti_ignore` |
| | KITTI drives per condition and part | `results/supporting_analyses/m8_drives_per_part.csv` (grid part left out) |
| | all recorded sequences of a condition (part `all`) | `results/post_hoc/ns_per_condition.csv` |
| `data/separation.json` | ROC points, FAP curve, operating points, interval at τ(0.1) | `results/supporting_analyses/fig_separation_curves.csv` |

`test.html` reads `site/explorer/data/outcomes.json` (written by `tools/build_explorer_data.py`) and offers only the rows
with unit recorded sequence, estimate FAP and a selected threshold (from `m7_scene_split.csv` variant
`scene_scene_unit` and `B_dataset_drive.csv` with `hb_unit` drive). For these rows the files record the mean
per-sequence value Â and the number of test sequences n, and the HB interval depends on the per-unit values only
through their mean and count, so L and U are recomputed from Â·n and n at δ/2 = 0.025. The frame-level rows of
`results/m6_five_splits/` record no number of test frames and are not offered.

Computed on the pages (not read): the HB p-value, L and U of the calculator, the curves and marker heights of
`units.html`, AUROC on `separation.html` (trapezoidal rule over the recorded ROC points, as in
`tools/figures/paper/make_fig_separation.py`), and every value of `concept.html`.

## Rebuild and check

```bash
python3 tools/build_interactive_data.py          # writes site/interactive/data/units.json and separation.json
python3 tools/build_interactive_data.py --check  # exit 1 if they differ from what the result files give
python3 tests/test_stats_js.py             # stats.js against experiments/m1_range_kitti.py and the recorded rows (needs node)
python3 tests/test_own_data_js.py          # apptest.js against a Python reference built on m1 and against package/ (needs node)
```

`tools/build_interactive_data.py --root <path>` reads the result files from another copy of the repository.

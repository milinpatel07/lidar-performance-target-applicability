# Outcome explorer

A static web page (HTML, CSS and JavaScript without libraries or external requests) that shows the outcome of every
cell of the recorded results: pair of conditions, condition of selection → condition of use, indicator, limit α and
splits 0 to 4. The views use the terms of the paper: the frame-level evaluation (division by frame, frame as unit), the
sequence-level evaluation (division by recorded sequence, sequence as unit), the third run (division by recorded
sequence, frame as unit) and the post-hoc Methods A and B. Views that count frames as units carry the note of Fig. 4 of
the paper: frames of one recorded sequence are not independent, so the stated error probability is not guaranteed.

Selecting a cell lists, per split, τ, the estimate, [L, U], retention, units and the source file and line. A small
graphic per split draws [L, U] against α and, where the file records the test units n, n against the minimum of Eq. 5
for testing, n ≥ ln(δ/2)/ln(1 − α) with δ = 0.05. The address of the page keeps the view, filters and the chosen cell
(for example `#view=seq_seq&rule=1&ind=u_s&limit=0.1&own=0`), so that a link opens the same state. "Download this view
as CSV" saves the records shown, with the term of the view in the first column.

- Online: https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/
- Locally: run `python -m http.server` in the repository root and open http://localhost:8000/explorer/ (opening
  `index.html` as a file does not work, because the browser blocks reading `data/outcomes.json` from disk).
- Data: `data/outcomes.json` is written by `python tools/build_explorer_data.py` from the CSV files in `results/`;
  the script stops if the frame-level counts differ from the table in `docs/results.md`.
  `python tools/build_explorer_data.py --check` exits with 1 if the committed file differs from a fresh build.
- Test: `node tools/test_explorer.mjs` tests the functions of `app.js` that do not touch the page (selection of
  records, counts, Eq. 5, link and address formats, CSV export) and compares the counts of the frame-level and
  sequence-level evaluations with the paper (168 of 240 and 5 of 240 transfer outcomes applicable or not applicable).

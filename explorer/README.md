# Outcome explorer

A static web page (HTML, CSS and JavaScript without libraries or external requests) that shows the outcome of every
cell of the recorded results: pair of conditions, condition of selection → condition of use, indicator, limit α and
splits 0 to 4, for the division by frame, the division by recorded sequence (frame or recorded sequence as unit) and
the post-hoc Methods A and B. Selecting a cell lists τ, the estimate, [L, U], retention, units and the source file and
line of each split.

- Online: https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/
- Locally: run `python -m http.server` in the repository root and open http://localhost:8000/explorer/ (opening
  `index.html` as a file does not work, because the browser blocks reading `data/outcomes.json` from disk).
- Data: `data/outcomes.json` is written by `python tools/build_explorer_data.py` from the CSV files in `results/`;
  the script stops if the division-by-frame counts differ from the table in `docs/results.md`.
  `python tools/build_explorer_data.py --check` exits with 1 if the committed file differs from a fresh build.

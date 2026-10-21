# Notebooks

`explore_results.ipynb` reads only the CSV files in `../results/` and `../docs/results.md`, and needs pandas and
matplotlib. It (a) rebuilds the outcome table of `docs/results.md` from the run files and asserts that every entry is
equal, (b) builds the same table for the division by recorded sequence (variants (i) and (ii)) and post-hoc Method A,
(c) gives the retention of applicable transfers at 10⁻², (d) compares the minimum number of independent units
n ≥ ln δ′ / ln(1 − α) with the frames and recorded sequences per condition, (e) lists the AUROC intervals and
(f) draws the outcome grid. It is stored with its outputs.

- Online (read only): open the file on GitHub, which shows the stored outputs. The page of the outcome explorer is at
  https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/
- Locally: run `jupyter lab` (or `jupyter notebook`) and open `notebooks/explore_results.ipynb`; Jupyter starts the kernel
  in the notebook's folder, so `../results` resolves.
- Rerun and check: `python -m nbconvert --to notebook --execute --inplace notebooks/explore_results.ipynb`; an
  `assert` stops the run if the files and `docs/results.md` disagree.

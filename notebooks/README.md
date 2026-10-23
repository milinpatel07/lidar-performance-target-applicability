# Notebooks

A notebook for readers who want to work with the recorded results of the case study in Python.
`explore_results.ipynb` reads only the CSV files in `../results/` and `../docs/results.md`, and needs pandas and
matplotlib. It (a) rebuilds the outcome table of the frame-level evaluation in `docs/results.md` from the run files and
asserts that every entry is equal, (b) builds the same table for the third run, the sequence-level evaluation and the
post-hoc sequence test (Method A), (c) gives the retention of applicable transfers at 10⁻², (d) compares the
zero-failure bound n ≥ ln δ′ / ln(1 − α) (paper Eq. 5) with the frames and recorded sequences per condition, (e) lists
the post-hoc AUROC intervals and (f) draws the outcome grid. It is stored with its outputs. Terms:
[`../docs/glossary.md`](../docs/glossary.md); the idea of the test: [`../docs/concept.md`](../docs/concept.md).

- Online (read only): open the file on GitHub, which shows the stored outputs. The results browser is at
  https://milinpatel07.github.io/lidar-performance-target-applicability/explorer/
- Locally: run `jupyter lab` (or `jupyter notebook`) and open `notebooks/explore_results.ipynb`; Jupyter starts the kernel
  in the notebook's folder, so `../results` resolves.
- Rerun and check: `python -m nbconvert --to notebook --execute --inplace notebooks/explore_results.ipynb`; an
  `assert` stops the run if the files and `docs/results.md` disagree.

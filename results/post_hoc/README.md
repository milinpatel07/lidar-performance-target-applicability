# Post-hoc analyses

The analyses in this folder were added **after** the parameters of the study (error probability δ = 0.05, the limits,
the conditions, the per-frame false acceptance proportion) were fixed and after the outcomes of the paper were known.
They are not part of the predictions fixed in advance ([`../../docs/study_protocol/`](../../docs/study_protocol/)).
The limits 0.05 and 0.1 (marked †) are exploratory and are not safety targets.

| analysis | what it does | where |
|---|---|---|
| Method A | Sequence-level test of the per-frame false acceptance proportion (FAP). The recorded sequence (KITTI drive, nuScenes scene) is the independent unit, and the per-frame target A_c(τ) = E[a_f(τ) \| f ∈ c] ≤ α is kept: with S_s the sum of a_f over the N_s frames of sequence s in condition c, each sequence enters the paper's selection and test as Y_s = (S_s − αN_s + αN_max)/N_max, which lies in [0, 1] and has E[Y] ≤ α exactly when A_c ≤ α. | [`REPORT.md`](REPORT.md), [`outcomes.csv`](outcomes.csv) (method A), [`summary.csv`](summary.csv) |
| Method B | Sensitivity check of the evaluation step of Method A with the betting confidence interval of Waudby-Smith and Ramdas (hedged capital process, each side at δ/2), using the `confseq` package; the thresholds are those selected by Method A. | [`outcomes.csv`](outcomes.csv) (method B), [`summary.csv`](summary.csv) |
| AUROC intervals | 95 % percentile bootstrap intervals (2,000 replicates, recorded sequences resampled) for the AUROC values of the three pairs of conditions in the separation figure, evaluation part of split 0, and for their differences. | [`auroc_bootstrap.csv`](auroc_bootstrap.csv) |
| Epoch check | Number of training epochs of the four nuScenes ensemble members, read from the training configurations, training logs and checkpoints. The configurations set 20 epochs; training ended after epoch 10, and the checkpoints used for inference hold about 10 epochs. | [`epoch_check.txt`](epoch_check.txt), [`REPORT.md`](REPORT.md) section 5 |

Before any new number, the code recomputed the recorded frame-unit results with every frame as its own sequence
(N_s = 1) and the recorded sequence-division results with frame units; [`GATE_PASSED.txt`](GATE_PASSED.txt) gives the
comparison. [`ns_per_condition.csv`](ns_per_condition.csv) lists the frames per sequence, and
[`provenance.json`](provenance.json) the script version, seeds and input hashes.

## Code

[`code/`](code/) holds the scripts that produced these files (MIT licence, as `analysis/`):

- `seq_ratio.py`: Methods A and B and the AUROC intervals. It imports the statistics (Hoeffding-Bentkus p-value and
  bounds, fixed-sequence selection, splits) unchanged from the scripts in [`../../analysis/`](../../analysis/); the path
  constant `CODE` names the folder that holds them.
- `tests/test_seq_ratio.py`: sanity tests (N_s = 1 reproduces the frame-unit outcomes; the transform keeps the
  condition E[S]/E[N] ≤ α; zero false acceptances give the implied p-value; coverage of the betting interval).
- `check_epochs.sh`: the epoch check (reads only).
- `make_report.py`: writes `REPORT.md` from the files of this folder.

Order of the steps: `check_epochs.sh`, the tests, `seq_ratio.py`, `make_report.py`; the run stops if a test or
the reproduction check fails.

The scripts read the per-detection tables, the nuScenes metadata and the KITTI devkit mapping files described in
[`../../docs/data.md`](../../docs/data.md); `confseq` 0.0.11 is needed for Method B.

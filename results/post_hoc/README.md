# Post-hoc analyses

The analyses in this folder were added **after** the parameters of the study (error probability δ = 0.05, the limits,
the conditions, the per-frame false acceptance proportion) were fixed and after the outcomes of the paper were known.
They are not part of the predictions fixed in advance ([`../../docs/study_protocol/`](../../docs/study_protocol/README.md)),
and the paper does not report the post-hoc sequence test or the AUROC intervals. The limits 0.05 and 0.1 (marked †)
are exploratory and define no performance target.

**Terms.** [`REPORT.md`](REPORT.md) is a recorded file and keeps the wording of its date. Its "sequence-level test" is
called the **post-hoc sequence test (Method A)** in the rest of the repository, so that it cannot be confused with the
**sequence-level evaluation** of the paper (division by recorded sequence, sequence as unit, the value of a sequence
being the mean of a_f over its frames). Further terms in REPORT.md:

| in REPORT.md and the files of this folder | term of the paper and of this repository |
|---|---|
| "Sequence-level test", Method A, `method` = `A` | post-hoc sequence test (Method A) |
| "frame division, frame unit", "frame unit" | frame-level evaluation |
| "paper's sequence-unit analysis", "paper sequence unit" (m7/m8) | sequence-level evaluation |
| "sequence division with frame units" (gate) | third run |
| "decided transfers" (section 2) | transfers with an applicable or not applicable outcome |
| "Self-check" (section 3) | own-condition check |
| "evaluation part" | test part |
| `established`, `applied` | condition of selection, condition of use |

| analysis | what it does | where |
|---|---|---|
| post-hoc sequence test (Method A) | The recorded sequence (KITTI drive, nuScenes scene) is the independent unit, and the per-frame target A_c(τ) = E[a_f(τ) \| f ∈ c] ≤ α is kept. With S_s the sum of a_f over the N_s frames of sequence s in condition c and N_max the largest N_s over all validation sequences of c, each sequence enters the selection and the test of the paper (HB, δ = 0.05, bounds at δ/2) as Y_s = (S_s − αN_s + αN_max)/N_max. Y_s lies in [0, 1], and E[Y] ≤ α exactly when E[S]/E[N] ≤ α, that is, when the FAP is at most α. The sequence-level evaluation of the paper instead bounds the mean over sequences of the per-sequence means of a_f, which equals the FAP only if long and short sequences have the same mean of a_f on average. Divisions and candidate thresholds as in the paper. | [`REPORT.md`](REPORT.md) sections 1 to 3, [`outcomes.csv`](outcomes.csv) (`method` = `A`), [`summary.csv`](summary.csv) |
| Method B | Sensitivity check of the test step of Method A: the bounds come from the betting confidence interval of Waudby-Smith and Ramdas (hedged capital process, each side at δ/2, `confseq` package); the thresholds are those selected by Method A. | [`outcomes.csv`](outcomes.csv) (`method` = `B`), [`summary.csv`](summary.csv) |
| AUROC intervals (post hoc) | 95 % percentile bootstrap intervals (2,000 replicates, recorded sequences resampled) for the AUROC values of the three pairs of conditions in Fig. 5, test part of split 0, and for their differences. The paper reports these AUROC values as point estimates (column `point`) without an interval. | [`auroc_bootstrap.csv`](auroc_bootstrap.csv), REPORT.md section 4 |
| Epoch check | Number of training epochs of the four nuScenes ensemble members, read from the training configurations, training logs and checkpoints. The configurations set 20 epochs; training ended after epoch 10, and the checkpoints used for inference hold about 10 epochs (paper Sect. 4.1). | [`epoch_check.txt`](epoch_check.txt), REPORT.md section 5 |

Over all 400 transfer outcomes, Method A gave 5 applicable and 0 not applicable outcomes; none of the 14 transfer
cells with a not applicable outcome on at least one split in Fig. 4 was not applicable under Method A (REPORT.md sections 1 and 2).

Before any new number, the code recomputed the recorded frame-level results with every frame as its own sequence
(N_s = 1) and the recorded third-run results (division by recorded sequence, frame units); [`GATE_PASSED.txt`](GATE_PASSED.txt)
gives the comparison (1,600 rows, 0 differ). [`ns_per_condition.csv`](ns_per_condition.csv) lists the frames per
sequence, and [`provenance.json`](provenance.json) the script version, seeds and input hashes.

## Code

[`code/`](code/) holds the scripts that produced these files (MIT licence, as `experiments/`):

- `seq_ratio.py`: Methods A and B and the AUROC intervals. It imports the statistics (Hoeffding-Bentkus p-value and
  bounds, fixed-sequence selection, division into parts) unchanged from the scripts in [`../../experiments/`](../../experiments/README.md);
  the path constant `CODE` names the folder that holds them.
- `tests/test_seq_ratio.py`: sanity tests (N_s = 1 reproduces the frame-level outcomes; the transform keeps the
  condition E[S]/E[N] ≤ α; zero false acceptances give the implied p-value; coverage of the betting interval).
- `check_epochs.sh`: the epoch check (reads only).
- `make_report.py`: writes `REPORT.md` from the files of this folder.

Order of the steps: `check_epochs.sh`, the tests, `seq_ratio.py`, `make_report.py`; the run stops if a test or
the reproduction check fails.

The scripts read the per-detection tables, the nuScenes metadata and the KITTI devkit mapping files described in
[`../../docs/data.md`](../../docs/data.md); `confseq` 0.0.11 is needed for Method B
([`../../environment/requirements-posthoc.txt`](../../environment/requirements-posthoc.txt)).

**Paths.** The scripts are published as they ran, with mount paths normalised, so that the SHA-256 in [`provenance.json`](provenance.json) matches
`code/seq_ratio.py`. Their path constants are container paths (`/data/work` is the working folder of the runs). The corresponding locations in this repository:

| constant in the scripts | in this repository |
|---|---|
| `/data/work/code/experiments/` (`CODE`), the analysis scripts loaded through m6 | [`experiments/`](../../experiments/README.md) (same files; m3 and m6 at versions m3-0.4 and m6-0.3) |
| `/data/work/cache/tables.pkl` | `work/cache/tables.pkl`, written by `tools/export_tables.py build` |
| `/data/work/m6/results/*.csv` | [`results/m6_five_splits/`](../m6_five_splits/) |
| `/data/work/results/m7_scene_split.csv` | [`results/m7_nuscenes_by_scene/m7_scene_split.csv`](../m7_nuscenes_by_scene/m7_scene_split.csv) |
| `/data/work/results/m8/*.csv` | [`results/m8_kitti_by_drive/`](../m8_kitti_by_drive/) |
| `/data/work/ext/kitti_devkit` (`--devkit`) | KITTI devkit mapping files, see `docs/data.md` |
| default of `--nusc-meta` | nuScenes v1.0-trainval metadata folder (`NUSC_META` in `tools/layout.py`) |
| `/data/inputs` (in `check_epochs.sh`) | detector outputs, training logs and checkpoints (`RUM`) |

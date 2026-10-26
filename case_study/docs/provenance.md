# Detector provenance

Where the detections that every result in this repository is computed from come from: the toolbox, the
configurations, the training runs, the checkpoints that inference loaded and the software environment. The facts below
were read on the training machine on 2026-10-23 (configuration files, training and inference logs, the epoch and
iteration stored in each checkpoint, `sha256sum`). The configuration files themselves are in
[`configs/detectors/`](../configs/detectors/README.md).

## Toolbox

| item | value |
|---|---|
| toolbox | OpenPCDet, `pcdet/version.py`: `0.6.0+233f849` |
| commit | `233f849829b6ac19afb8af8837a0246890908755` (2025-10-08) of https://github.com/open-mmlab/OpenPCDet |
| stored in the checkpoints | `pcdet+0.6.0+233f849` |
| local changes | 7 files, listed in [`../configs/detectors/openpcdet_base/openpcdet_local_modifications.diff`](../configs/detectors/openpcdet_base/openpcdet_local_modifications.diff): NumPy type aliases (`np.int`, `np.bool`, `np.float` replaced by `np.int64`, `np.bool_`, `np.float64`), the Argoverse 2 dataset import disabled, and a `--seed` option in `tools/train.py` that seeds with `seed + LOCAL_RANK`. The diff is the state of the working tree on 2026-10-23; whether every change predates training was not checked. |

## Ensembles

Each ensemble has four PointPillars members trained from different random seeds, without a pretrained model, one GPU
per member. Merging, the vote of three of four members and the two indicators are described in
[`method.md`](method.md#1-detector-detections-and-indicators).

| | KITTI ensemble | nuScenes ensemble |
|---|---|---|
| member configuration | [`pointpillar_kitti_v2_seed{1..4}.yaml`](../configs/detectors/kitti/) | [`cbgs_pp_multihead_nuscenes_seed{1..4}.yaml`](../configs/detectors/nuscenes/) |
| base | `kitti_models/pointpillar.yaml`, `NUM_EPOCHS` 10 (80 in the base) | `nuscenes_models/cbgs_pp_multihead.yaml` (class-balanced multi-head), `NUM_EPOCHS` 20 |
| training data | 3,712 frames (`ImageSets/train.txt`) | `nuscenes_infos_10sweeps_train` of v1.0-trainval (700 training scenes, 28,130 samples) |
| command line | `--batch_size 2 --seed k` (overrides the configured 4 per GPU) | `--batch_size 4 --seed k` |
| training period (UTC) | 2026-05-11, 11:12 to about 12:05 | 2026-04-28 17:15 to 2026-05-10/11 |
| epochs run | 10 of 10 | 10 of 20; training was stopped after epoch 10, before the learning-rate schedule (one cycle over 20 epochs) had decayed |
| score cut-off at inference | 0.1 | 0.1 |

The KITTI validation frames (`ImageSets/val.txt`, 3,769 frames) come from 45 recorded drives, none of which contributes
training frames ([`data.md`](data.md)).

## Checkpoints loaded by inference

Every member's inference loaded `ckpt/latest_model.pth` of its training output. The table gives what that file is.

| member | file loaded | stored epoch / iteration | size (bytes) | SHA-256 |
|---|---|---|---|---|
| KITTI 1 | symbolic link to `checkpoint_epoch_10.pth` | 10 / 18,560 | 58,092,639 | `8c953bdffb5167112ac078299c472d4fdc0b071de5ce7b5cef5bda95af0a726a` |
| KITTI 2 | snapshot saved during epoch 10 | 9 / 18,542 | 58,092,114 | `b7aa73e35970ef6cf8bea1486fcb079e0b25db5a6b604a20dd40b16495bfa2f0` |
| KITTI 3 | snapshot saved during epoch 10 | 9 / 18,491 | 58,092,340 | `6361773b3399ac43c02b972aeec5df0af7232017f752cb740562932eb29bf516` |
| KITTI 4 | snapshot saved during epoch 10 | 9 / 18,514 | 58,092,485 | `b2af208bd901e2bb0c53a0a39bcf9654157ea13c1f7068f4a2a43a5a866a3e82` |
| nuScenes 1 | snapshot saved during epoch 10 | 9 / 308,860 | 73,172,015 | `6f27cdf469d4a45c2508d97fbebd89f1f66a06bd2f8dd7b2051530d539055397` |
| nuScenes 2 | snapshot saved during epoch 10 | 9 / 308,840 | 73,171,828 | `bd0e959e7c37f1c4dd0e590ea80668ca5ed0ef08e099405fd55dc1f1079318e4` |
| nuScenes 3 | snapshot saved during epoch 10 | 9 / 308,899 | 73,172,447 | `5916db095d45a5a8d630cd51ea8c77e2c0b0d6f043ab2bc3868eef4355f31a56` |
| nuScenes 4 | snapshot saved during epoch 10 | 9 / 308,842 | 73,172,689 | `d954541b9fb5f39e1416c3a91ecdc0486c7f2b95e5e59009cbdf4c78656f75c6` |

The stored epoch counter of a snapshot saved during epoch 10 is 9 (OpenPCDet stores the last completed epoch). An epoch
of the KITTI training has 1,856 iterations (18,560 after ten), so the KITTI members 2 to 4 are 18, 69 and 46
iterations short of the end of epoch 10, and member 1 is at its end. An epoch of the nuScenes training has 30,895
iterations (training log), so the nuScenes snapshots lie 51 to 110 iterations before the end of epoch 10 of 20; the
earlier record of this is
[`../results/post_hoc/epoch_check.txt`](../results/post_hoc/epoch_check.txt). The checkpoints are not distributed.

## Software environment

| item | value |
|---|---|
| container image | the analysis image (local build, image id `sha256:36077376c42c231f7d597110d563bff17f98e8b6f319fce10e56c5e729788952`, created 2025-06-11), Ubuntu 22.04.3 |
| Python and libraries | Python 3.10.13, PyTorch 2.2.1 (CUDA 12.1, cuDNN 8.9.2), torchvision 0.17.1, spconv-cu120 2.3.6, NumPy 1.26.3, SciPy 1.15.2, pandas 2.2.3, Matplotlib 3.10.0, scikit-learn 1.6.1, numba 0.61.0, kornia 0.8.0 |
| full package list | [`../configs/detectors/environment/pip_freeze.txt`](../configs/detectors/environment/pip_freeze.txt) |
| OpenPCDet | not installed as a package; used from its source tree through `PYTHONPATH` |
| added for the post-hoc analyses | confseq 0.0.11, dill 0.4.1, multiprocess 0.70.19, pytest 9.1.1 ([`../environment/requirements-posthoc.txt`](../environment/requirements-posthoc.txt)) |

The analysis scripts and tools of this repository need only the CPU packages in
[`../environment/requirements.txt`](../environment/requirements.txt) (and the [`../environment/Dockerfile`](../environment/Dockerfile)); they read the detector outputs, not
the networks. That the training ran in the same image is stated in the project notes but could not be confirmed from
the machine, because the training container no longer exists.

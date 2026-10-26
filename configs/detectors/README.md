# Detector configurations

The configurations with which the eight PointPillars members of the two ensembles were trained, copied from the
training machine. What was trained, for how long, and which checkpoint each member's inference loaded is in
[`docs/provenance.md`](../../docs/provenance.md).

| folder | content |
|---|---|
| `kitti/` | `pointpillar_kitti_v2_seed1.yaml` ... `seed4.yaml`: the four KITTI members (identical files; the seed is passed on the command line as `--seed k`) |
| `nuscenes/` | `cbgs_pp_multihead_nuscenes_seed1.yaml` ... `seed4.yaml`: the four nuScenes members (each with a header `RANDOM_SEED: k`) |
| `openpcdet_base/` | the OpenPCDet configurations the member files derive from or include, unmodified at commit 233f849, and `openpcdet_local_modifications.diff`, the changes in the OpenPCDet working tree on the training machine |
| `environment/pip_freeze.txt` | `pip freeze` of the analysis container image (inference and analysis; whether training ran in the same image could not be confirmed, see [`provenance.md`](../../docs/provenance.md#software-environment)) |

Differences from the OpenPCDet base files:

- KITTI member = `kitti_models/pointpillar.yaml` with `NUM_EPOCHS: 80` changed to `10`.
- nuScenes member = `nuscenes_models/cbgs_pp_multihead.yaml` with four header lines prepended (comment and
  `RANDOM_SEED: k`); `NUM_EPOCHS` stays 20.

Both include `cfgs/dataset_configs/kitti_dataset.yaml` or `nuscenes_dataset.yaml` (in `openpcdet_base/`).

SHA-256 of the files as they are on the training machine:

| file | SHA-256 |
|---|---|
| `kitti/pointpillar_kitti_v2_seed{1..4}.yaml` | `4f4cf3d7be7b142a7d5a05737c126799e392b02634361c501f98993575df2166` |
| `nuscenes/cbgs_pp_multihead_nuscenes_seed1.yaml` | `212ab4d2e7cc76329e8a146817ab5375da0acb211eecff723cdf0049643acec6` |
| `nuscenes/cbgs_pp_multihead_nuscenes_seed2.yaml` | `cf00385899bc08c0c72aa8e1fd8fee138169a18d591d88225acc84d8085ac5c1` |
| `nuscenes/cbgs_pp_multihead_nuscenes_seed3.yaml` | `3b026f21d615246a7af11648529fd8aa562431a90ab2053de7fb1e90246b243a` |
| `nuscenes/cbgs_pp_multihead_nuscenes_seed4.yaml` | `b54836589d3bab01892c62f68bd01f219394221ca00a6bf2c54017eab2991087` |
| `openpcdet_base/kitti_dataset.yaml` | `a6c44a7b0f15b94e135946cecbd8b5541906a69d37811705e9884a411e7b1797` |
| `openpcdet_base/nuscenes_dataset.yaml` | `a9a561d3da8a05e0537da55c15817b19dd5ff60c968a562d9475bc71094e1036` |
| `openpcdet_base/pointpillar.yaml` | `170a9ffe76cfd8509d1044cfbcf1cbd44c5d320fda81bf0089a8d5efaf1c91c8` |
| `openpcdet_base/cbgs_pp_multihead.yaml` | `1f628098208d1619d9373ab8ff90904a4e3582227d5676ea9ef5a94530848dad` |

Licence: the files in this folder are derived from OpenPCDet (https://github.com/open-mmlab/OpenPCDet), which is
licensed under the Apache License 2.0, and remain under that licence. They are excluded from the CC BY-NC-SA 4.0 licence
of the other configuration files (see `LICENSE-results`).

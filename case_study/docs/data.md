# Data

Which datasets the case study uses, what of them this repository does not contain, and which input files the scripts
read.

## Datasets

| dataset | split used | frames | licence |
|---|---|---|---|
| [KITTI 3D object detection](https://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d) | validation half of the training set (3,769 frames, the common 3,712 / 3,769 split) | 3,769 from 45 recorded drives | CC BY-NC-SA 3.0 |
| [nuScenes v1.0-trainval](https://www.nuscenes.org/nuscenes) | validation scenes | 6,019 key frames from 150 scenes | nuScenes terms of use |

The KITTI object frames are mapped to their recorded drives with `mapping/train_rand.txt` and
`mapping/train_mapping.txt` of the public KITTI object development kit (`devkit_object.zip`); the validation frames
come from 45 drives.

## What is not included, and why

No point clouds, images, annotations, detector outputs or per-detection tables are in this repository. They are
part of, or derived from, the datasets and fall under the dataset licences. The recorded results contain counts,
proportions, intervals, thresholds and frame identifiers only.

## Inputs the scripts read

The scripts read their inputs from one folder, mounted read-only at `/data/inputs` (option `--rum`, or the environment
variable `RUM` for the tools). It holds the outputs of the detector ensembles and the dataset files in this layout:

```
/data/inputs/
  detections/kitti_v2/seed1_val.pkl ... seed4_val.pkl    per-network detections, KITTI validation frames
  detections/kitti_v2/scored_val.pkl                      merged detections of the pipeline and the merge parameters
  detections/kitti_v2/frame_errors_cache.pkl              per-frame missed and false detections (consistency check)
  detections/nuscenes/...                                 the same four kinds of file for nuScenes
  third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl    KITTI annotations (OpenPCDet info file)
  data/nuscenes/v1.0-trainval/nuscenes_infos_10sweeps_val.pkl   nuScenes annotations (OpenPCDet info file)
  data/kitti/training/{calib,image_2,velodyne}/           KITTI calibration, images, point clouds (tools only)
  data/nuscenes/v1.0-trainval/samples/                    nuScenes sweeps and camera images (tools only)
  configs/*.yaml                                          detector configurations (score cut-off, tools only)
```

The weather conditions and the division by recorded scene also read `scene.json` and `sample.json` of nuScenes v1.0-trainval (option
`--nusc-meta`, or `NUSC_META` for the tools); the frame figure also reads `sample_data.json`, `ego_pose.json` and
`calibrated_sensor.json`. The division by recorded KITTI drive reads the two devkit mapping files (option `--devkit`).

[`../results/INPUT_HASHES.md`](../results/INPUT_HASHES.md) lists the SHA-256 of every input file of every run. A rerun
reproduces a recorded run only if its inputs have these hashes.

## Where the detector outputs come from

The ensembles were trained with OpenPCDet 0.6.0 (four seeds per dataset, score cut-off 0.1): the KITTI members for 10
epochs on the 3,712 training frames, the nuScenes members on the 700 training scenes for about 10 of the 20 configured
epochs (training ended after epoch 10; [`../results/post_hoc/epoch_check.txt`](../results/post_hoc/epoch_check.txt)).
Configurations, training runs, the checkpoint each member's inference loaded (with SHA-256) and the software
environment are in [`provenance.md`](provenance.md). The outputs were merged as
described in [`method.md`](method.md#1-detector-detections-and-indicators). The two indicators are taken from the
conference paper that introduced them (the spatial indicator, Eq. 1 of the paper, is adapted from it):

> M. Patel, R. Jung. Uncertainty evaluation to support safety of the intended functionality analysis for identifying
> performance insufficiencies in ML-based LiDAR object detection. In: Proceedings of the 12th International Conference
> on Vehicle Technology and Intelligent Transport Systems (VEHITS), pp. 154-167. SciTePress, 2026.
> [doi:10.5220/0014967200004030](https://doi.org/10.5220/0014967200004030)

The detector outputs are not distributed; to request them for a reproduction, contact the authors
(milin.patel@hs-kempten.de, rolf.jung@hs-kempten.de).

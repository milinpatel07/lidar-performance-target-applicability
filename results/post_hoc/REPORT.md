# Sequence-level test of the per-frame target (post-hoc analysis)

**Post-hoc.** This analysis was added after the outcomes of the paper were known. It is not part of the predictions fixed in advance. † marks the exploratory limits 0.05 and 0.1, which are not safety targets.

Method A: recorded sequence (KITTI drive, nuScenes scene) as the independent unit, per-frame target kept through Y_s = (S_s − αN_s + αN_max)/N_max; selection and evaluation as in the paper (HB, δ = 0.05, bounds at δ/2). Method B: evaluation bounds from the betting interval (Waudby-Smith and Ramdas, `confseq` 0.0.11, hedged capital process, θ = 1/2), selection from Method A. Division by recorded sequence as in the paper (m7 scenes, m8 drives; for the change of dataset and detector, the existing m8 division into halves of KITTI drives and nuScenes scenes, so no new division was built). Splits 0 to 4; candidate thresholds as in the paper.

Checks: GATE PASSED: 1600 recomputed rows compared with the recorded rows (frame division with N_s = 1 against m6 A/B and m7 frame rows; sequence division with frame units against m7 scene_frame_unit and m8 frame-unit rows); 0 differ. Sanity tests (`tests/test_seq_ratio.py`): 5 passed in 145.67s (0:02:25).

## 1. Not applicable outcomes of Fig. 4 under Method A

Fig. 4 (frame division, frame unit) holds 14 transfer cells (pair, direction, indicator, limit) with a not applicable outcome on at least one split. Method A gives not applicable in 0 of them.

| pair | transfer | indicator | α | frame unit: not appl. | A: not appl. | A: not det. | A: appl. | A: none sel. | B: not appl. |
|---|---|---|---|---|---|---|---|---|---|
| KITTI distance | near->far | u_e | 0.05† | 2/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| KITTI distance | near->far | u_e | 0.1† | 5/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| KITTI distance | near->far | u_s | 1e-2 | 1/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| KITTI distance | near->far | u_s | 0.05† | 5/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| KITTI distance | near->far | u_s | 0.1† | 5/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| change of dataset and detector | nuScenes->KITTI | u_s | 1e-2 | 5/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| change of dataset and detector | nuScenes->KITTI | u_s | 0.05† | 5/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| change of dataset and detector | nuScenes->KITTI | u_s | 0.1† | 5/5 | 0/5 | 5 | 0 | 0 | 0/5 |
| nuScenes distance | far->near | u_e | 1e-2 | 3/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| nuScenes distance | near->far | u_e | 0.1† | 5/5 | 0/5 | 1 | 3 | 1 | 0/5 |
| nuScenes distance | near->far | u_s | 0.1† | 5/5 | 0/5 | 0 | 2 | 3 | 0/5 |
| nuScenes weather | clear->rain | u_e | 0.05† | 1/5 | 0/5 | 0 | 0 | 5 | 0/5 |
| nuScenes weather | clear->rain | u_e | 0.1† | 4/5 | 0/5 | 5 | 0 | 0 | 0/5 |
| nuScenes weather | clear->rain | u_s | 0.1† | 1/5 | 0/5 | 5 | 0 | 0 | 0/5 |

## 2. Decided transfers under Method A

Over all transfers (4 pairs × 2 directions × 2 indicators × 5 limits × 5 splits = 400 outcomes), Method A gave 5 applicable and 0 not applicable outcomes. The last column counts the splits on which the paper's sequence-unit analysis (loss = mean of a_f over the frames of a sequence, m7/m8) gave the same outcome.

| pair | direction | indicator | α | outcome | A splits | paper sequence unit, same outcome |
|---|---|---|---|---|---|---|
| nuScenes distance | near->far | u_e | 0.1† | applicable | 3/5 | 2/5 |
| nuScenes distance | near->far | u_s | 0.1† | applicable | 2/5 | 2/5 |

Splits on which Method A selected a threshold (all other condition, indicator and limit combinations: none):

| pair | established | indicator | α | splits |
|---|---|---|---|---|
| change of dataset and detector | nuScenes | u_e | 0.1† | 5/5 |
| change of dataset and detector | nuScenes | u_s | 0.1† | 5/5 |
| nuScenes distance | far | u_e | 0.1† | 5/5 |
| nuScenes distance | far | u_s | 0.1† | 5/5 |
| nuScenes distance | near | u_e | 0.1† | 4/5 |
| nuScenes distance | near | u_s | 0.1† | 2/5 |
| nuScenes weather | clear | u_e | 0.1† | 5/5 |
| nuScenes weather | clear | u_s | 0.1† | 5/5 |

## 3. Self-check (threshold used in its own condition of selection)

Counts over 4 pairs × 2 conditions × 2 indicators × 5 limits × 5 splits per method. With independent sequences, the frequency of not applicable among selected thresholds is bounded by δ + δ/2 = 0.075.

| method | applicable | no threshold selected | not determined |
|---|---|---|---|
| A | 9 | 364 | 27 |
| B | 34 | 364 | 2 |

- Method A: not applicable in 0 of 36 self-checks with a selected threshold (0.000).
- Method B: not applicable in 0 of 36 self-checks with a selected threshold (0.000).

## 4. AUROC of Fig. 5 with a sequence bootstrap

Evaluation part of split 0 (frame division, as in Fig. 5), 2000 replicates, seed 20261021, percentile interval. Near/far: drives resampled once for both conditions; clear/rain and the two datasets: sequences resampled within each condition.

| pair | indicator | quantity | point | 95 % interval | sequences | resampling |
|---|---|---|---|---|---|---|
| KITTI distance | u_s | AUROC near | 0.915 | [0.884, 0.946] | 39 | joint |
| KITTI distance | u_s | AUROC far | 0.845 | [0.831, 0.860] | 25 | joint |
| KITTI distance | u_s | AUROC far - AUROC near | -0.069 | [-0.091, -0.046] |  | joint |
| nuScenes weather | u_e | AUROC clear | 0.844 | [0.819, 0.869] | 111 | per condition |
| nuScenes weather | u_e | AUROC rain | 0.856 | [0.821, 0.887] | 24 | per condition |
| nuScenes weather | u_e | AUROC rain - AUROC clear | 0.012 | [-0.030, 0.051] |  | per condition |
| change of dataset and detector | u_s | AUROC nuScenes | 0.749 | [0.734, 0.765] | 150 | per condition |
| change of dataset and detector | u_s | AUROC KITTI | 0.905 | [0.886, 0.922] | 42 | per condition |
| change of dataset and detector | u_s | AUROC KITTI - AUROC nuScenes | 0.157 | [0.133, 0.180] |  | per condition |

## 5. Training epochs of the nuScenes members (item C, nothing changed)

- Configurations `runtime-monitoring/configs/cbgs_pp_multihead_nuscenes_seed{1..5}.yaml`: NUM_EPOCHS = 20.
- Training logs `runtime-monitoring/training_seed{1..4}_nuscenes.log`, last epoch markers: Train:   10/20; Train:   11/20; Train:   10/20; Train:   11/20; Train:   10/20; Train:   11/20; Train:   10/20; Train:   11/20.
- Checkpoint files per member (`third_party/OpenPCDet/output/workspace/configs/cbgs_pp_multihead_nuscenes_seed<s>/seed_<s>/ckpt/`): checkpoint_epoch_10.pth, checkpoint_epoch_6.pth, checkpoint_epoch_7.pth, checkpoint_epoch_8.pth, checkpoint_epoch_9.pth, latest_model.pth.
- Inference logs `runtime-monitoring/logs/nuscenes_inference_seed<s>.log` load: /workspace/third_party/OpenPCDet/output/workspace/configs/cbgs_pp_multihead_nuscenes_seed1/seed_1/ckpt/latest_model.pth; /workspace/third_party/OpenPCDet/output/workspace/configs/cbgs_pp_multihead_nuscenes_seed2/seed_2/ckpt/latest_model.pth; /workspace/third_party/OpenPCDet/output/workspace/configs/cbgs_pp_multihead_nuscenes_seed3/seed_3/ckpt/latest_model.pth; /workspace/third_party/OpenPCDet/output/workspace/configs/cbgs_pp_multihead_nuscenes_seed4/seed_4/ckpt/latest_model.pth.
- Epoch stored in the checkpoints: seed 1 latest_model.pth: epoch=9 it=308860; seed 1 checkpoint_epoch_10.pth: epoch=10 it=308950; seed 2 latest_model.pth: epoch=9 it=308840; seed 2 checkpoint_epoch_10.pth: epoch=10 it=308950; seed 3 latest_model.pth: epoch=9 it=308899; seed 3 checkpoint_epoch_10.pth: epoch=10 it=308950; seed 4 latest_model.pth: epoch=9 it=308842; seed 4 checkpoint_epoch_10.pth: epoch=10 it=308950.

Reading: checkpoint_epoch_10 holds iteration 308950 = 10 epochs of 30895 iterations; the latest_model.pth files that inference loaded hold iterations 308840 to 308899, i.e. 9.9964 to 9.9983 epochs, 51 to 110 iterations before the end of epoch 10. Training was configured for 20 epochs and the logs end at the start of epoch 11, so the members were trained for (just under) 10 epochs, not 20.

Full listing: `epoch_check.txt`.

## 6. Frames per sequence N_s (sequences with N_s ≥ 1, all parts, split 0)

N_max(c) is the largest N_s over all validation sequences of c; for distance it depends on the boundary of each split.

| pair | condition | sequences | N_s_min | N_s_median | N_s_max | N_max over splits, min | N_max over splits, max |
|---|---|---|---|---|---|---|---|
| KITTI distance | near | 44 | 1 | 8.0 | 380 | 284 | 380 |
| KITTI distance | far | 26 | 1 | 80.0 | 557 | 557 | 569 |
| nuScenes distance | near | 149 | 3 | 37.0 | 41 | 41 | 41 |
| nuScenes distance | far | 150 | 4 | 38.0 | 41 | 41 | 41 |
| nuScenes weather | clear | 111 | 12 | 40.0 | 41 | 41 | 41 |
| nuScenes weather | rain | 24 | 19 | 40.0 | 41 | 41 | 41 |
| change of dataset and detector | KITTI | 45 | 1 | 9.0 | 571 | 571 | 571 |
| change of dataset and detector | nuScenes | 150 | 12 | 40.0 | 41 | 41 | 41 |


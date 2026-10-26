# Results with whole recorded sequences divided into parts

In these runs whole recorded sequences (nuScenes scenes, KITTI drives) are assigned to the grid, selection and test
parts, so that no sequence contributes frames to two parts. Each run reports two evaluations on this division:

- the **third run**: frames are counted as units, as in the frame-level evaluation (`hb_unit` = `frame`; in the
  nuScenes table `variant` = `scene_frame_unit`);
- the **sequence-level evaluation**: sequences are counted as units, each with the mean per-frame share of its frames
  (`hb_unit` = `scene` or `drive`; `variant` = `scene_scene_unit`). Only this evaluation meets the independence
  assumption of the test.

Before the division by sequence, each run repeats the frame-level evaluation and stops unless it reproduces the
recorded results of [`../division_by_frame/`](../division_by_frame/README.md) (`REPRO_PASSED.txt`).

| folder | question | run ID |
|---|---|---|
| [`nuscenes_by_scene/`](nuscenes_by_scene/README.md) | nuScenes distance and weather with whole scenes in the parts | m7 |
| [`kitti_by_drive/`](kitti_by_drive/README.md) | KITTI distance and the change of dataset and detector with whole drives in the parts | m8 |

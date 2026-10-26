# Results with the frames divided at random

In these runs the frames of each condition are assigned at random to the grid part (candidate thresholds), the
selection part and the test part, on five splits (random seeds 0 to 4). Each frame counts as one independent unit
(**frame-level evaluation**). Frames of one recorded sequence are not independent, so the stated error probability is
not guaranteed for these outcomes; [`../division_by_sequence/`](../division_by_sequence/README.md) repeats the
evaluation with whole sequences.

| folder | question | run ID |
|---|---|---|
| [`kitti_distance_pilot/`](kitti_distance_pilot/README.md) | KITTI near and far distance, pilot with the blended score of the detection pipeline | m1 |
| [`kitti_distance/`](kitti_distance/README.md) | KITTI near and far distance with the indicators u_s and u_e | m2 |
| [`nuscenes_distance/`](nuscenes_distance/README.md) | nuScenes near and far distance with u_s and u_e (Fig. 4) | m3 |
| [`dataset_change_one_split/`](dataset_change_one_split/README.md) | KITTI with its detector against nuScenes with its detector, split 0 | m4 |
| [`kitti_rule_dataset_change_weather/`](kitti_rule_dataset_change_weather/README.md) | KITTI distance with and without the KITTI rule, the change of dataset and detector on five splits, nuScenes clear weather and rain (Fig. 4) | m6 |

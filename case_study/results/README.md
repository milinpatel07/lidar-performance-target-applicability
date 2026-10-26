# Recorded results

The recorded results of the KITTI and nuScenes case study, grouped by how the frames of each condition were divided into
the grid, selection and test parts. Each run folder holds the files the run wrote, a `provenance.json` (script version
and SHA-256, SHA-256 of every input, configuration) and a README that says what the folder answers and what each file
holds. [`../docs/results.md`](../docs/results.md) explains every column; [`INPUT_HASHES.md`](INPUT_HASHES.md) lists the
input files of every run. The files keep the labels they were written with (run IDs m1 to m8, file names such as
`A_kitti_range_protocol.csv`); [`../../docs/glossary.md`](../../docs/glossary.md) maps them to the terms of the paper.

| folder | what it holds | run ID | path up to version 1.2.0 |
|---|---|---|---|
| [`division_by_frame/`](division_by_frame/README.md) | frames assigned to the parts at random; frame-level evaluation | | |
| [`kitti_distance_pilot/`](division_by_frame/kitti_distance_pilot/README.md) | KITTI near and far distance, pilot with the blended score | m1 | `results/m1_range_kitti` |
| [`kitti_distance/`](division_by_frame/kitti_distance/README.md) | KITTI near and far distance with u_s and u_e | m2 | `results/m2_indicators_kitti` |
| [`nuscenes_distance/`](division_by_frame/nuscenes_distance/README.md) | nuScenes near and far distance, five splits (Fig. 4) | m3 | `results/m3_range_nuscenes` |
| [`dataset_change_one_split/`](division_by_frame/dataset_change_one_split/README.md) | change of dataset and detector, split 0 | m4 | `results/m4_dataset_shift` |
| [`kitti_rule_dataset_change_weather/`](division_by_frame/kitti_rule_dataset_change_weather/README.md) | KITTI distance with and without the KITTI rule, change of dataset and detector, nuScenes weather, five splits (Fig. 4) | m6 | `results/m6_protocol_seeds_weather` |
| [`division_by_sequence/`](division_by_sequence/README.md) | whole recorded sequences assigned to the parts; third run and sequence-level evaluation | | |
| [`nuscenes_by_scene/`](division_by_sequence/nuscenes_by_scene/README.md) | nuScenes distance and weather with whole scenes in the parts | m7 | `results/m7_scene_split` |
| [`kitti_by_drive/`](division_by_sequence/kitti_by_drive/README.md) | KITTI distance and change of dataset and detector with whole drives in the parts | m8 | `results/m8_kitti_drive_split` |
| [`supporting_analyses/`](supporting_analyses/README.md) | retention, changes in the detections, intervals, common threshold, recall, annotation checks, figure data; computed by `tools/supporting/` and `tools/figures/` from the per-detection tables (files: [`../docs/results.md`](../docs/results.md#supporting-analyses)) | | `results/supporting_analyses` |
| [`post_hoc/`](post_hoc/README.md) | analyses added after the outcomes were known, not in the paper, with the scripts that produced them | | `results/post_hoc` |
| [`earlier_summaries/`](earlier_summaries/README.md) | outcome counts of the first runs, superseded | | `results/outcome_counts.csv`, `results/failing_cells_primary.csv` |

[`../checks/check_recorded_results.py`](../checks/check_recorded_results.py) checks every result file of version 1.0.0
at its current path. The files themselves keep the folder names of the time they were written (for example in
`provenance.json` or in `REPRO_PASSED.txt`).

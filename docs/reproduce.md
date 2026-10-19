# Reproducing the results

## Environment

The recorded runs used Python 3.10.13, NumPy 1.26.3, pandas 2.2.3 and Matplotlib 3.10.0 (`provenance.json` of each
run records the Python and NumPy versions). The rotated box overlap uses the polygon clipping backend of m1
(`--bev auto` selects it when Shapely is not installed, as in the recorded runs). The [`Dockerfile`](../Dockerfile)
builds this environment:

```bash
docker build -t pt-applicability .
```

All commands below run inside the container with the repository mounted at `/repo`, the inputs at `/rum` and the
nuScenes metadata at `/nuscenes` (see [`data.md`](data.md)):

```bash
docker run --rm -it -v "$PWD:/repo" -v /path/to/inputs:/rum:ro -v /path/to/nuscenes:/nuscenes:ro \
    -w /repo pt-applicability bash
```

## 1. Self-tests (no data needed)

```bash
cd analysis && python3 m1_range_kitti.py --selftest && python3 m3_range_nuscenes.py --selftest && cd ..
```

## 2. Experiment runs

Every run first rebuilds the merged detections and compares the per-frame missed and false detections with the
detection pipeline; it stops if one frame differs. It then writes its result files and a `provenance.json` with the
script version, the SHA-256 of every input and the configuration. Run the scripts from `analysis/`, because they load
each other by file name. A run on the nuScenes table takes about 20 minutes on 4 CPU cores.

```bash
cd analysis
python3 m1_range_kitti.py      --rum /rum --out ../work/m1
python3 m2_indicators_kitti.py --rum /rum --out ../work/m2
python3 m3_range_nuscenes.py   --rum /rum --out ../work/m3
python3 m4_dataset_shift.py    --rum /rum --out ../work/m4
python3 m6_protocol_seeds_weather.py --rum /rum --out ../work/m6 --nusc-meta /nuscenes/v1.0-trainval
```

Split by recorded nuScenes scene (m7): the frame split must first reproduce the recorded results.

```bash
python3 m3_range_nuscenes.py --rum /rum --out ../work/m7/m3_frame --split frame
python3 m6_protocol_seeds_weather.py --rum /rum --out ../work/m7/m6_frame --nusc-meta /nuscenes/v1.0-trainval --split frame
python3 m7_scene_split_report.py gate --run ../work/m7          # stops unless every row and input hash is equal
python3 m3_range_nuscenes.py --rum /rum --out ../work/m7/m3_scene --split scene --nusc-meta /nuscenes/v1.0-trainval
python3 m6_protocol_seeds_weather.py --rum /rum --out ../work/m7/m6_scene --nusc-meta /nuscenes/v1.0-trainval --split scene
python3 m7_scene_split_report.py collect --run ../work/m7
```

Split by recorded KITTI drive (m8). The devkit folder holds `mapping/train_rand.txt` and `mapping/train_mapping.txt`
from `devkit_object.zip` of the KITTI object benchmark. The script reruns the frame split first and stops unless it
equals the recorded m6 results byte for byte with equal input hashes.

```bash
python3 m8_kitti_drive_split.py --rum /rum --out ../work/m8 --devkit /path/to/kitti_devkit \
    --nusc-meta /nuscenes/v1.0-trainval --recorded ../results/m6_protocol_seeds_weather
cd ..
```

## 3. Tools: export, supporting analyses, figures

The tools build one cache of the per-detection tables and read it afterwards (`work/` is not versioned).

```bash
python3 tools/export_tables.py build --rum /rum --nusc-meta /nuscenes/v1.0-trainval   # about 20 minutes
python3 tools/export_tables.py export --kitti-cut m6rule      # work/data: split-0 exports and thresholds
python3 tools/check_export.py                                # AUROC, A and R recomputed independently
python3 tools/table_and_figure_values.py                     # frame counts and split-0 values
python3 tools/outcome_counts.py                              # outcome counts over all cells
python3 tools/supporting/retention_and_causes.py
python3 tools/supporting/common_threshold_and_recall.py
python3 tools/supporting/annotation_checks.py
python3 tools/supporting/frame_candidates.py                 # needs the three before it
python3 tools/figures/frame_figure.py
cd work/data && python3 ../../tools/figures/make_figures.py causes --csv kitti_distance_split0.csv \
    --tau tau_kitti_distance_split0.json --indicator u_s --out ../figures/fig_causes_kitti.pdf
```

Each supporting script first recomputes the split-0 cells of every setting from the cache and compares them with
`results/`; it stops on any difference.

## 4. Comparing a rerun with the recorded results

A rerun reproduces a recorded run if its result files equal those in `results/` and its input hashes equal
[`results/INPUT_HASHES.md`](../results/INPUT_HASHES.md):

```bash
diff work/m3/matrix_all_variants.csv results/m3_range_nuscenes/matrix_all_variants.csv
diff -r work/supporting_analyses results/supporting_analyses
```

[`analysis/SCRIPT_VERSIONS.md`](../analysis/SCRIPT_VERSIONS.md) names the script file behind each recorded run.

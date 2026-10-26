# Reproducing the results

This page gives the commands to check and rerun the KITTI and nuScenes case study. There are three levels, from the
cheapest to the most complete ([`pipeline.md`](pipeline.md) shows which script reads and writes what): (1) the checks,
which need only this repository (sections 0, 1 and 6); (2) tables and figures from the recorded results, which need only
this repository and pdflatex (section 5); (3) the experiment runs, which need the datasets and the detector outputs
([`data.md`](data.md); sections 2 to 4 and 7).

Run every command from the folder `case_study/` (`cd case_study` after cloning); paths on this page are relative to it.

## 0. Checks without data

```bash
pip install -r environment/requirements.txt
(cd .. && sha256sum -c MANIFEST.sha256)                   # every file of the repository against the manifest
python3 checks/check_recorded_results.py                   # every recorded file of version 1.0.0 unchanged at its path
python3 checks/check_paper_numbers.py --check-fresh        # numbers of the paper against results/; docs/paper_map.md fresh
python3 tools/supplementary/make_supplementary.py --check # numbers of the supplementary against results/
python3 tools/build_explorer_data.py --check              # data of the results browser against results/
python3 tools/build_interactive_data.py --check           # data of the interactive pages against results/
python3 ../tests/test_stats_js.py                         # page statistics against the Python implementation (needs node)
python3 ../tests/test_own_data_js.py                      # own-data page against the Python implementation (needs node)
node --test ../tests/test_explorer.mjs                    # functions of the results browser
PYTHONPATH=../package/src python3 -m pytest ../package/tests    # the package against experiments/m1_range_kitti.py
python3 ../tests/check_links.py                           # every relative link and every link into the pages
```

These checks and the self-tests of section 1 run in GitHub Actions on every push
([`../../.github/workflows/checks.yml`](../../.github/workflows/checks.yml)).

## Environment

The recorded runs used a container based on the NVIDIA CUDA 12.1.1 image (no GPU used) with Python 3.10.13, NumPy 1.26.3,
pandas 2.2.3 and Matplotlib 3.10.0 (`provenance.json` of each run records the Python and NumPy versions). The rotated box overlap uses the polygon clipping backend of m1
(`--bev auto` selects it when Shapely is not installed, as in the recorded runs). The [`../environment/Dockerfile`](../environment/Dockerfile)
builds this environment:

```bash
(cd .. && docker build -f case_study/environment/Dockerfile -t pt-applicability .)   # context: the repository root
```

All commands below run inside the container, in `/opt/repo/case_study`, with the repository mounted at `/opt/repo`, the inputs at `/data/inputs` and
the nuScenes metadata at `/data/nuscenes` (see [`data.md`](data.md)). `INPUTS` and `NUSCENES` are the folders on your
machine:

```bash
docker run --rm -it -v "$(dirname "$PWD"):/opt/repo" -v "$INPUTS:/data/inputs:ro" -v "$NUSCENES:/data/nuscenes:ro" \
    -w /opt/repo/case_study pt-applicability bash
```

## 1. Self-tests (no data needed)

```bash
cd experiments && python3 m1_range_kitti.py --selftest && python3 m3_range_nuscenes.py --selftest && cd ..
```

## 2. Experiment runs

Every run first rebuilds the merged detections and compares the per-frame missed and false detections with the
detection pipeline; it stops if one frame differs. It then writes its result files and a `provenance.json` with the
script version, the SHA-256 of every input and the configuration. Run the scripts from `experiments/`, because they load
each other by file name. A run on the nuScenes table takes about 20 minutes on 4 CPU cores.

```bash
cd experiments
python3 m1_range_kitti.py      --rum /data/inputs --out ../work/m1
python3 m2_indicators_kitti.py --rum /data/inputs --out ../work/m2
python3 m3_range_nuscenes.py   --rum /data/inputs --out ../work/m3
python3 m4_dataset_shift.py    --rum /data/inputs --out ../work/m4
python3 m6_protocol_seeds_weather.py --rum /data/inputs --out ../work/m6 --nusc-meta /data/nuscenes/v1.0-trainval
```

Third run and sequence-level evaluation on nuScenes scenes (m7; terms in [`concept.md`, section 5](../../docs/concept.md#5-the-independent-unit-frame-or-recorded-sequence)). The frame-level evaluation must first reproduce the recorded results.

```bash
python3 m3_range_nuscenes.py --rum /data/inputs --out ../work/m7/m3_frame --split frame
python3 m6_protocol_seeds_weather.py --rum /data/inputs --out ../work/m7/m6_frame --nusc-meta /data/nuscenes/v1.0-trainval --split frame
python3 m7_scene_split_report.py gate --run ../work/m7          # stops unless every row and input hash is equal
python3 m3_range_nuscenes.py --rum /data/inputs --out ../work/m7/m3_scene --split scene --nusc-meta /data/nuscenes/v1.0-trainval
python3 m6_protocol_seeds_weather.py --rum /data/inputs --out ../work/m7/m6_scene --nusc-meta /data/nuscenes/v1.0-trainval --split scene
python3 m7_scene_split_report.py collect --run ../work/m7
```

Third run and sequence-level evaluation on KITTI drives (m8). The devkit folder holds `mapping/train_rand.txt` and
`mapping/train_mapping.txt` from `devkit_object.zip` of the KITTI object benchmark. The script reruns the frame-level
evaluation first and stops unless it equals the recorded m6 results byte for byte with equal input hashes.

```bash
python3 m8_kitti_drive_split.py --rum /data/inputs --out ../work/m8 --devkit /data/kitti_devkit \
    --nusc-meta /data/nuscenes/v1.0-trainval --recorded ../results/division_by_frame/kitti_rule_dataset_change_weather
cd ..
```

## 3. Tools: export, supporting analyses, figures

The tools build one cache of the per-detection tables and read it afterwards (`work/` is not versioned).

```bash
python3 tools/export_tables.py build --rum /data/inputs --nusc-meta /data/nuscenes/v1.0-trainval   # about 20 minutes
python3 tools/export_tables.py export --kitti-cut m6rule      # work/data: split-0 exports and thresholds
python3 checks/check_export.py                                # AUROC, A and R recomputed independently
python3 tools/table_and_figure_values.py                     # frame counts and split-0 values
python3 tools/outcome_counts.py                              # outcome counts over all cells
python3 tools/supporting/retention_and_causes.py
python3 tools/supporting/common_threshold_and_recall.py
python3 tools/supporting/annotation_checks.py
python3 tools/supporting/frame_candidates.py                 # needs the three before it
python3 tools/figures/frame_figure.py
cd work/data && python3 ../../tools/figures/make_figures.py causes --csv kitti_distance_split0.csv \
    --tau tau_kitti_distance_split0.json --indicator u_s --out ../figures/fig_causes_kitti.pdf && cd ../..
```

Each supporting script first recomputes the split-0 cells of every pair of conditions from the cache and compares them with
`results/`; it stops on any difference.

## 4. Comparing a rerun with the recorded results

A rerun reproduces a recorded run if its result files equal those in `results/` and its input hashes equal
[`../results/INPUT_HASHES.md`](../results/INPUT_HASHES.md):

```bash
diff work/m3/matrix_all_variants.csv results/division_by_frame/nuscenes_distance/matrix_all_variants.csv
diff -r work/supporting_analyses results/supporting_analyses
```

[`../experiments/SCRIPT_VERSIONS.md`](../experiments/SCRIPT_VERSIONS.md) names the script file behind each recorded run. Files
written by a rerun differ from the recorded ones in their time stamps (`provenance.json` fields `started`, `finished`)
and, for the `*_log.txt` files, in run times; compare the CSV and JSON result files.

## 5. Figures and supplementary material from the recorded results (no data)

```bash
mkdir -p work/figures
python3 tools/figures/paper/make_fig_outcomes.py results/supporting_analyses/retention_applicable_cells.csv work/figures/fig_outcomes.tex
python3 tools/figures/paper/make_fig_separation.py results/supporting_analyses/fig_separation_curves.csv work/figures/fig_separation.pdf
python3 tools/figures/supplementary/supplementary_figures.py      # rewrites docs/supplementary/figures/
python3 tools/supplementary/make_supplementary.py && cd docs/supplementary && pdflatex supplementary.tex && pdflatex supplementary.tex
```

[`../tools/figures/paper/README.md`](../tools/figures/paper/README.md) describes every figure of the paper and its inputs;
the figure sources are those of 21 October 2026 and differ from the submitted figures in label wording. The TikZ
figures need pdflatex with TikZ, pgfplots and the newtx fonts.

## 6. Results browser and notebook (no data)

```bash
python3 tools/build_explorer_data.py          # ../site/explorer/data/outcomes.json
python3 -m http.server -d ../site 8000        # then open http://localhost:8000/explorer/
python3 -m nbconvert --to notebook --execute --inplace notebooks/explore_results.ipynb
```

## 7. Post-hoc analyses (data needed)

The post-hoc sequence test (Methods A and B) and the AUROC bootstrap intervals were added after the outcomes were
known and are not reported in the paper; the epoch check supports the number of epochs stated in paper Sect. 4.1. The scripts in [`../results/post_hoc/code/`](../results/post_hoc/code/) need the per-detection cache, the nuScenes
metadata and the KITTI devkit mapping files, and `pip install -r environment/requirements-posthoc.txt`. They are published as they
ran; [`../results/post_hoc/README.md`](../results/post_hoc/README.md) maps their path constants to this repository.
Before computing a new number, `seq_ratio.py` recomputes 1,600 recorded rows and stops if one differs.

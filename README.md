# Applicability of performance targets across triggering conditions in LiDAR object detection

Code and recorded results for the paper

> Milin Patel and Rolf Jung. *Uncertainty Evaluation to Support Safety of the Intended Functionality Analysis for
> Determining the Applicability of Performance Targets Across Triggering Conditions in ML-Based LiDAR Object
> Detection.* Under review.

Every number of the paper can be traced to a file in [`results/`](results/), and every file there can be
regenerated with the scripts in [`analysis/`](analysis/) and [`tools/`](tools/) from the detector outputs described in
[`docs/data.md`](docs/data.md).

## The question

ISO 21448 (safety of the intended functionality, SOTIF) asks that the residual risk of an automated driving function
be shown acceptable against an **acceptance criterion** at vehicle level. For a perception element this criterion is
broken down into a **performance target**: here, an upper limit α on the **false acceptance proportion** A, the share
of wrong detections among the detections the element accepts.

A LiDAR object detector built as an ensemble of four networks gives each detection an uncertainty value. A
**rejection threshold** τ on this value is selected, with a statistical confidence bound, so that A ≤ α holds in one
**triggering condition**, for example near distance or clear weather. The repository answers one question for each
pair of conditions: **does the performance target still hold when the same threshold is used in another condition**
(far distance, rain, another dataset)?

Each transferred threshold is evaluated on held-out frames of the receiving condition, and the two-sided
Hoeffding-Bentkus interval [L, U] of A at 95 % confidence decides one of three outcomes:

| outcome | rule | meaning |
|---|---|---|
| applicable | U ≤ α | the target holds in the receiving condition |
| not applicable | L > α | the target is exceeded in the receiving condition |
| not determined | L ≤ α < U | the recorded data do not suffice to decide |

[`docs/method.md`](docs/method.md) explains the test step by step.

## What the recorded results show

Target values 10⁻², 10⁻³ and 10⁻⁴ were fixed before the first run. The values 0.05† and 0.1† were added to show what
the data can decide; they are marked † and are not read as safety targets. KITTI results apply the KITTI rule
(wrong detections in DontCare regions or on vans are not counted).

1. **A threshold carries its guarantee only into the condition it was selected in.** At α = 10⁻², the threshold on the
   spatial indicator selected on nuScenes is not applicable on KITTI in all five random splits; in the opposite
   direction it is applicable but keeps at most 0.02 % of the correct nuScenes detections
   ([m6 B](results/m6_protocol_seeds_weather/B_shift_seeds_protocol.csv),
   [retention](results/supporting_analyses/retention_applicable_cells.csv)). With the KITTI parts drawn by recorded
   drive, the first outcome holds on all five splits as well ([m8](results/m8_kitti_drive_split/summary.txt)).
2. **For distance and rain, the stable exceedances appear at the exploratory target values.** Near to far distance is
   not applicable on all five splits at 0.1† for both indicators on both datasets. At 10⁻², a distance or rain transfer
   is not applicable on at most three of five splits (nuScenes, far to near, existence indicator). The full outcome
   table is in [`docs/results.md`](docs/results.md#outcomes-over-the-five-splits).
3. **Discrimination does not decide applicability.** On nuScenes the existence indicator separates correct from wrong
   detections as well in rain as in clear weather (AUROC 0.856 and 0.844, evaluation part of split 0), yet the
   clear-weather threshold at 0.1† is not applicable in rain on four of five splits: rain holds more wrong detections
   (42.5 % against 33.6 %) ([ROC points](results/supporting_analyses/roc_clear_rain_points.csv),
   [shares](results/supporting_analyses/wrong_share_and_median_split0.csv)).
4. **An applicable outcome is evidence only together with its retention.** A limit on false acceptance can be met by
   rejecting almost everything. At 10⁻², the applicable cells keep at most 46.6 % of the correct detections, and a
   transferred threshold at most 28.5 % ([applicable cells](results/supporting_analyses/applicable_cells_1e-2.csv)).
5. **What recorded data can confirm is set by the number of independent units.** A decision at 10⁻² needs at least
   299 independent selection units and 368 evaluation units without a false acceptance (n ≥ ln δ′ / ln(1 − α)).
   With the recorded scene (nuScenes, 150 scenes) or drive (KITTI, 45 drives) as the unit, no threshold can be
   selected at 10⁻², 10⁻³ or 10⁻⁴, and no outcome is "not applicable" at any target value
   ([m7](results/m7_scene_split/m7_scene_split_summary.txt), [m8](results/m8_kitti_drive_split/summary.txt)).

## Repository layout

```
analysis/        experiment scripts m1 to m8 and the statistics helpers; they load each other by file name
  recorded_versions/   earlier script versions that produced the first runs (hash-checked)
  SCRIPT_VERSIONS.md   which script file produced which recorded run
tools/           table export, supporting analyses and figures, built on analysis/
results/         recorded results of every run, each with provenance.json (script version, input SHA-256)
configs/         configuration of each run, as recorded in its provenance
docs/            method, data, reproduction, guide to the results, frozen predictions
MANIFEST.sha256  SHA-256 of every file
```

| run | what it computes | results |
|---|---|---|
| m1 | KITTI, near and far distance, with the blended score of the detection pipeline (precursor of m2) | [`results/m1_range_kitti`](results/m1_range_kitti/) |
| m2 | KITTI distance with the spatial indicator u_s and the existence indicator u_e | [`results/m2_indicators_kitti`](results/m2_indicators_kitti/) |
| m3 | nuScenes distance with u_s and u_e | [`results/m3_range_nuscenes`](results/m3_range_nuscenes/) |
| m4 | change of dataset (KITTI and nuScenes), one split | [`results/m4_dataset_shift`](results/m4_dataset_shift/) |
| m6 | KITTI distance with the KITTI rule; change of dataset over five splits; nuScenes rain against clear weather | [`results/m6_protocol_seeds_weather`](results/m6_protocol_seeds_weather/) |
| m7 | nuScenes distance and rain with the parts drawn by recorded scene | [`results/m7_scene_split`](results/m7_scene_split/) |
| m8 | KITTI distance and change of dataset with the KITTI parts drawn by recorded drive | [`results/m8_kitti_drive_split`](results/m8_kitti_drive_split/) |
| supporting | retention per applicable cell, causes, common threshold, recall, annotation checks | [`results/supporting_analyses`](results/supporting_analyses/) |

## Quick start

The self-tests need no data. m1 checks the Hoeffding-Bentkus bound against its closed form and the error rate of the
threshold selection on synthetic frames; m3 checks the indicator definitions on constructed boxes:

```bash
pip install -r requirements.txt
cd analysis
python3 m1_range_kitti.py --selftest
python3 m3_range_nuscenes.py --selftest
```

or in a container:

```bash
docker build -t pt-applicability .
docker run --rm -v "$PWD:/repo" -w /repo/analysis pt-applicability python3 m1_range_kitti.py --selftest
```

To inspect results, open the CSV files in [`results/`](results/); [`docs/results.md`](docs/results.md) explains every
column. To rerun an experiment from the detector outputs, follow [`docs/reproduce.md`](docs/reproduce.md).

## Data

No KITTI or nuScenes data is included: no point clouds, images, annotations, detector outputs or per-detection
exports. The scripts read the datasets under their own licences and the outputs of the detector ensembles; see
[`docs/data.md`](docs/data.md). [`results/INPUT_HASHES.md`](results/INPUT_HASHES.md) gives the SHA-256 of every input
file, so a rerun can show that it used the same inputs.

## Citation

See [`CITATION.cff`](CITATION.cff). The entry will be completed with the venue once the paper is accepted.

## Licence

Code (`analysis/`, `tools/`): MIT, see [`LICENSE`](LICENSE). Results and documentation (`results/`, `configs/`,
`docs/`): CC BY 4.0, see [`LICENSE-results`](LICENSE-results).

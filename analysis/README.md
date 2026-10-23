# Experiment scripts

The scripts load each other by file name (m3 loads m1; m4 loads m1, m2 and m3; m6 loads m4; m8 loads m6), so
they stay in this folder and are run from it. Each script states its inputs, outputs and options in its header. What
they compute: [`../docs/method.md`](../docs/method.md); the idea of the test: [`../docs/concept.md`](../docs/concept.md).

| script | run | what it does |
|---|---|---|
| `m1_range_kitti.py` | m1 | statistics core: per-frame share and FAP of paper Eq. 2 (`Cell`), Hoeffding-Bentkus p-value and bounds (`hb_pvalue`, `hb_upper`, `hb_lower`), fixed-sequence selection (`chain_index`), zero-failure bound of paper Eq. 5 (`n_required`), division into parts (`split_frames`), `analyse()` for two conditions; KITTI distance with the blended score; `--selftest` |
| `m2_indicators_kitti.py` | m2 | rebuilds the merged KITTI detections from the four networks, computes u_s and u_e, KITTI distance |
| `m3_range_nuscenes.py` | m3 | the same for nuScenes; `--split scene` divides by recorded scene and gives the third run (frame as unit) and the sequence-level evaluation (scene as unit); `--selftest` |
| `m4_dataset_shift.py` | m4 | change of dataset and detector, halves for selection and test |
| `m6_protocol_seeds_weather.py` | m6 | KITTI rule, change of dataset and detector on five splits, nuScenes weather; `--split scene` for weather |
| `m7_scene_split_report.py` | m7 | reproduction gate of the frame-level evaluation and the side-by-side table of the three evaluations on nuScenes scenes |
| `m8_kitti_drive_split.py` | m8 | third run and sequence-level evaluation on KITTI drives (devkit mapping), with a reproduction gate |

A variant replaces `m1.split_frames` or `m1.Cell` at run time; the statistics in m1 are never edited.
[`SCRIPT_VERSIONS.md`](SCRIPT_VERSIONS.md) names the file behind each recorded run; earlier versions are in
[`recorded_versions/`](recorded_versions/).

**Headers written during the study.** The scripts are published byte for byte as they ran, so that their SHA-256 values
match the provenance of the runs (`m8_kitti_drive_split.py` differs from its run version only in its docstring). Their
header texts therefore keep the wording and numbering of the time they were written:

| in the scripts | in the submitted paper |
|---|---|
| "Eq. 1" for a_f and the false acceptance proportion (`m3_range_nuscenes.py`, `m7_scene_split_report.py`) | Eq. 2 (per-frame share a_f and FAP) |
| "VEHITS Eq. 3" for u_s | the conference paper's equation, adapted as Eq. 1 |
| "VEHITS Eq. 1" for u_e | defined in the text of Sect. 3.1 (no equation number); the scripts note that a missing member counts with confidence 0 |
| "VEHITS Eq. 2" for the confidence variance u_v | not used in the paper |
| "variant (i)", `scene_frame_unit` | third run (division by recorded sequence, frame as unit) |
| "variant (ii)", `scene_scene_unit`, `hb_unit` = `scene` / `drive` | sequence-level evaluation (division by recorded sequence, sequence as unit) |
| "frame split", `split` = `frame` | frame-level evaluation |
| "established", "applied" | condition of selection, condition of use |
| "applies", "does not apply", "no threshold established" | applicable, not applicable, no threshold selected |
| "class" (for a condition) | condition |

Further header notes:

- `m1_range_kitti.py` calls itself "milestone 1" and says that its numbers are "not paper numbers": m1 used the blended
  score `u` of the detection pipeline (RUM), before the indicators u_s and u_e of m2; its statistics functions are used
  by every later run.
- `m3_range_nuscenes.py` repeats part of the docstring of m2 (including an output path of m2), and its self-test prints
  "M2 SELFTEST"; the code is the nuScenes version.
- `m6_protocol_seeds_weather.py` names version m6-0.1 in its first line; `SCRIPT_VERSION` in the code (m6-0.3) is the
  version. Its open note "[VERIFY against the devkit ...]" refers to the KITTI rule, which [`../docs/method.md`](../docs/method.md)
  states as implemented.

All terms: [`../docs/glossary.md`](../docs/glossary.md).

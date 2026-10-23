# Recorded results

One folder per run, as written by the run, with `provenance.json` (script version and SHA-256, SHA-256 of every input,
configuration) and `summary.txt` (consistency check against the detection pipeline and outcome counts).
[`../docs/results.md`](../docs/results.md) explains every folder and column and lists which files hold the values of each
section, table and figure of the paper; [`INPUT_HASHES.md`](INPUT_HASHES.md) lists the input files of every run. The
files keep the labels they were written with; [`../docs/glossary.md`](../docs/glossary.md) maps them to the terms of the
paper (for example m7 `variant` = `scene_frame_unit` is the third run and `scene_scene_unit` the sequence-level
evaluation).

[`post_hoc/`](post_hoc/README.md) holds analyses added after the parameters were fixed and the outcomes were known; they
are labelled as post hoc throughout.

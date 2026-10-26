#!/usr/bin/env python3
"""check_paper_numbers.py (paper-map-2.0, 2026-10-23) - the numbers of the submitted paper, recomputed from the files of
this repository.

Each entry names where the number appears in the paper, the value as printed there, the file(s) and filter it comes
from, and the script that wrote the file. Three kinds of entry:
  - result: the value is recomputed from a file in results/ (or configs/) and compared with the printed value at the
    printed precision (half a unit of the last printed digit) or with the stated tolerance;
  - equation: the value follows from an equation of the paper (Eq. 5) and is recomputed here;
  - provenance: the value describes the detector training and is not recorded in a result file; the entry points to
    docs/provenance.md and checks only that the printed value occurs there (not checked while that file is absent).
The paper itself is not part of the repository; the entries quote only the statement and the number.

Usage, from case_study/:
  python3 checks/check_paper_numbers.py                 # check; exit 1 on any difference
  python3 checks/check_paper_numbers.py --write         # check and write docs/paper_map.md
  python3 checks/check_paper_numbers.py --check-fresh   # check; exit 1 also if docs/paper_map.md differs from a fresh --write
"""
import argparse, ast, json, math, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
SA = R / "supporting_analyses"
PROV = ROOT / "docs/provenance.md"
MAP = ROOT / "docs/paper_map.md"
VERSION = "paper-map-2.0 (2026-10-23)"
DELTA = 0.05


def csv(rel):
    return pd.read_csv(R / rel)


def js(rel):
    return json.loads((R / rel).read_text(encoding="utf-8"))


def text(rel):
    return (R / rel).read_text(encoding="utf-8")


# ------------------------------------------------------------------ sources used by several entries
m6A = csv("division_by_frame/kitti_rule_dataset_change_weather/A_kitti_range_protocol.csv")
m6B = csv("division_by_frame/kitti_rule_dataset_change_weather/B_shift_seeds_protocol.csv")
m6C = csv("division_by_frame/kitti_rule_dataset_change_weather/C_weather_nuscenes.csv")
m3 = csv("division_by_frame/nuscenes_distance/matrix_all_variants.csv")
m3p = m3[(m3.iou == "A_iou0.5") & (m3.objects == "car") & (m3.cut_q == 0.5)]
m7 = csv("division_by_sequence/nuscenes_by_scene/m7_scene_split.csv")
m8A = csv("division_by_sequence/kitti_by_drive/A_kitti_distance_drive.csv")
m8B = csv("division_by_sequence/kitti_by_drive/B_dataset_drive.csv")
m8p = js("division_by_sequence/kitti_by_drive/provenance.json")
ws = pd.read_csv(SA / "wrong_share_and_median_split0.csv")
mr = pd.read_csv(SA / "merge_recall.csv")
fpc = pd.read_csv(SA / "frames_per_condition.csv")
ret = pd.read_csv(SA / "retention_applicable_cells.csv")
dpp = pd.read_csv(SA / "m8_drives_per_part.csv")
au = pd.read_csv(R / "post_hoc/auroc_bootstrap.csv")
sepc = pd.read_csv(SA / "fig_separation_curves.csv")
roc_cr = pd.read_csv(SA / "roc_clear_rain_points.csv")
tfv = json.loads((SA / "table_and_figure_values.json").read_text(encoding="utf-8"))
cfg = json.loads((ROOT / "configs/m1_range_kitti.json").read_text(encoding="utf-8"))
NAME = {"kitti": "KITTI", "nuscenes": "nuScenes"}


def b_cells(D):
    """m6 B / m8 B with the column names of the other tables."""
    return D.rename(columns={"source": "established", "target": "applied"}).replace({"established": NAME, "applied": NAME})


def frame_cells():
    """Transfer outcomes of the frame-level evaluation (Fig. 4 of the paper), KITTI rule; one row per cell and split."""
    parts = [m6A[m6A.protocol == "kitti_ignore"].assign(pair="KITTI distance"),
             m3p.assign(pair="nuScenes distance"),
             m6C.assign(pair="nuScenes weather"),
             b_cells(m6B[m6B.protocol == "kitti_ignore"]).assign(pair="change of dataset and detector")]
    d = pd.concat(parts, ignore_index=True)[["pair", "indicator", "seed", "alpha", "established", "applied", "outcome"]]
    return d[d.established != d.applied]


def unit_cells(hb_unit, m7_variant):
    """Transfer outcomes with division by recorded sequence: m8 (KITTI drives) and m7 (nuScenes scenes), KITTI rule."""
    parts = [m8A[(m8A.protocol == "kitti_ignore") & (m8A.hb_unit == hb_unit)].assign(pair="KITTI distance"),
             b_cells(m8B[(m8B.protocol == "kitti_ignore") & (m8B.hb_unit == hb_unit)]).assign(pair="change of dataset and detector"),
             m7[m7.variant == m7_variant].replace({"setting": {"distance": "nuScenes distance", "rain": "nuScenes weather"}})
             .rename(columns={"setting": "pair"})]
    d = pd.concat(parts, ignore_index=True)[["pair", "indicator", "seed", "alpha", "established", "applied", "outcome"]]
    return d[d.established != d.applied]


FC = frame_cells()
SEQ = unit_cells("drive", "scene_scene_unit")     # sequence-level evaluation
THIRD = unit_cells("frame", "scene_frame_unit")   # third run: division by recorded sequence, frame as unit
M7O = m7[m7.established == m7.applied]
EXPL = [0.01, 0.05, 0.1]
DEC = ["applies", "does not apply"]


def n_na(D, pair, ind, alpha, est, app):
    q = D[(D.pair == pair) & (D.indicator == ind) & (D.alpha == alpha) & (D.established == est) & (D.applied == app)]
    assert len(q) == 5, (pair, ind, alpha, est, app, len(q))
    return int((q.outcome == "does not apply").sum()), int((q.outcome == "applies").sum())


def wshare(setting, cond, ind="u_s", part="all", col="share_wrong"):
    q = ws[(ws.setting == setting) & (ws.condition == cond) & (ws.indicator == ind) & (ws.part == part)]
    assert len(q) == 1, (setting, cond, ind, part)
    return float(q[col].iloc[0])


def n_units(alpha, d):
    """Smallest n with n >= ln(d) / ln(1 - alpha) (Eq. 5)."""
    return math.ceil(math.log(d) / math.log(1 - alpha))


def lowest_limit(n, d):
    """Lowest limit that n units without a false acceptance can show to be met (Eq. 5 solved for alpha)."""
    return 1 - d ** (1 / n)


def fig4_counts():
    """Counts hard-coded in tools/figures/paper/make_fig_outcomes.py, compared cell by cell with the result files."""
    src = (ROOT / "tools/figures/paper/make_fig_outcomes.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    rows = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "rows")
    pair_of = {"KITTI distance": "KITTI distance", "nuScenes distance": "nuScenes distance", "nuScenes rain": "nuScenes weather",
               "change of dataset": "change of dataset and detector"}
    bad, n = [], 0
    for _, spec in rows:
        if spec is None:
            continue
        setting, est, app, cus, cue = spec
        for ind, cs in (("u_s", cus), ("u_e", cue)):
            for alpha, c in zip(EXPL, cs):
                q = FC[(FC.pair == pair_of[setting]) & (FC.indicator == ind) & (FC.alpha == alpha) & (FC.established == est) & (FC.applied == app)]
                got = "/".join(str(int((q.outcome == o).sum())) for o in ("applies", "not determined", "does not apply"))
                n += 1
                if got != c:
                    bad.append(f"{setting} {est}->{app} {ind} {alpha}: figure {c}, files {got}")
    return n, bad


def kitti_rule_changes():
    """Transfer cells with one outcome on all five splits with the KITTI rule that change without it (m6 A and B)."""
    keep = {}
    for D, k0, k1, lab in ((m6A, "established", "applied", "KITTI distance"), (m6B, "source", "target", "change of dataset and detector")):
        D = D[D[k0] != D[k1]]
        for key, g in D.groupby(["indicator", "alpha", k0, k1]):
            o = {p: "".join({"applies": "A", "does not apply": "N", "not determined": "?", "no threshold established": "-"}[x]
                            for x in g[g.protocol == p].sort_values("seed").outcome) for p in ("kitti_ignore", "as_run")}
            if len(set(o["kitti_ignore"])) == 1 and o["as_run"] != o["kitti_ignore"]:
                keep[(lab,) + key] = o
    return keep


# ------------------------------------------------------------------ the entries
E = []


def add(where, what, printed, value, digits, source, script, note=None, tol=None, kind="result"):
    """digits: compare at the printed precision; tol: compare within this absolute tolerance; neither: compare as text."""
    E.append({"where": where, "what": what, "printed": printed, "value": value, "digits": digits, "source": source,
              "script": script, "note": note, "tol": tol, "kind": kind})


def prov(where, what, printed, find):
    """A number about the detector training; source: docs/provenance.md (checked only that it occurs there)."""
    E.append({"where": where, "what": what, "printed": printed, "value": None, "digits": None, "source": "docs/provenance.md, text " + " or ".join(f"`{f}`" for f in find),
              "script": "-", "note": None, "tol": None, "kind": "provenance", "find": find})


S33 = "Sect. 3.3"
add(S33, "bound on the probability of not applicable in the condition of selection (delta + delta/2)", "7.5 %", 100 * (DELTA + DELTA / 2), 1,
    "Sect. 3.3 of the paper, delta = 0.05", "-", kind="equation")

SM = "division_by_frame/kitti_rule_dataset_change_weather"
SM_PY = "experiments/m6_protocol_seeds_weather.py"
SR = "tools/supporting/retention_and_causes.py"
S41 = "Sect. 4.1"
prov(S41, "OpenPCDet version", "0.6.0", ["0.6.0+233f849"])
prov(S41, "KITTI training frames", "3,712", ["3,712 frames"])
prov(S41, "KITTI epochs", "10", ["10 of 10"])
prov(S41, "nuScenes training scenes", "700", ["700 training scenes"])
prov(S41, "nuScenes configured epochs, of which about 10 were run", "about 10 of 20", ["10 of 20"])
prov(S41, "members per ensemble (M)", "4", ["four PointPillars members"])
prov(S41, "confidence cut-off of the member boxes", "0.1", ["score cut-off at inference | 0.1"])
ep = text("post_hoc/epoch_check.txt")
done = sorted({int(x) for x in re.findall(r"seed \d checkpoint_epoch_10\.pth: epoch=(\d+)", ep)})
add(S41, "epochs of the nuScenes members (configured 20)", "about 10",
    f"{done[0]} (checkpoint of epoch 10; inference used latest_model.pth just before its end)" if done else "not found", None,
    "results/post_hoc/epoch_check.txt", "results/post_hoc/code/check_epochs.sh")

S42 = "Sect. 4.2"
add(S42, "rain scenes in daylight (validation set)", "24", int(csv("post_hoc/ns_per_condition.csv").query("condition == 'rain' and split == 0").sequences.iloc[0]), 0,
    "results/post_hoc/ns_per_condition.csv, rain, split 0", "results/post_hoc/code/seq_ratio.py")
add(S42, "detections excluded by the KITTI rule", "2,454", js(f"{SM}/provenance.json")["A"]["ignored_total"], 0,
    f"results/{SM}/provenance.json `A.ignored_total`", f"{SM_PY}")

T3 = "Table 3"
add(T3, "KITTI validation frames", "3,769", sum(m8p["frames_per_drive"].values()), 0,
    "results/division_by_sequence/kitti_by_drive/provenance.json `frames_per_drive` (sum)", "experiments/m8_kitti_drive_split.py")
add(T3, "KITTI car detections with the KITTI rule", "27,175", wshare("change of dataset", "KITTI (KITTI rule)", col="detections"), 0,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, KITTI (KITTI rule), part all", SR)
for ds, n_gt, rec in (("KITTI", "14,385", "0.858"), ("nuScenes", "65,465", "0.398")):
    q = mr[mr.dataset == ds].iloc[0]
    add(T3, f"{ds}: annotated cars", n_gt, int(q.annotated_cars), 0, "results/supporting_analyses/merge_recall.csv `annotated_cars`", SR)
    add(T3, f"{ds}: share of annotated cars matched after the vote", rec, float(q.recall), 3, "results/supporting_analyses/merge_recall.csv `recall`", SR)
php = js("post_hoc/provenance.json")
wf = php["weather_frames"]
add(T3, "nuScenes validation frames", "6,019", sum(wf.values()), 0, "results/post_hoc/provenance.json `weather_frames` (sum)", "results/post_hoc/code/seq_ratio.py")
add(T3, "nuScenes validation scenes", "150", php["nuscenes_scenes"], 0, "results/post_hoc/provenance.json `nuscenes_scenes`", "results/post_hoc/code/seq_ratio.py")
add(T3, "nuScenes car detections", "40,036", wshare("change of dataset", "nuScenes", col="detections"), 0,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, nuScenes, part all", SR)
add(T3, "near/far boundary, KITTI with the KITTI rule, split 0 (m)", "34.8", tfv["a_distance"]["KITTI_rule"]["cut_m"], 1,
    "results/supporting_analyses/table_and_figure_values.json `a_distance.KITTI_rule.cut_m`", "tools/table_and_figure_values.py")
add(T3, "near/far boundary, nuScenes, split 0 (m)", "21.4", tfv["a_distance"]["nuScenes"]["cut_m"], 1,
    "results/supporting_analyses/table_and_figure_values.json `a_distance.nuScenes.cut_m`", "tools/table_and_figure_values.py")
add(T3, "nuScenes clear daylight frames", "4,449", wf["clear_day"], 0, "results/post_hoc/provenance.json `weather_frames.clear_day`", "results/post_hoc/code/seq_ratio.py")
add(T3, "nuScenes rain daylight frames", "968", wf["rain_day"], 0, "results/post_hoc/provenance.json `weather_frames.rain_day`", "results/post_hoc/code/seq_ratio.py")
add(T3, "nuScenes night frames excluded", "602", wf["night"] + wf["rain_night"], 0, "results/post_hoc/provenance.json `weather_frames.night + rain_night`", "results/post_hoc/code/seq_ratio.py")
FPC_LABEL = {"nuScenes rain": "nuScenes weather", "change of dataset": "change of dataset and detector"}
for setting, cond, sel, ev in (("KITTI distance (KITTI rule)", "near", "1,484", "1,500"), ("KITTI distance (KITTI rule)", "far", "1,514", "1,545"),
                               ("nuScenes distance", "near", "2,207", "2,209"), ("nuScenes distance", "far", "2,270", "2,276"),
                               ("nuScenes rain", "clear", "1,917", "1,900"), ("nuScenes rain", "rain", "392", "414"),
                               ("change of dataset", "KITTI (KITTI rule)", "1,844", "1,852"), ("change of dataset", "nuScenes", "2,849", "2,850")):
    q = fpc[(fpc.setting == setting) & (fpc.condition == cond) & (fpc.seed == 0)].iloc[0]
    add(T3, f"{FPC_LABEL.get(setting, setting)}, {cond}: frames in the selection / test part, split 0", f"{sel} / {ev}",
        f"{q.frames_select:,} / {q.frames_eval:,}", None, "results/supporting_analyses/frames_per_condition.csv, seed 0", SR)

S43 = "Sect. 4.3"
add(S43, "grid part / selection part / test part (share of the frames)", "10 % / 45 % / 45 %",
    f"{100 * cfg['frac_grid']:.0f} % / {100 * cfg['frac_select']:.0f} % / {100 * (1 - cfg['frac_grid'] - cfg['frac_select']):.0f} %", None,
    "configs/m1_range_kitti.json `frac_grid`, `frac_select`", "experiments/m1_range_kitti.py (provenance.json `config`)")
lv = cfg["grid_levels"]
add(S43, "levels of the candidate thresholds", "0.01, 0.02, ..., 1.00", f"{lv[0]:.2f}, {lv[1]:.2f}, ..., {lv[-1]:.2f}" if len(lv) == 100 else f"{len(lv)} levels",
    None, "configs/m1_range_kitti.json `grid_levels`", "experiments/m1_range_kitti.py (provenance.json `config`)")
add(S43, "random seeds of the division (splits)", "5", len(cfg["seeds"]), 0, "configs/m1_range_kitti.json `seeds`", "experiments/m1_range_kitti.py (provenance.json `config`)")
m3sp = js("division_by_sequence/nuscenes_by_scene/m3_scene/provenance.json")["scene_counts_primary"]
gse = sorted({f"{v['grid']['scenes']} / {v['select']['scenes']} / {v['eval']['scenes']}" for v in m3sp.values()})
add(S43, "nuScenes scenes in the grid / selection / test part (every split)", "15 / 68 / 67", "; ".join(gse), None,
    "results/division_by_sequence/nuscenes_by_scene/m3_scene/provenance.json `scene_counts_primary`", "experiments/m3_range_nuscenes.py (`--split scene`)")
m6sp = js("division_by_sequence/nuscenes_by_scene/m6_scene/provenance.json")["C"]["parts"]
rs = [v[p]["rain"]["scenes"] for v in m6sp.values() for p in ("select", "eval")]
add(S43, "rain scenes in each selection and test part (all splits)", "9 to 12", f"{min(rs)} to {max(rs)}", None,
    "results/division_by_sequence/nuscenes_by_scene/m6_scene/provenance.json `C.parts.*.{select,eval}.rain.scenes`", f"{SM_PY} (`--split scene`)")
add(S43, "KITTI validation drives", "45", m8p["kitti_drives"], 0, "results/division_by_sequence/kitti_by_drive/provenance.json `kitti_drives`", "experiments/m8_kitti_drive_split.py")
pd0 = m8p["parts_distance"]["seed0"]
add(S43, "KITTI drives in the grid / selection / test part, split 0", "4 / 20 / 21",
    f"{pd0['grid']['drives']} / {pd0['select']['drives']} / {pd0['eval']['drives']}", None,
    "results/division_by_sequence/kitti_by_drive/provenance.json `parts_distance.seed0`", "experiments/m8_kitti_drive_split.py")

S44 = "Sect. 4.4"
add(S44, "error probability delta", "0.05", cfg["delta"], 2, "configs/m1_range_kitti.json `delta`", "experiments/m1_range_kitti.py (provenance.json `config`)")
add(S44, "target limits", "1e-2, 1e-3, 1e-4", ", ".join(f"{a:.0e}".replace("e-0", "e-") for a in cfg["alphas_frozen"]), None,
    "configs/m1_range_kitti.json `alphas_frozen`", "experiments/m1_range_kitti.py (provenance.json `config`)")
add(S44, "exploratory limits", "0.05, 0.1", ", ".join(f"{a:g}" for a in cfg["alphas_exploratory"]), None,
    "configs/m1_range_kitti.json `alphas_exploratory`", "experiments/m1_range_kitti.py (provenance.json `config`)")

S51 = "Sect. 5.1 / Fig. 4"
F4 = "frame-level evaluation, KITTI rule; m6 A and B (`kitti_ignore`), m3 (`A_iou0.5`, `car`, cut 0.5), m6 C"
n4, bad4 = fig4_counts()
add(S51, f"outcome counts of all {n4} transfer cells of Fig. 4", "as drawn", "equal" if not bad4 else "; ".join(bad4[:3]), None,
    F4 + "; counts in tools/figures/paper/make_fig_outcomes.py", "tools/figures/paper/make_fig_outcomes.py")
dec = FC[FC.alpha.isin(EXPL)]
add(S51, "transfer outcomes of the frame-level evaluation that are applicable or not applicable", "168 of 240",
    f"{int(dec.outcome.isin(DEC).sum())} of {len(dec)}", None, F4, "-")
hi = FC[FC.alpha.isin([0.001, 0.0001])]
add("Fig. 4 caption", "transfer outcomes at 1e-3 and 1e-4 with a selected threshold", "0",
    int((hi.outcome != "no threshold established").sum()), 0, F4, "-")
add(S51, "nuScenes → KITTI, u_s: not applicable at 1e-2, 0.05, 0.1 (splits of 5)", "5, 5, 5",
    ", ".join(str(n_na(FC, "change of dataset and detector", "u_s", a, "nuScenes", "KITTI")[0]) for a in EXPL), None, F4, "-")
add(S51, "KITTI near → far, u_s / nuScenes far → near, u_e: not applicable at 1e-2 (splits of 5)", "1 / 3",
    f"{n_na(FC, 'KITTI distance', 'u_s', 0.01, 'near', 'far')[0]} / {n_na(FC, 'nuScenes distance', 'u_e', 0.01, 'far', 'near')[0]}", None, F4, "-")
w01 = FC[(FC.pair == "nuScenes weather") & (FC.alpha == 0.01)]
add(S51, "weather transfers with a not applicable outcome at 1e-2", "0", int((w01.outcome == "does not apply").sum()), 0, F4, "-")
into = [("KITTI distance", "near", "far"), ("nuScenes distance", "near", "far"), ("nuScenes weather", "clear", "rain")]
add(S51, "transfers into far distance and into rain: largest number of not applicable splits of the two indicators at 0.1 (at least 4)",
    "≥ 4, ≥ 4, ≥ 4", ", ".join(str(max(n_na(FC, p, i, 0.1, e, a)[0] for i in ("u_s", "u_e"))) for p, e, a in into), None, F4, "-",
    tol="min4")
add(S51, "opposite directions (far → near on both datasets, rain → clear): applicable splits at 0.1, both indicators", "5 on all",
    ", ".join(str(n_na(FC, p, i, 0.1, a, e)[1]) for p, e, a in into for i in ("u_s", "u_e")), None, F4, "-", tol="all5")
tr = ret[(ret.in_fig_outcomes == True) & (ret.alpha == 0.01)]
add(S51, "largest retention of a transferred threshold with an applicable outcome at 1e-2, any split", "29 %",
    100 * tr.R_hat.max(), 0, "results/supporting_analyses/retention_applicable_cells.csv, `in_fig_outcomes`, alpha 0.01", SR)
fr = ret[(ret.variant == "frame") & (ret.alpha == 0.01)]
own_med = {}
for (st, ind, est, app), _ in fr[fr.transfer == True].groupby(["setting", "indicator", "established", "applied"]):
    o = fr[(fr.setting == st) & (fr.indicator == ind) & (fr.established == app) & (fr.applied == app)].R_hat
    if len(o):
        own_med[(st, ind, app)] = float(o.median())
best = max(own_med, key=own_med.get)
add(S51, "largest median retention of the thresholds selected in the conditions of use of the transfers with an applicable outcome "
    f"at 1e-2 (open markers of Fig. 4; largest: {best[0]}, {best[1]}, {best[2]})", "33 %", 100 * own_med[best], 0,
    "results/supporting_analyses/retention_applicable_cells.csv, variant frame, alpha 0.01, established = applied = condition of use", SR)
taus = pd.concat([m3p[(m3p.indicator == "u_e") & (m3p.alpha == 0.01)].tau, m6C[(m6C.indicator == "u_e") & (m6C.alpha == 0.01)].tau,
                  m6B[(m6B.indicator == "u_e") & (m6B.alpha == 0.01) & (m6B.protocol == "kitti_ignore")].tau]).dropna()
add(S51, "largest threshold for u_e at 1e-2 (m6 A records no threshold, KITTI distance is not covered)", "< 0.25",
    f"{taus.max():.4f}" if taus.max() < 0.25 else f"{taus.max():.4f} (not below 0.25)", None, f"m3, m6 C, m6 B `tau`", "experiments/")
add(S51, "transfer cells with one outcome on all five splits with the KITTI rule that change when the excluded detections are included",
    "0 (\"changed no outcome that held on all five splits\")", str(len(kitti_rule_changes())), None,
    "results/division_by_frame/kitti_rule_dataset_change_weather/A_kitti_range_protocol.csv and B_shift_seeds_protocol.csv, protocol `kitti_ignore` against `as_run`",
    "experiments/m6_protocol_seeds_weather.py", note="note 2")
f4 = FC.groupby(["pair", "indicator", "alpha", "established", "applied"]).outcome.apply(lambda s: int((s == "does not apply").sum()))
t4 = THIRD.groupby(["pair", "indicator", "alpha", "established", "applied"]).outcome.apply(lambda s: int((s == "does not apply").sum()))
k4 = [k for k, v in f4.items() if v >= 4]
kept = sum(int(t4.get(k, 0) >= 4) for k in k4)
add(S51, "transfers with not applicable on at least 4 of 5 splits in the frame-level evaluation that have it again on at least 4 of 5 in the third run",
    "every", f"{kept} of {len(k4)}", None,
    "third run: results/division_by_sequence/kitti_by_drive/ A and B (`kitti_ignore`, `hb_unit` frame), results/division_by_sequence/nuscenes_by_scene/m7_scene_split.csv (variant scene_frame_unit)",
    "experiments/m8_kitti_drive_split.py, experiments/m7_scene_split_report.py", tol="every")
for var, printed, lab in (("frame", "0 of 112", "frame-level evaluation"), ("scene_frame_unit", "5 of 113", "third run")):
    q = M7O[(M7O.variant == var) & (M7O.outcome != "no threshold established")]
    add(S51, f"nuScenes distance and weather, thresholds used in their own condition: not applicable, {lab}", printed,
        f"{int((q.outcome == 'does not apply').sum())} of {len(q)}", None, f"results/division_by_sequence/nuscenes_by_scene/m7_scene_split.csv, variant {var}, own condition",
        "experiments/m7_scene_split_report.py")
sq = SEQ[SEQ.alpha.isin(EXPL)]
sdec = sq[sq.outcome.isin(DEC)]
add(S51, "sequence-level evaluation: transfer outcomes that are applicable or not applicable", "5 of 240",
    f"{len(sdec)} of {len(sq)}", None,
    "results/division_by_sequence/nuscenes_by_scene/m7_scene_split.csv (variant scene_scene_unit, 120) and results/division_by_sequence/kitti_by_drive/ A and B "
    "(`kitti_ignore`, `hb_unit` drive, 120); transfers at 1e-2, 0.05, 0.1", "experiments/m7_scene_split_report.py, experiments/m8_kitti_drive_split.py")
add(S51, "of these: on nuScenes, applicable, at 0.1", "5",
    int((sdec.pair.str.startswith("nuScenes") & (sdec.outcome == "applies") & (sdec.alpha == 0.1)).sum()), 0,
    "as above", "experiments/m7_scene_split_report.py")

S52 = "Sect. 5.2 / Table 4"
au_ = lambda pair, q: float(au[(au.pair == pair) & (au.quantity == q)].point.iloc[0])
for pair, q, printed in (("KITTI distance", "AUROC near", "0.915"), ("KITTI distance", "AUROC far", "0.845"),
                         ("nuScenes weather", "AUROC clear", "0.844"), ("nuScenes weather", "AUROC rain", "0.856"),
                         ("change of dataset and detector", "AUROC nuScenes", "0.749"), ("change of dataset and detector", "AUROC KITTI", "0.905")):
    add("Table 4 / Fig. 5 legend", f"{pair}: {q} (test part of split 0)", printed, au_(pair, q), 3, "results/post_hoc/auroc_bootstrap.csv `point`",
        "results/post_hoc/code/seq_ratio.py")
dbl = text("supporting_analyses/distance_bins_log.txt").split("==== causes nuScenes")[1]
au_log = {k: float(v) for k, v in re.findall(r"^AUROC (near|far): ([0-9.]+)$", dbl, re.M)}
m3s = text("division_by_frame/nuscenes_distance/summary.txt")
au3 = {k: float(v) for k, v in re.findall(r"^\s*AUROC (near|far): ([0-9.]+) \[", m3s, re.M)[:2]}   # first block: u_s
for cond, printed in (("near", "0.729"), ("far", "0.655")):
    agree = abs(au_log[cond] - au3[cond]) <= 0.0005 + 0.00005 + 1e-12
    add("Table 4", f"nuScenes distance: AUROC of u_s {cond} (test part of split 0)", printed, au_log[cond], 3,
        f"results/supporting_analyses/distance_bins_log.txt, block `causes nuScenes` (3 digits); "
        f"results/division_by_frame/nuscenes_distance/summary.txt prints {au3[cond]:.4f} (4 digits){'' if agree else ' (DISAGREES)'}",
        "log of the recorded figure run (make_figures v13.4); experiments/m3_range_nuscenes.py",
        note="note 1" if cond == "near" else None)
for setting, cond, printed, lab in (("KITTI distance (KITTI rule)", "near", "0.34", None), ("KITTI distance (KITTI rule)", "far", "0.76", None),
                                    ("nuScenes distance", "near", "0.19", None), ("nuScenes distance", "far", "0.51", None),
                                    ("nuScenes rain", "clear", "0.33", "nuScenes weather"), ("nuScenes rain", "rain", "0.42", "nuScenes weather"),
                                    ("change of dataset", "nuScenes", "0.35", "change of dataset and detector"),
                                    ("change of dataset", "KITTI (KITTI rule)", "0.55", "change of dataset and detector")):
    add("Table 4", f"share of wrong detections, {lab or setting}, {cond} (all validation frames)", printed, wshare(setting, cond), 2,
        "results/supporting_analyses/wrong_share_and_median_split0.csv, part all", SR)
c0 = m6C[(m6C.indicator == "u_e") & (m6C.seed == 0) & (m6C.alpha == 0.1) & (m6C.established == "clear")]
add("Table 4", "FAP in clear weather, u_e, threshold selected in clear weather at 0.1, split 0", "0.09", float(c0[c0.applied == "clear"].A_hat.iloc[0]), 2,
    f"results/{SM}/C_weather_nuscenes.csv", f"{SM_PY}")
add("Table 4", "FAP in rain, same threshold", "0.17", float(c0[c0.applied == "rain"].A_hat.iloc[0]), 2, f"results/{SM}/C_weather_nuscenes.csv", f"{SM_PY}")
tau_c = float(c0.tau.iloc[0])


def pooled(cond):
    q = roc_cr[(roc_cr.condition == cond) & (roc_cr.alpha == 0.1)].iloc[0]
    assert abs(q.tau_clear - tau_c) < 1e-9, "roc_clear_rain_points.csv: threshold differs from m6 C"
    fa = (q.detections - q.correct) * (1 - q.wrong_rejected)
    return fa / (fa + q.correct * (1 - q.correct_rejected))


for cond, printed in (("clear", "0.12"), ("rain", "0.17")):
    add("Table 4", f"pooled share in {cond}, same threshold (test part of split 0)", printed, pooled(cond), 2,
        "results/supporting_analyses/roc_clear_rain_points.csv, alpha 0.1: wrong accepted / (wrong accepted + correct accepted)", SR)
for cond, lab, printed in (("nuScenes", "nuScenes", "0.23"), ("KITTI (KITTI rule)", "KITTI", "0.12")):
    add("Table 4", f"median u_s of the correct detections, {lab}", printed, wshare("change of dataset", cond, col="median_correct"), 2,
        "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, part all", SR)
up = {("KITTI distance", "near", "far"): ("KITTI distance (KITTI rule)", "near", "far"),
      ("nuScenes distance", "near", "far"): ("nuScenes distance", "near", "far"),
      ("nuScenes distance", "far", "near"): ("nuScenes distance", "far", "near"),
      ("KITTI distance", "far", "near"): ("KITTI distance (KITTI rule)", "far", "near"),
      ("nuScenes weather", "clear", "rain"): ("nuScenes rain", "clear", "rain"),
      ("nuScenes weather", "rain", "clear"): ("nuScenes rain", "rain", "clear"),
      ("change of dataset and detector", "nuScenes", "KITTI"): ("change of dataset", "nuScenes", "KITTI (KITTI rule)"),
      ("change of dataset and detector", "KITTI", "nuScenes"): ("change of dataset", "KITTI (KITTI rule)", "nuScenes")}
na_tr = sorted({(p, e, a) for p, e, a in FC[FC.outcome == "does not apply"][["pair", "established", "applied"]].itertuples(index=False)})
down = [f"{p} {e} → {a}" for p, e, a in na_tr if wshare(up[(p, e, a)][0], up[(p, e, a)][2]) < wshare(up[(p, e, a)][0], up[(p, e, a)][1])]
add("Sect. 5.2", "transfers with a not applicable outcome into a condition with a smaller share of wrong detections", "1 (nuScenes far → near)",
    f"{len(down)} ({'; '.join(down)})", None, "Fig. 4 outcomes and results/supporting_analyses/wrong_share_and_median_split0.csv", "-",
    tol="one_far_near")
mv = max(abs(wshare("nuScenes rain", "rain", "u_e", col=c) - wshare("nuScenes rain", "clear", "u_e", col=c)) for c in ("median_correct", "median_wrong"))
add("Sect. 5.2", "largest change of the median u_e of correct or wrong detections from clear to rain", "at most 0.03",
    f"{mv:.3f}" if mv <= 0.03 else f"{mv:.3f} (above 0.03)", None,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, nuScenes rain, u_e, part all", SR)
op = sepc[(sepc.row == "ROC operating point") & (sepc.panel.str.startswith("dataset"))]
tmax = op.tau.max()
add("Sect. 5.2", "share of KITTI wrong detections accepted by the nuScenes threshold at 0.1 (test part, split 0); 'about': within 2.5 points",
    "about 25 %", 100 * (1 - float(op[(op.condition == "KITTI") & (op.tau == tmax)].y.iloc[0])), None,
    "results/supporting_analyses/fig_separation_curves.csv, ROC operating point, 1 - y", "tools/figures/paper/make_fig_separation.py", tol=2.5)
add("Sect. 5.2", "share of nuScenes wrong detections accepted by the same threshold", "8 %", 100 * (1 - float(op[(op.condition == "nuScenes") & (op.tau == tmax)].y.iloc[0])), 0,
    "results/supporting_analyses/fig_separation_curves.csv, ROC operating point, 1 - y", "tools/figures/paper/make_fig_separation.py")

S53 = "Sect. 5.3 / Fig. 6"
add(S53, "units without a false acceptance needed to select a threshold at 1e-2 (delta' = 0.05)", "299", n_units(0.01, DELTA), 0, "Eq. 5", "-", kind="equation")
add(S53, "units needed to test a threshold at 1e-2 (delta' = 0.025)", "368", n_units(0.01, DELTA / 2), 0, "Eq. 5", "-", kind="equation")
add(S53, "units needed to select a threshold at 1e-3", "2,995", n_units(0.001, DELTA), 0, "Eq. 5", "-", kind="equation")
mx = int(fpc.frames_select.max())
add(S53, "largest selection part of any condition (frames, any split); must be below 2,995", "< 2,995", f"{mx:,}", None,
    "results/supporting_analyses/frames_per_condition.csv `frames_select`", SR, tol="lt2995")
f0 = fpc[fpc.seed == 0]
ok_frames = bool(((f0.frames_select >= n_units(0.01, DELTA)) & (f0.frames_eval >= n_units(0.01, DELTA / 2))).all())
add(S53, "frame-level evaluation: every condition holds the Eq. 5 minimum at 1e-2 in both parts (split 0)", "every",
    "every" if ok_frames else "not every", None, "results/supporting_analyses/frames_per_condition.csv, seed 0", SR)
for cond, printed in (("rain", 5), ("clear", 3)):
    q = m6C[(m6C.indicator == "u_s") & (m6C.alpha == 0.01) & (m6C.established == cond) & (m6C.applied == cond)]
    add(S53, f"splits without a selected threshold for u_s at 1e-2 in {cond}", str(printed), int((q.outcome == "no threshold established").sum()), 0,
        f"results/{SM}/C_weather_nuscenes.csv", f"{SM_PY}")
add(S53, "nuScenes validation scenes, fewer than the 299 needed for the selection at 1e-2", "150 < 299",
    f"{m3sp['seed0']['grid']['scenes'] + m3sp['seed0']['select']['scenes'] + m3sp['seed0']['eval']['scenes']} < {n_units(0.01, DELTA)}", None,
    "results/division_by_sequence/nuscenes_by_scene/m3_scene/provenance.json `scene_counts_primary`; Eq. 5", "-")
sel_k = sorted({v["select"]["drives"] for v in m8p["parts_distance"].values()} |
               set(dpp[(dpp.part == "select") & (dpp.setting.str.startswith("change"))].drives.astype(int)))
add(S53, "KITTI selection part (drives); paper: too small for any limit used here (largest 0.1)", "20 to 22",
    f"{sel_k[0]} to {sel_k[-1]}; lowest limit {lowest_limit(sel_k[-1], DELTA):.3f} with {sel_k[-1]} drives (Eq. 5)", None,
    "results/division_by_sequence/kitti_by_drive/provenance.json `parts_distance` (distance) and results/supporting_analyses/m8_drives_per_part.csv (change of dataset)",
    "experiments/m8_kitti_drive_split.py", tol="kitti_drives")
lims = [0.0001, 0.001, 0.01, 0.05, 0.1]


def reached(sel, ev):
    return [a for a in lims if sel >= n_units(a, DELTA) and ev >= n_units(a, DELTA / 2)]


rch = {}
for s, v in m3sp.items():
    for c in ("near", "far"):
        rch.setdefault(c, set()).add(tuple(reached(v["select"][c], v["eval"][c])))
for s, v in m6sp.items():
    for c in ("clear", "rain"):
        rch.setdefault(c, set()).add(tuple(reached(v["select"][c]["scenes"], v["eval"][c]["scenes"])))
fmt_r = lambda t: ", ".join(f"{a:g}" for a in t) if t else "none"
add(S53, "nuScenes scenes: limits whose Eq. 5 minimum the selection and test parts reach (all splits)", "near, far, clear: 0.1; rain: none",
    "; ".join(f"{c}: {' | '.join(fmt_r(t) for t in sorted(rch[c]))}" for c in ("near", "far", "clear", "rain")), None,
    "results/division_by_sequence/nuscenes_by_scene/m3_scene/provenance.json `scene_counts_primary`, results/division_by_sequence/nuscenes_by_scene/m6_scene/provenance.json `C.parts`; Eq. 5", "-",
    tol="scene_limits")
add("Fig. 6", "lowest limit that the 21 KITTI test drives can show to be met (delta' = 0.025); above 0.1", "> 0.1",
    f"{lowest_limit(pd0['eval']['drives'], DELTA / 2):.3f}", None, "Eq. 5 with results/division_by_sequence/kitti_by_drive/provenance.json `parts_distance.seed0.eval.drives`", "-",
    tol="gt0.1")

S62 = "Sect. 6.2"
fcl = text("supporting_analyses/frame_candidates_log.txt").splitlines()
fcl = next(l for l in fcl if "unannotated boxes" in l)
add(S62, "accepted wrong KITTI detections inside the image with no annotation nearby", "1,536",
    int(re.search(r"below 0\.1\): (\d+)", fcl).group(1)), 0, "results/supporting_analyses/frame_candidates_log.txt, line `(1) unannotated boxes`",
    "tools/supporting/frame_candidates.py")
add(S62, "recorded rain scenes behind the rain AUROC", "24", int(au[(au.pair == "nuScenes weather") & (au.quantity == "AUROC rain")].sequences.iloc[0]), 0,
    "results/post_hoc/auroc_bootstrap.csv `sequences`", "results/post_hoc/code/seq_ratio.py")
add(S62, "expected erroneous outcomes among the 240 transfer outcomes if frames were independent (at most 240 x delta/2)", "6",
    len(dec) * DELTA / 2, 0, "Sect. 3.3 of the paper; 240 = transfer outcomes of Fig. 4", "-", kind="equation")


# ------------------------------------------------------------------ notes on the paper text (computed from the files)
def notes():
    keep = kitti_rule_changes()
    lst = "; ".join(f"{lab}, {NAME.get(a, a)} → {NAME.get(b, b)}, {i}, α = {al:g}: {o['kitti_ignore']} with the rule, {o['as_run']} without"
                    for (lab, i, al, a, b), o in sorted(keep.items()))
    n1 = ("**Note 1 (Table 4, AUROC 0.729).** `results/division_by_frame/nuscenes_distance/summary.txt` prints the AUROC of u_s at near distance with four digits "
          "(0.7295); rounding this printed value again to three digits would give 0.730. The same quantity printed with three digits in "
          "`results/supporting_analyses/distance_bins_log.txt` is 0.729. Both printed values hold only if the value lies in "
          "[0.72945, 0.7295), which rounds to 0.729, so the files support the printed 0.729.")
    n2 = (f"**Note 2 (Sect. 5.1, KITTI rule).** The paper states: \"Including the detections excluded by the KITTI rule changed no "
          f"outcome that held on all five splits.\" In `results/division_by_frame/kitti_rule_dataset_change_weather/` (protocol `kitti_ignore` with the rule, "
          f"`as_run` without), {len(keep)} transfer cells held one outcome on all five splits with the rule and change on at least one "
          f"split without it. Codes per split 0 to 4: A applicable, N not applicable, ? not determined. {lst}. "
          "The not applicable outcome of nuScenes → KITTI for u_s holds on all five splits at every limit with and without the rule.")
    return [n1, n2]


# ------------------------------------------------------------------ comparison and output
def ok(e):
    p, v, d, t = e["printed"], e["value"], e["digits"], e["tol"]
    if e["kind"] == "provenance":
        if not PROV.exists():
            return None
        body = PROV.read_text(encoding="utf-8")
        pat = lambda f: (r"(?<![\d.,])" if f[0].isdigit() else "") + re.escape(f) + (r"(?![\d,]|\.\d)" if f[-1].isdigit() else "")
        return any(re.search(pat(f), body) for f in e["find"])
    if isinstance(t, (int, float)) and not isinstance(t, bool):
        return abs(float(v) - float(re.sub(r"[^0-9.]", "", p))) <= t + 1e-12
    if t == "min4":
        return all(int(x) >= 4 for x in v.split(", "))
    if t == "all5":
        return all(int(x) == 5 for x in v.split(", "))
    if t == "every":
        a, b = v.split(" of ")
        return a == b and int(b) > 0
    if t == "one_far_near":
        return v == "1 (nuScenes distance far → near)"
    if t == "lt2995":
        return int(v.replace(",", "")) < 2995
    if t == "kitti_drives":
        return v.startswith("20 to 22;") and float(v.rsplit("limit ", 1)[1].split()[0]) > 0.1
    if t == "scene_limits":
        return v == "near: 0.1; far: 0.1; clear: 0.1; rain: none"
    if t == "gt0.1":
        return float(v) > 0.1
    if d is None:
        if p == "as drawn":
            return v == "equal"
        if p.startswith("<") or p.startswith("at most"):
            return "not" not in str(v) and "above" not in str(v)
        if p.startswith("about"):
            return str(v).startswith(re.sub(r"\D", "", p))
        if p == "150 < 299":
            return v == p
        return str(v) == p
    num = float(re.sub(r"[^0-9.]", "", p))
    return abs(float(v) - num) <= 0.5 * 10 ** -d + 1e-12


def fmt(e):
    v, d = e["value"], e["digits"]
    if e["kind"] == "provenance":
        return "-"
    if isinstance(v, str):
        return v
    if d == 0 and float(v) == int(v):
        return f"{int(v):,}"
    if d is not None:
        return f"{float(v):.{d + 2}f}"
    return f"{float(v):.3f}" if isinstance(v, float) else str(v)


def status(e):
    if e["kind"] == "provenance":
        return ("not checked (docs/provenance.md absent)" if e["ok"] is None else
                "occurs in docs/provenance.md" if e["ok"] else "**not found in docs/provenance.md**")
    if e["ok"]:
        return "equal" + (f", see {e['note']}" if e["note"] else "")
    return f"differs, see {e['note']}" if e["note"] else "**differs**"


def render():
    n_res = sum(e["kind"] == "result" for e in E)
    n_eq = sum(e["kind"] == "equation" for e in E)
    n_pr = sum(e["kind"] == "provenance" for e in E)
    L = ["# Paper map: numbers of the paper and their sources", "",
         f"Written by `checks/check_paper_numbers.py` ({VERSION}); do not edit by hand. Each row gives where a number appears in "
         "the submitted paper, the value printed there, the value recomputed from the repository, the file and filter, and the "
         "script that wrote the file. The check compares at the precision printed in the paper unless the row states a "
         "tolerance. CI runs the check on every push and fails if this page differs from a fresh `--write`. The paper is not "
         "part of the repository.", "",
         f"Of the {len(E)} rows, {n_res} are recomputed from files in `results/` or `configs/`, {n_eq} follow from an equation of the "
         f"paper (Eq. 5 or the error bound of Sect. 3.3), and {n_pr} describe the detector training, which no result file records; "
         f"these point to {'[`docs/provenance.md`](provenance.md)' if PROV.exists() else '`docs/provenance.md`'} and are checked only for the "
         "printed value occurring there. "
         "Numbers that describe the datasets (scene length, frame interval) or the method without a recorded value are not listed.", "",
         "Numbering follows the submitted paper: Eq. 2 FAP, Eq. 3 trivial bound, Eq. 4 mix of conditions, Eq. 5 minimum number of "
         "units; Table 3 pairs of conditions, Table 4 changes in the detections, Table 5 outcome and measure; Fig. 4 outcomes, "
         "Fig. 5 separation, Fig. 6 units.", "",
         "Figures of the paper: Fig. 1 (two frames, dataset images; facts in `results/supporting_analyses/fig1_two_panel_facts.txt`, "
         "scripts in `tools/figures/paper/frame_figure/`), Fig. 2 and Fig. 3 (schematics, `tools/figures/paper/fig_concept.tex`, "
         "`fig_parts.tex`), Fig. 4 (`make_fig_outcomes.py`), Fig. 5 (`make_fig_separation.py` from "
         "`results/supporting_analyses/fig_separation_curves.csv`), Fig. 6 (`fig_units.tex`). See "
         "[`tools/figures/paper/README.md`](../tools/figures/paper/README.md).", "",
         "| paper | statement | printed | from the repository | check | source | written by |", "|---|---|---|---|---|---|---|"]
    for e in E:
        cells = [e["where"], e["what"], e["printed"], fmt(e), status(e), e["source"], e["script"]]
        L.append("| " + " | ".join(str(c).replace("|", r"\|") for c in cells) + " |")
    L += ["", "## Notes on the paper text", "",
          "Note 1 shows how a printed value is traced to two recorded files. Note 2 records a statement of the submitted paper "
          "that the recorded files do not support; the files are the record.", ""] + [x for n in notes() for x in (n, "")]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=VERSION)
    ap.add_argument("--write", action="store_true", help="write docs/paper_map.md")
    ap.add_argument("--check-fresh", action="store_true", help="fail if docs/paper_map.md differs from a fresh --write")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for e in E:
        e["ok"] = ok(e)
    bad = [e for e in E if e["ok"] is False and not e["note"]]
    print(f"{VERSION}: {len(E)} statements checked, {len(bad)} differ")
    for e in bad:
        print(f"  DIFFERS  {e['where']}: {e['what']}: paper {e['printed']}, files {fmt(e)}")
    for b in bad4:
        print("  Fig. 4:", b)
    page = render()
    stale = False
    if a.write:
        MAP.write_bytes(page.encode("utf-8"))
        print("wrote docs/paper_map.md")
    if a.check_fresh:
        stale = not MAP.exists() or MAP.read_bytes() != page.encode("utf-8")
        print("docs/paper_map.md " + ("differs from a fresh --write; run checks/check_paper_numbers.py --write" if stale else "is fresh"))
    sys.exit(1 if bad or stale else 0)


if __name__ == "__main__":
    main()

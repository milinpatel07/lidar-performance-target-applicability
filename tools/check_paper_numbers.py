#!/usr/bin/env python3
"""check_paper_numbers.py (paper-map-1.0, 2026-10-21) - every number the paper states, recomputed from the files in results/.

Each entry names where the number appears in the paper, the value as printed there, the file(s) and filter it comes
from, and the script that wrote the file. The value is recomputed from the file and compared with the printed value at
the printed precision (half a unit of the last printed digit). The paper itself is not part of the repository; the
entries quote only the statement and the number.

Usage, from the repository root:
  python3 tools/check_paper_numbers.py            # check; exit 1 on any difference
  python3 tools/check_paper_numbers.py --write    # check and write docs/paper_map.md
"""
import argparse, ast, json, math, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
SA = R / "supporting_analyses"
VERSION = "paper-map-1.0 (2026-10-21)"


def csv(rel):
    return pd.read_csv(R / rel)


def js(rel):
    return json.loads((R / rel).read_text())


def text(rel):
    return (R / rel).read_text()


# ------------------------------------------------------------------ sources used by several entries
m6A = csv("m6_protocol_seeds_weather/A_kitti_range_protocol.csv")
m6B = csv("m6_protocol_seeds_weather/B_shift_seeds_protocol.csv")
m6C = csv("m6_protocol_seeds_weather/C_weather_nuscenes.csv")
m3 = csv("m3_range_nuscenes/matrix_all_variants.csv")
m3p = m3[(m3.iou == "A_iou0.5") & (m3.objects == "car") & (m3.cut_q == 0.5)]
m7 = csv("m7_scene_split/m7_scene_split.csv")
ws = pd.read_csv(SA / "wrong_share_and_median_split0.csv")
mr = pd.read_csv(SA / "merge_recall.csv")
fpc = pd.read_csv(SA / "frames_per_condition.csv")
ret = pd.read_csv(SA / "retention_applicable_cells.csv")
au = pd.read_csv(R / "post_hoc/auroc_bootstrap.csv")
sepc = pd.read_csv(SA / "fig_separation_curves.csv")
tfv = json.loads((SA / "table_and_figure_values.json").read_text())


def frame_cells():
    """Transfer outcomes of the division by frame (Fig. 4 of the paper), KITTI rule; one row per cell and split."""
    parts = [m6A[m6A.protocol == "kitti_ignore"].assign(pair="KITTI distance"),
             m3p.assign(pair="nuScenes distance"),
             m6C.assign(pair="nuScenes weather"),
             m6B[m6B.protocol == "kitti_ignore"].rename(columns={"source": "established", "target": "applied"})
             .replace({"established": {"kitti": "KITTI", "nuscenes": "nuScenes"}, "applied": {"kitti": "KITTI", "nuscenes": "nuScenes"}})
             .assign(pair="change of dataset and detector")]
    d = pd.concat(parts, ignore_index=True)[["pair", "indicator", "seed", "alpha", "established", "applied", "outcome"]]
    return d[d.established != d.applied]


FC = frame_cells()
M7T = m7[m7.established != m7.applied]
M7O = m7[m7.established == m7.applied]


def wshare(setting, cond, ind="u_s", part="all", col="share_wrong"):
    q = ws[(ws.setting == setting) & (ws.condition == cond) & (ws.indicator == ind) & (ws.part == part)]
    assert len(q) == 1, (setting, cond, ind, part)
    return float(q[col].iloc[0])


def n_units(alpha, d):
    """Smallest n with (1 - alpha)^n <= d (Eq. 4)."""
    return math.ceil(math.log(d) / math.log(1 - alpha))


def fig4_counts():
    """Counts hard-coded in tools/figures/paper/make_fig_outcomes.py, compared cell by cell with the result files."""
    src = (ROOT / "tools/figures/paper/make_fig_outcomes.py").read_text()
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
            for alpha, c in zip((0.01, 0.05, 0.1), cs):
                q = FC[(FC.pair == pair_of[setting]) & (FC.indicator == ind) & (FC.alpha == alpha) & (FC.established == est) & (FC.applied == app)]
                got = "/".join(str(int((q.outcome == o).sum())) for o in ("applies", "not determined", "does not apply"))
                n += 1
                if got != c:
                    bad.append(f"{setting} {est}->{app} {ind} {alpha}: figure {c}, files {got}")
    return n, bad


# ------------------------------------------------------------------ the entries
# (where in the paper, statement, printed value, computed value, digits after the point, source, producing script)
E = []


def add(where, what, printed, value, digits, source, script, note=None):
    what = re.sub(r"change of dataset(?! and)", "change of dataset and detector", what).replace("nuScenes rain", "nuScenes weather")
    E.append({"where": where, "what": what, "printed": printed, "value": value, "digits": digits, "source": source, "script": script,
              "note": note})


T2 = "Table 2"
add(T2, "KITTI validation frames", "3769", sum(js("m8_kitti_drive_split/provenance.json")["frames_per_drive"].values()), 0,
    "results/m8_kitti_drive_split/provenance.json `frames_per_drive` (sum)", "analysis/m8_kitti_drive_split.py")
add(T2, "KITTI car detections with the KITTI rule", "27175", wshare("change of dataset", "KITTI (KITTI rule)", col="detections"), 0,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, KITTI (KITTI rule), part all", "tools/supporting/retention_and_causes.py")
for ds, n_gt, rec in (("KITTI", "14385", "0.858"), ("nuScenes", "65465", "0.398")):
    q = mr[mr.dataset == ds].iloc[0]
    add(T2, f"{ds}: annotated cars", n_gt, int(q.annotated_cars), 0, "results/supporting_analyses/merge_recall.csv `annotated_cars`", "tools/supporting/retention_and_causes.py")
    add(T2, f"{ds}: share of annotated cars matched after the vote", rec, float(q.recall), 3, "results/supporting_analyses/merge_recall.csv `recall`", "tools/supporting/retention_and_causes.py")
add(T2, "nuScenes validation frames", "6019", sum(js("post_hoc/provenance.json")["weather_frames"].values()), 0,
    "results/post_hoc/provenance.json `weather_frames` (sum)", "results/post_hoc/code/seq_ratio.py")
add(T2, "nuScenes scenes", "150", js("post_hoc/provenance.json")["nuscenes_scenes"], 0, "results/post_hoc/provenance.json `nuscenes_scenes`", "results/post_hoc/code/seq_ratio.py")
add(T2, "nuScenes car detections", "40036", wshare("change of dataset", "nuScenes", col="detections"), 0,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, nuScenes, part all", "tools/supporting/retention_and_causes.py")
add(T2, "near/far boundary, KITTI with the KITTI rule, split 0 (m)", "34.8", tfv["a_distance"]["KITTI_rule"]["cut_m"], 1,
    "results/supporting_analyses/table_and_figure_values.json `a_distance.KITTI_rule.cut_m`", "tools/table_and_figure_values.py")
add(T2, "near/far boundary, nuScenes, split 0 (m)", "21.4", tfv["a_distance"]["nuScenes"]["cut_m"], 1,
    "results/supporting_analyses/table_and_figure_values.json `a_distance.nuScenes.cut_m`", "tools/table_and_figure_values.py")
wf = js("post_hoc/provenance.json")["weather_frames"]
add(T2, "nuScenes clear daylight frames", "4449", wf["clear_day"], 0, "results/post_hoc/provenance.json `weather_frames.clear_day`", "results/post_hoc/code/seq_ratio.py")
add(T2, "nuScenes rain daylight frames", "968", wf["rain_day"], 0, "results/post_hoc/provenance.json `weather_frames.rain_day`", "results/post_hoc/code/seq_ratio.py")
add(T2, "nuScenes night frames excluded", "602", wf["night"] + wf["rain_night"], 0, "results/post_hoc/provenance.json `weather_frames.night + rain_night`", "results/post_hoc/code/seq_ratio.py")
for setting, cond, sel, ev in (("KITTI distance (KITTI rule)", "near", 1484, 1500), ("KITTI distance (KITTI rule)", "far", 1514, 1545),
                               ("nuScenes distance", "near", 2207, 2209), ("nuScenes distance", "far", 2270, 2276),
                               ("nuScenes rain", "clear", 1917, 1900), ("nuScenes rain", "rain", 392, 414),
                               ("change of dataset", "KITTI (KITTI rule)", 1844, 1852), ("change of dataset", "nuScenes", 2849, 2850)):
    q = fpc[(fpc.setting == setting) & (fpc.condition == cond) & (fpc.seed == 0)].iloc[0]
    add(T2, f"{setting}, {cond}: frames in the selection / test part, split 0", f"{sel} / {ev}", f"{q.frames_select} / {q.frames_eval}", None,
        "results/supporting_analyses/frames_per_condition.csv, seed 0", "tools/supporting/retention_and_causes.py")
S42 = "Sect. 4.2"
add(S42, "detections excluded by the KITTI rule", "2454", js("m6_protocol_seeds_weather/provenance.json")["A"]["ignored_total"], 0,
    "results/m6_protocol_seeds_weather/provenance.json `A.ignored_total`", "analysis/m6_protocol_seeds_weather.py")
ns = pd.read_csv(R / "post_hoc/ns_per_condition.csv")
add(S42, "rain scenes in daylight", "24", int(ns[(ns.condition == "rain") & (ns.split == 0)].sequences.iloc[0]), 0,
    "results/post_hoc/ns_per_condition.csv, rain, split 0", "results/post_hoc/code/seq_ratio.py")
add("Sect. 4.3", "KITTI drives in the validation frames", "45", js("m8_kitti_drive_split/provenance.json")["kitti_drives"], 0,
    "results/m8_kitti_drive_split/provenance.json `kitti_drives`", "analysis/m8_kitti_drive_split.py")

S51 = "Sect. 5.1 / Fig. 4"
n4, bad4 = fig4_counts()
add(S51, f"outcome counts of all {n4} transfer cells of Fig. 4 (division by frame, KITTI rule)", "as drawn", "equal" if not bad4 else "; ".join(bad4[:3]), None,
    "m6 A and B (`kitti_ignore`), m3 (`A_iou0.5`, `car`, cut 0.5), m6 C; counts in tools/figures/paper/make_fig_outcomes.py", "tools/figures/paper/make_fig_outcomes.py")
tr = ret[(ret.in_fig_outcomes == True) & (ret.alpha == 0.01)]
add(S51, "largest retention of a transferred threshold with an applicable outcome at 1e-2, any split", "29 %",
    100 * tr.R_hat.max(), 0, "results/supporting_analyses/retention_applicable_cells.csv, in_fig_outcomes, alpha 0.01", "tools/supporting/retention_and_causes.py")
own = ret[(ret.variant == "frame") & (ret.alpha == 0.01) & (ret.transfer == False)]
add(S51, "largest median retention of a threshold in its own condition with an applicable outcome at 1e-2", "47 %",
    100 * own.groupby(["setting", "indicator", "established"]).R_hat.median().max(), 0,
    "results/supporting_analyses/retention_applicable_cells.csv, own condition, division by frame, alpha 0.01", "tools/supporting/retention_and_causes.py")
taus = pd.concat([m3p[(m3p.indicator == "u_e") & (m3p.alpha == 0.01)].tau, m6C[(m6C.indicator == "u_e") & (m6C.alpha == 0.01)].tau,
                  m6B[(m6B.indicator == "u_e") & (m6B.alpha == 0.01) & (m6B.protocol == "kitti_ignore")].tau]).dropna()
add(S51, "largest threshold for u_e at 1e-2 (paper: below 0.25; m6 A records no tau, KITTI distance not covered)", "< 0.25",
    f"{taus.max():.4f}" if taus.max() < 0.25 else f"{taus.max():.4f} (not below 0.25)", None, "m3, m6 C, m6 B `tau`", "analysis/")
sq = M7T[M7T.variant == "scene_scene_unit"]
add(S51, "nuScenes transfer outcomes decided with the recorded sequence as the unit", "5 of 120",
    f"{int(sq.outcome.isin(['applies', 'does not apply']).sum())} of {len(sq[sq.alpha.isin([0.01, 0.05, 0.1])])}", None,
    "results/m7_scene_split/m7_scene_split.csv, variant scene_scene_unit, transfers, alpha 1e-2, 0.05, 0.1", "analysis/m7_scene_split_report.py")
add(S51, "of these, applicable at 0.1", "5", int(((sq.outcome == "applies") & (sq.alpha == 0.1)).sum()), 0,
    "results/m7_scene_split/m7_scene_split.csv, variant scene_scene_unit, transfers", "analysis/m7_scene_split_report.py")
for var, printed, lab in (("frame", "0 of 112", "division by frame"), ("scene_frame_unit", "5 of 113", "division by recorded sequence, frame unit")):
    q = M7O[(M7O.variant == var) & (M7O.outcome != "no threshold established")]
    add(S51, f"nuScenes thresholds in their own condition: not applicable, {lab}", printed,
        f"{int((q.outcome == 'does not apply').sum())} of {len(q)}", None, f"results/m7_scene_split/m7_scene_split.csv, variant {var}, own condition",
        "analysis/m7_scene_split_report.py")
add(S51, "bound on the frequency of not applicable in the own condition (delta + delta/2)", "7.5 %", 100 * (0.05 + 0.025), 1, "Sect. 3.4 of the paper (delta = 0.05)", "-")

S52 = "Sect. 5.2 / Fig. 5"
au_ = lambda pair, q: float(au[(au.pair == pair) & (au.quantity == q)].point.iloc[0])
for pair, q, printed in (("KITTI distance", "AUROC near", "0.915"), ("KITTI distance", "AUROC far", "0.845"),
                         ("nuScenes weather", "AUROC clear", "0.844"), ("nuScenes weather", "AUROC rain", "0.856"),
                         ("change of dataset and detector", "AUROC nuScenes", "0.749"), ("change of dataset and detector", "AUROC KITTI", "0.905")):
    add(S52, f"Fig. 5 legend, {pair}: {q} (test part of split 0)", printed, au_(pair, q), 3, "results/post_hoc/auroc_bootstrap.csv `point`",
        "results/post_hoc/code/seq_ratio.py")
m3s = text("m3_range_nuscenes/summary.txt")
au3 = {k: float(v) for k, v in re.findall(r"^\s*AUROC (near|far): ([0-9.]+) \[", m3s, re.M)[:2]}   # first block: u_s
add(S52, "AUROC of u_s, nuScenes near", "0.73", au3["near"], 2, "results/m3_range_nuscenes/summary.txt (primary variant, test part of split 0)", "analysis/m3_range_nuscenes.py")
add(S52, "AUROC of u_s, nuScenes far", "0.66", au3["far"], 2, "results/m3_range_nuscenes/summary.txt", "analysis/m3_range_nuscenes.py")
NOTE_RAIN = ("nuScenes rain", "clear")
for setting, cond, printed in (("KITTI distance (KITTI rule)", "near", "0.34"), ("KITTI distance (KITTI rule)", "far", "0.76"),
                               ("nuScenes distance", "near", "0.19"), ("nuScenes distance", "far", "0.51"),
                               ("nuScenes rain", "clear", "0.34"), ("nuScenes rain", "rain", "0.42"),
                               ("change of dataset", "KITTI (KITTI rule)", "0.55"), ("change of dataset", "nuScenes", "0.35")):
    add(S52, f"share of wrong detections, {setting}, {cond} (all validation frames)", printed, wshare(setting, cond), 2,
        "results/supporting_analyses/wrong_share_and_median_split0.csv, part all", "tools/supporting/retention_and_causes.py",
        note="note 1" if (setting, cond) == NOTE_RAIN else None)
c0 = m6C[(m6C.indicator == "u_e") & (m6C.seed == 0) & (m6C.alpha == 0.1) & (m6C.established == "clear")]
add(S52, "FAP in clear weather, u_e, threshold selected in clear weather at 0.1, split 0", "0.09", float(c0[c0.applied == "clear"].A_hat.iloc[0]), 2,
    "results/m6_protocol_seeds_weather/C_weather_nuscenes.csv", "analysis/m6_protocol_seeds_weather.py")
add(S52, "FAP in rain, same threshold", "0.17", float(c0[c0.applied == "rain"].A_hat.iloc[0]), 2,
    "results/m6_protocol_seeds_weather/C_weather_nuscenes.csv", "analysis/m6_protocol_seeds_weather.py")
mv = max(abs(wshare("nuScenes rain", "rain", "u_e", col=c) - wshare("nuScenes rain", "clear", "u_e", col=c)) for c in ("median_correct", "median_wrong"))
add(S52, "largest change of the median u_e of correct or wrong detections from clear to rain", "at most 0.03", f"{mv:.3f}" if mv <= 0.03 else f"{mv:.3f} (above 0.03)", None,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, nuScenes rain, u_e, part all", "tools/supporting/retention_and_causes.py")
add(S52, "median u_s of the correct detections, KITTI", "0.12", wshare("change of dataset", "KITTI (KITTI rule)", col="median_correct"), 2,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, part all", "tools/supporting/retention_and_causes.py")
add(S52, "median u_s of the correct detections, nuScenes", "0.23", wshare("change of dataset", "nuScenes", col="median_correct"), 2,
    "results/supporting_analyses/wrong_share_and_median_split0.csv, change of dataset, part all", "tools/supporting/retention_and_causes.py")
op = sepc[(sepc.row == "ROC operating point") & (sepc.panel.str.startswith("dataset"))]
tmax = op.tau.max()
add(S52, "share of KITTI wrong detections accepted by the nuScenes threshold at 0.1 (test part, split 0)", "about a quarter",
    f"{1 - float(op[(op.condition == 'KITTI') & (op.tau == tmax)].y.iloc[0]):.3f}", None,
    "results/supporting_analyses/fig_separation_curves.csv, ROC operating point, 1 - y", "tools/figures/paper/separation_curves.py")
add(S52, "share of nuScenes wrong detections accepted by the same threshold", "8 %", 100 * (1 - float(op[(op.condition == "nuScenes") & (op.tau == tmax)].y.iloc[0])), 0,
    "results/supporting_analyses/fig_separation_curves.csv, ROC operating point, 1 - y", "tools/figures/paper/separation_curves.py")

S53 = "Sect. 5.3 / Fig. 6"
add(S53, "units without a false acceptance needed to select a threshold at 1e-2 (delta' = 0.05)", "299", n_units(0.01, 0.05), 0, "Eq. 4", "-")
add(S53, "units needed to test at 1e-2 (delta' = 0.025)", "368", n_units(0.01, 0.025), 0, "Eq. 4", "-")
add(S53, "units needed to select a threshold at 1e-3", "2995", n_units(0.001, 0.05), 0, "Eq. 4", "-")
for ind, cond, printed in (("u_s", "rain", 5), ("u_s", "clear", 3)):
    q = m6C[(m6C.indicator == ind) & (m6C.alpha == 0.01) & (m6C.established == cond) & (m6C.applied == cond)]
    add(S53, f"splits without a threshold for u_s at 1e-2 in {cond}", str(printed), int((q.outcome == "no threshold established").sum()), 0,
        "results/m6_protocol_seeds_weather/C_weather_nuscenes.csv", "analysis/m6_protocol_seeds_weather.py")
nsel = max(v["select"]["drives"] for v in js("m8_kitti_drive_split/provenance.json")["parts_distance"].values())
add(S53, f"lowest limit that a KITTI selection part ({nsel} drives) can show to be met (zero-failure bound, delta = 0.05); paper: no threshold below 0.13",
    ">= 0.13", 1 - 0.05 ** (1 / nsel), None, "Eq. 4 with the selection drives of results/m8_kitti_drive_split/provenance.json `parts_distance`", "-")
dec = FC[FC.alpha.isin([0.01, 0.05, 0.1])]
add("Sect. 6", "transfer outcomes of Fig. 4 decided (applicable or not applicable)", "168 of 240",
    f"{int(dec.outcome.isin(['applies', 'does not apply']).sum())} of {len(dec)}", None, "as Fig. 4", "-")
add("Sect. 6", "expected wrong outcomes among them if frames were independent (168 x delta/2)", "4.2", 168 * 0.025, 1, "-", "-")
fcl = text("supporting_analyses/frame_candidates_log.txt").splitlines()[0]
add("Sect. 6.2", "accepted wrong KITTI detections inside the image with no annotation nearby", "1536",
    int(re.search(r"below 0\.1\): (\d+)", fcl).group(1)), 0,
    "results/supporting_analyses/frame_candidates_log.txt, line 1", "tools/supporting/frame_candidates.py")
ep = text("post_hoc/epoch_check.txt")
done = sorted({int(x) for x in re.findall(r"seed \d checkpoint_epoch_10\.pth: epoch=(\d+)", ep)})
add("Sect. 4.1 / 6.2", "epochs of the nuScenes members (configured 20)", "about 10", f"{done[0]} (checkpoint of epoch 10; inference used latest_model.pth just before its end)", None,
    "results/post_hoc/epoch_check.txt", "results/post_hoc/code/check_epochs.sh")


# ------------------------------------------------------------------ notes on the paper text (computed from the files)
def notes():
    c = lambda part, cond: wshare("nuScenes rain", cond, part=part)
    n1 = (f"**Note 1 (Sect. 5.2, rain).** The paper gives the share of wrong detections as rising \"from 0.34 to 0.42\" and states "
          f"that shares refer to all validation frames. Over all validation frames the shares are {c('all', 'clear'):.3f} (clear) and "
          f"{c('all', 'rain'):.3f} (rain), which round to 0.33 and 0.42; on the test part of split 0 they are {c('eval', 'clear'):.3f} and "
          f"{c('eval', 'rain'):.3f}. Source: `results/supporting_analyses/wrong_share_and_median_split0.csv`.")
    keep = {}
    for D, k0, k1 in ((m6A, "established", "applied"), (m6B, "source", "target")):
        D = D[D[k0] != D[k1]]
        for key, g in D.groupby(["indicator", "alpha", k0, k1]):
            o = {p: "".join({"applies": "A", "does not apply": "N", "not determined": "?", "no threshold established": "-"}[x]
                            for x in g[g.protocol == p].sort_values("seed").outcome) for p in ("kitti_ignore", "as_run")}
            if len(set(o["kitti_ignore"])) == 1 and o["as_run"] != o["kitti_ignore"]:
                keep[key] = o
    nm = {"kitti": "KITTI", "nuscenes": "nuScenes"}
    lst = "; ".join(f"{nm.get(a, a)} → {nm.get(b, b)}, {i}, α = {al:g}: {o['kitti_ignore']} with the rule, {o['as_run']} without (splits 0 to 4)"
                    for (i, al, a, b), o in sorted(keep.items()))
    n2 = (f"**Note 2 (Sect. 5.1, KITTI rule).** The paper states that including the detections excluded by the KITTI rule changed no "
          f"outcome that held on all five splits. In `results/m6_protocol_seeds_weather/` (protocol `kitti_ignore` with the rule, "
          f"`as_run` without), {len(keep)} transfer cells that held one outcome on all five splits with the rule change without it: {lst}. "
          "The not applicable outcome of nuScenes → KITTI for u_s holds on all five splits at every limit with and without the rule.")
    t = ret[(ret.in_fig_outcomes == True) & (ret.alpha == 0.01)]
    med = t.groupby(["setting", "indicator", "established", "applied"]).R_hat.median()
    n3 = (f"**Note 3 (Sect. 5.1, retention).** The paper writes \"at most 29 % ... (medians, Fig. 4, right)\". The largest retention "
          f"of a transferred threshold with an applicable outcome at 10⁻² is {100 * t.R_hat.max():.1f} % on a single split; the largest "
          f"median over the splits is {100 * med.max():.1f} % ({' '.join(str(x) for x in med.idxmax())}). The statements \"at most 29 %\" "
          "without the parenthesis (Sect. 5.1, answer to RQ1; Sect. 7) agree with the files. Source: "
          "`results/supporting_analyses/retention_applicable_cells.csv`.")
    return [n1, n2, n3]


# ------------------------------------------------------------------ comparison and output
def ok(e):
    p, v, d = e["printed"], e["value"], e["digits"]
    if d is None:
        if p in ("as drawn",):
            return v == "equal"
        if p.startswith(">="):
            return float(v) >= float(p[2:])
        if p.startswith("<") or p.startswith("at most") or p.startswith("about"):
            return "not" not in str(v) and "above" not in str(v) and (p != "about a quarter" or 0.2 <= float(v) <= 0.3)
        return str(v) == p
    num = float(re.sub(r"[^0-9.]", "", p))
    return abs(float(v) - num) <= 0.5 * 10 ** -d + 1e-12


def main():
    ap = argparse.ArgumentParser(description=VERSION); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    for e in E:
        e["ok"] = ok(e)
    bad = [e for e in E if not e["ok"] and not e["note"]]
    print(f"{VERSION}: {len(E)} statements checked, {len(bad)} differ")
    for e in bad:
        print(f"  DIFFERS  {e['where']}: {e['what']}: paper {e['printed']}, files {e['value']}")
    for b in bad4:
        print("  Fig. 4:", b)
    if a.write:
        fmt = lambda e: (f"{float(e['value']):.{e['digits'] + 2}f}" if e["digits"] is not None else
                         f"{e['value']:.3f}" if isinstance(e["value"], float) else str(e["value"]))
        L = ["# Paper map: every number of the paper and the file it comes from", "",
             f"Written by `tools/check_paper_numbers.py` ({VERSION}); do not edit by hand. Each row gives where a number appears in "
             "the paper, the value printed there, the value recomputed from the repository file, the file and filter, and the "
             "script that wrote the file. The check compares at the precision printed in the paper. CI runs the check on every "
             "push. The paper is not part of the repository.", "",
             "Figures of the paper: Fig. 1 (two frames, dataset images; facts in `results/supporting_analyses/fig1_two_panel_facts.txt`, "
             "scripts in `tools/figures/paper/frame_figure/`), Fig. 2 and Fig. 3 (schematics, `tools/figures/paper/fig_concept.tex`, "
             "`fig_parts.tex`), Fig. 4 (`make_fig_outcomes.py`), Fig. 5 (`make_fig_separation.py` from "
             "`results/supporting_analyses/fig_separation_curves.csv`), Fig. 6 (`fig_units.tex`). See "
             "[`tools/figures/paper/README.md`](../tools/figures/paper/README.md).", "",
             "| paper | statement | printed | from the files | check | source | written by |", "|---|---|---|---|---|---|---|"]
        for e in E:
            chk = "equal" if e["ok"] else f"differs, see {e['note']}" if e["note"] else "**differs**"
            L.append(f"| {e['where']} | {e['what']} | {e['printed']} | {fmt(e)} | {chk} | {e['source']} | {e['script']} |")
        L += ["", "## Notes on the paper text", "",
              "Three statements of the submitted paper do not agree with the recorded files. The files are the record; the notes give "
              "the values they hold.", ""] + [x for n in notes() for x in (n, "")]
        (ROOT / "docs/paper_map.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        print("wrote docs/paper_map.md")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

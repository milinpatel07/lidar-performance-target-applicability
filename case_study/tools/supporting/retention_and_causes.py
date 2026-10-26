#!/usr/bin/env python3
"""
retention_and_causes.py - descriptive tables from the recorded results and the cached per-detection tables
(no new experiment):
  retention_applicable_cells.csv     retention R of every applicable cell (all settings, frame and scene splits)
  wrong_share_and_median_split0.csv  share of wrong detections and median indicator value per condition
  intervals_clear_to_rain.csv        Hoeffding-Bentkus interval [L, U] of every clear -> rain cell
  frames_per_condition.csv           selection and evaluation frames per condition and split
  common_threshold_recorded.txt      where the common threshold tau* was computed in the recorded runs
  merge_recall.csv                   recall of the 3-of-4 merge before thresholding, merge and detector cut-offs
  roc_clear_rain_points.csv, retention_vs_false_acceptance_*.csv and the two figures in work/figures
  frame_rule_candidates.csv, frame_rule_choice.txt   KITTI frame for the frame figure by a fixed rule

Inputs, read-only: results/ (m3, m6, m7 and the m1/m3 summaries), work/cache/tables.pkl and
work/data/tau_kitti_distance_split0.json (tools/export_tables.py), RUM (detector outputs, info files,
KITTI calibration and images, detector configs), NUSC_META (scene.json, sample.json).
Statistics come from m1 in experiments/. Before anything is written, the split-0 cells of every setting are
recomputed from the cache and compared with the recorded rows; the script stops on any difference.
Writes only below work/supporting_analyses and work/figures.

Usage: python3 tools/supporting/retention_and_causes.py
"""
import csv, importlib.util, json, pickle, re, struct, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "figures"))
import layout
VERSION = "retention-and-causes-1.0 (2026-10-19)"
W = layout.RESULTS; REL = layout.WORK; RUM = layout.RUM; META = layout.NUSC_META
OUT = REL / "supporting_analyses"; FIG = REL / "figures"
m6 = layout.load_analysis()
m1, m2, m3, m4 = m6.m1, m6.m2, m6.m3, m6.m4
n1 = m3.m1                                  # m1 as used by m3 (nuScenes), as in export_tables.py
import make_figures as mf                   # colours, rcParams and roc() of the matplotlib figures
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

LOG = []
def log(s=""):
    LOG.append(s); print(s, flush=True)


def write(path, rows):
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    log(f"wrote {path.name} ({len(rows)} rows)")


def near(a, b, tol=1e-12):
    return (a is None and (b is None or b != b)) or (a is not None and b == b and abs(float(a) - float(b)) <= tol)


# ------------------------------------------------------------------ inputs
C = pickle.load(open(layout.CACHE, "rb"))
ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
kign = m6.subset(ktab, why == "")
wcls, wcounts = m6.nusc_weather_classes(META, ntab["fids"])
A_rec = pd.read_csv(W / "division_by_frame/kitti_rule_dataset_change_weather/A_kitti_range_protocol.csv")
B_rec = pd.read_csv(W / "division_by_frame/kitti_rule_dataset_change_weather/B_shift_seeds_protocol.csv")
C_rec = pd.read_csv(W / "division_by_frame/kitti_rule_dataset_change_weather/C_weather_nuscenes.csv")
M7 = pd.read_csv(W / "division_by_sequence/nuscenes_by_scene/m7_scene_split.csv")
M3 = pd.read_csv(W / "division_by_frame/nuscenes_distance/matrix_all_variants.csv")
M3 = M3[(M3.iou == "A_iou0.5") & (M3.objects == "car") & (M3.cut_q == 0.5)]
ALPHAS = m6.ALPHAS
OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
log(f"{VERSION}; tables: {C['prov']['export_version']}; KITTI frames {ktab['n_frames']}, nuScenes frames {ntab['n_frames']}; "
    f"KITTI rule removes {int((why != '').sum())}; weather frames {wcounts}")


def run_distance(tab, mod, ind, seed):
    T = dict(tab); T["u"] = tab[ind]
    car = "Car" if mod is m1 else "car"
    return mod.analyse(T, tab["y_A_iou0.5"], [car], 0.5, seed, mod.CFG, ALPHAS, boot=False)


# ------------------------------------------------------------------ gate: split-0 cells from the cache = recorded rows
bad = []
dist = {}
for ind in ("u_s", "u_e"):
    for seed in range(5):
        dist[("K", ind, seed)] = run_distance(kign, m1, ind, seed)[:2]
        dist[("N", ind, seed)] = run_distance(ntab, n1, ind, seed)[:2]
    for key, rec, q in ((("K", ind, 0), A_rec, (A_rec.protocol == "kitti_ignore")),
                        (("N", ind, 0), M3, np.ones(len(M3), bool))):
        info, res = dist[key]
        for r in res:
            for c in r["cells"]:
                row = rec[q & (rec.indicator == ind if "indicator" in rec else True) & (rec.seed == 0) & (rec.alpha == r["alpha"])
                          & (rec.established == c["established"]) & (rec.applied == c["applied"])]
                if len(row) != 1 or row.outcome.iloc[0] != c["outcome"] or not all(
                        near(c.get(k), row[k].iloc[0]) for k in ("A_hat", "hb_L", "hb_U", "R_hat")):
                    bad.append(f"distance {key} alpha {r['alpha']} {c['established']}->{c['applied']}")
det_class = wcls[ntab["fpos"]]
for ind in ("u_s", "u_e"):
    rr, _ = m6.class_matrix(ntab, det_class, ind, 0, ALPHAS, m1.CFG)
    for c in rr:
        row = C_rec[(C_rec.indicator == ind) & (C_rec.seed == 0) & (C_rec.alpha == c["alpha"]) &
                    (C_rec.established == c["established"]) & (C_rec.applied == c["applied"])]
        if len(row) != 1 or row.outcome.iloc[0] != c["outcome"] or not all(
                near(c.get(k), row[k].iloc[0]) for k in ("tau", "A_hat", "hb_L", "hb_U", "R_hat")):
            bad.append(f"rain {ind} alpha {c['alpha']} {c['established']}->{c['applied']}")
    for src, T, cn in (("kitti", kign, "Car"), ("nuscenes", ntab, "car")):
        cs = m4.car_cells(T, cn, ind, 0, 0.5)["select"]
        for alpha in ALPHAS:
            tau = m4.establish_tau(cs, np.array(m4.CFG["grid_levels"]), alpha, m1.CFG["delta"])
            row = B_rec[(B_rec.protocol == "kitti_ignore") & (B_rec.indicator == ind) & (B_rec.seed == 0) &
                        (B_rec.alpha == alpha) & (B_rec.source == src) & (B_rec.target == src)]
            if not near(tau, row.tau.iloc[0]):
                bad.append(f"dataset tau {src} {ind} alpha {alpha}")
if bad:
    (OUT / "GATE_FAILED.txt").write_text("\n".join(bad)); sys.exit(f"GATE FAILED: {len(bad)} cells differ, e.g. {bad[:3]}")
log("GATE PASSED: split-0 cells recomputed from the cache equal the recorded rows "
    "(KITTI distance with the KITTI rule, nuScenes distance, rain: tau, A, [L,U], R, outcome; dataset: tau), both indicators, all five alphas")

# ------------------------------------------------------------------ retention of every applicable cell
parts = []
a = A_rec[A_rec.protocol == "kitti_ignore"].assign(setting="KITTI distance", variant="frame")
parts.append(a)
m7 = M7.assign(setting=M7.setting.map({"distance": "nuScenes distance", "rain": "nuScenes rain"}),
               variant=M7.variant.map({"frame": "frame", "scene_frame_unit": "scene (i) frame unit",
                                       "scene_scene_unit": "scene (ii) scene unit"}))
parts.append(m7)
b = B_rec[B_rec.protocol == "kitti_ignore"].rename(columns={"source": "established", "target": "applied"})
b = b.assign(setting="change of dataset", variant="frame",
             established=b.established.map({"kitti": "KITTI", "nuscenes": "nuScenes"}),
             applied=b.applied.map({"kitti": "KITTI", "nuscenes": "nuScenes"}))
parts.append(b)
allc = pd.concat(parts, ignore_index=True)
allc["transfer"] = allc.established != allc.applied
allc["exploratory"] = allc.alpha.isin([0.05, 0.1])
allc["in_fig_outcomes"] = (allc.variant == "frame") & allc.transfer
allc["in_fig_pairs"] = allc.in_fig_outcomes & (allc.seed == 0) & (allc.alpha == 0.1)
cols = ["setting", "variant", "indicator", "seed", "alpha", "exploratory", "established", "applied", "transfer", "outcome",
        "tau", "A_hat", "hb_L", "hb_U", "R_hat", "n_select_units", "n_eval_units", "in_fig_outcomes", "in_fig_pairs"]
app = allc[allc.outcome == "applies"][cols].sort_values(["setting", "variant", "indicator", "alpha", "established", "applied", "seed"])
app.to_csv(OUT / "retention_applicable_cells.csv", index=False)
log(f"wrote retention_applicable_cells.csv ({len(app)} rows; {int(app.in_fig_outcomes.sum())} in Fig. outcomes, "
    f"{int(app.in_fig_pairs.sum())} in Fig. pairs)")
s = app[app.in_fig_outcomes].groupby(["setting", "indicator", "alpha", "established", "applied"]).R_hat.agg(["count", "min", "median", "max"])
log("retention R of the applicable transfer cells of the outcome figure (frame split, 5 splits):")
log(s.to_string(float_format=lambda v: f"{v:.4f}"))
s2 = app[app.transfer & (app.variant != "frame")].groupby(["setting", "variant", "indicator", "alpha", "established", "applied"]).R_hat.agg(["count", "min", "median", "max"])
log("same for the scene split (m7):"); log(s2.to_string(float_format=lambda v: f"{v:.4f}") if len(s2) else "   none")

# ------------------------------------------------------------------ share wrong and medians per condition, split 0
rows = []
def describe(setting, cond, tab, m, part, carname):
    y = tab["y_A_iou0.5"][m]
    for ind in ("u_s", "u_e"):
        u = tab[ind][m]
        rows.append({"setting": setting, "condition": cond, "indicator": ind, "part": part, "detections": int(m.sum()),
                     "wrong": int((y == 0).sum()), "share_wrong": float((y == 0).mean()), "median_all": float(np.median(u)),
                     "median_correct": float(np.median(u[y == 1])), "median_wrong": float(np.median(u[y == 0]))})

cutK = dist[("K", "u_s", 0)][0]["cut_m"]; cutN = dist[("N", "u_s", 0)][0]["cut_m"]
codeK = m1.split_frames(ktab["n_frames"], 0, m1.CFG)[kign["fpos"]]
codeN = n1.split_frames(ntab["n_frames"], 0, n1.CFG)[ntab["fpos"]]
carK, carN = kign["cls"] == "Car", ntab["cls"] == "car"
for part, pk, pn in (("all", np.ones_like(carK), np.ones_like(carN)), ("eval", codeK == 2, codeN == 2)):
    describe("KITTI distance (KITTI rule)", "near", kign, carK & pk & (kign["rng"] <= cutK), part, "Car")
    describe("KITTI distance (KITTI rule)", "far", kign, carK & pk & (kign["rng"] > cutK), part, "Car")
    describe("nuScenes distance", "near", ntab, carN & pn & (ntab["rng"] <= cutN), part, "car")
    describe("nuScenes distance", "far", ntab, carN & pn & (ntab["rng"] > cutN), part, "car")
    describe("nuScenes rain", "clear", ntab, carN & pn & (det_class == 0), part, "car")
    describe("nuScenes rain", "rain", ntab, carN & pn & (det_class == 1), part, "car")
def m4_eval(tab):
    rng = np.random.default_rng(0); codes = np.zeros(tab["n_frames"], np.int8)
    codes[rng.permutation(tab["n_frames"])[: int(round(0.5 * tab["n_frames"]))]] = 1
    return codes[tab["fpos"]] == 0
describe("change of dataset", "KITTI (KITTI rule)", kign, carK, "all", "Car")
describe("change of dataset", "KITTI (as run)", ktab, ktab["cls"] == "Car", "all", "Car")
describe("change of dataset", "nuScenes", ntab, carN, "all", "car")
describe("change of dataset", "KITTI (KITTI rule)", kign, carK & m4_eval(kign), "eval", "Car")
describe("change of dataset", "KITTI (as run)", ktab, (ktab["cls"] == "Car") & m4_eval(ktab), "eval", "Car")
describe("change of dataset", "nuScenes", ntab, carN & m4_eval(ntab), "eval", "car")
write(OUT / "wrong_share_and_median_split0.csv", rows)
log(f"   distance boundaries, split 0: KITTI (rule) {cutK:.4f} m, nuScenes {cutN:.4f} m")

# ------------------------------------------------------------------ HB intervals of all clear -> rain cells
r3 = m7[(m7.setting == "nuScenes rain") & (m7.established == "clear") & (m7.applied == "rain")]
r3 = r3[["variant", "indicator", "alpha", "seed", "outcome", "tau", "A_hat", "hb_L", "hb_U", "R_hat", "n_select_units", "n_eval_units"]]
r3.sort_values(["variant", "indicator", "alpha", "seed"]).to_csv(OUT / "intervals_clear_to_rain.csv", index=False)
log(f"wrote intervals_clear_to_rain.csv ({len(r3)} rows)")

# ------------------------------------------------------------------ selection and evaluation frames per condition
rows = []
for seed in range(5):
    for key, setting in ((("K", "u_s", seed), "KITTI distance (KITTI rule)"), (("N", "u_s", seed), "nuScenes distance")):
        for cond, d in dist[key][0]["classes"].items():
            rows.append({"setting": setting, "seed": seed, "condition": cond, "frames_select": d["frames_select"], "frames_eval": d["frames_eval"]})
    for cond in ("clear", "rain"):
        r = C_rec[(C_rec.indicator == "u_s") & (C_rec.seed == seed) & (C_rec.alpha == 0.01) & (C_rec.established == cond) & (C_rec.applied == cond)]
        rows.append({"setting": "nuScenes rain", "seed": seed, "condition": cond, "frames_select": int(r.frames_select.iloc[0]),
                     "frames_eval": int(r.frames_eval.iloc[0])})
    for cond, T, cn in (("KITTI (KITTI rule)", kign, "Car"), ("nuScenes", ntab, "car")):
        cc = m4.car_cells(T, cn, "u_s", seed, 0.5)
        rows.append({"setting": "change of dataset", "seed": seed, "condition": cond, "frames_select": cc["select"].m, "frames_eval": cc["eval"].m})
write(OUT / "frames_per_condition.csv", rows)
want = {("KITTI distance (KITTI rule)", "near"): 1500, ("KITTI distance (KITTI rule)", "far"): 1545, ("nuScenes distance", "near"): 2209,
        ("nuScenes distance", "far"): 2276, ("nuScenes rain", "clear"): 1900, ("nuScenes rain", "rain"): 414,
        ("change of dataset", "KITTI (KITTI rule)"): 1852, ("change of dataset", "nuScenes"): 2850}
for r in rows:
    if r["seed"] == 0:
        w = want[(r["setting"], r["condition"])]
        log(f"   split 0 {r['setting']:28s} {r['condition']:20s} select {r['frames_select']:5d}  eval {r['frames_eval']:5d} "
            f"(Table 3: {w}, {'equal' if w == r['frames_eval'] else 'DIFFERS'})")

# ------------------------------------------------------------------ common threshold tau*
lines = []
for f in (W / "division_by_frame/kitti_distance_pilot/summary.txt", W / "division_by_frame/nuscenes_distance/summary.txt"):
    lines += [f"{f.relative_to(W)}: {l.strip()}" for l in open(f) if "star" in l or "retention gap" in l or l.startswith("===") or "indicator" in l.lower()]
(OUT / "common_threshold_recorded.txt").write_text(
    "tau* (common threshold, chain over both distance classes at delta/2) is computed only in m1.analyse (distance settings).\n"
    "Recorded uses: m1 primary (KITTI, labels as run) and m3 primary (nuScenes) summary.txt, as tau values and the retention gap\n"
    "G = R(tau_c) - R(tau*) on the evaluation part of class c. No experiment run computed A_c(tau*), its HB interval or an outcome\n"
    "(common_threshold_and_recall.py computes them: common_threshold_outcomes.csv);\n"
    "m6 (KITTI rule, rain, dataset) and m7 write no tau* at all.\n\n" + "\n".join(lines) + "\n")
log("wrote common_threshold_recorded.txt")

# ------------------------------------------------------------------ recall of the 3-of-4 merge, score cut-offs
rows = []
for ds, tab, carname, f_info, f_scored, f_cache, loader in (
        ("KITTI", ktab, "Car", RUM / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl", RUM / "detections/kitti_v2/scored_val.pkl",
         RUM / "detections/kitti_v2/frame_errors_cache.pkl", lambda fi, ec: m1.load_gt(fi, ec)[0]),
        ("nuScenes", ntab, "car", RUM / "data/nuscenes/v1.0-trainval/nuscenes_infos_10sweeps_val.pkl", RUM / "detections/nuscenes/scored_val.pkl",
         RUM / "detections/nuscenes/frame_errors_cache.pkl", lambda fi, ec: m3.load_gt_nuscenes(fi, ec))):
    sc = pickle.load(open(f_scored, "rb")); ec = pickle.load(open(f_cache, "rb"))["eval_classes"]
    gt = loader(f_info, ec)
    n_gt = int(sum((np.asarray(gt[f]["gt_names"]) == carname).sum() for f in tab["fids"] if f in gt))
    car = tab["cls"] == carname; tp = int((car & (tab["y_A_iou0.5"] == 1)).sum())
    rows.append({"dataset": ds, "annotated_cars": n_gt, "correct_car_detections": tp, "recall": tp / n_gt,
                 "car_detections": int(car.sum()), "wrong_car_detections": int(car.sum()) - tp,
                 "members_K": sc.get("K"), "consensus_threshold": sc.get("consensus_threshold"),
                 "consensus_iou_threshold": sc.get("iou_threshold"), "member_min_confidence": sc.get("min_confidence"),
                 "eval_classes": "|".join(map(str, ec))})
cfg = {}
for y in sorted((RUM / "configs").glob("*.yaml")):
    cfg[y.name] = re.findall(r"SCORE_THRESH:\s*([0-9.]+)", y.read_text())
for r in rows:
    r["detector_SCORE_THRESH"] = ";".join(f"{k}={'/'.join(v)}" for k, v in cfg.items()
                                          if ("kitti" in k) == (r["dataset"] == "KITTI"))
write(OUT / "merge_recall.csv", rows)
for r in rows:
    log(f"   {r['dataset']}: annotated cars {r['annotated_cars']}, correct car detections {r['correct_car_detections']}, recall {r['recall']:.4f}; "
        f"K {r['members_K']}, consensus {r['consensus_threshold']}, IoU {r['consensus_iou_threshold']}, member min confidence {r['member_min_confidence']}")

# ------------------------------------------------------------------ ROC of u_e, clear and rain, clear-weather thresholds marked
MM = 1 / 25.4
def tau_clear(alpha):
    r = C_rec[(C_rec.indicator == "u_e") & (C_rec.seed == 0) & (C_rec.alpha == alpha) & (C_rec.established == "clear") & (C_rec.applied == "rain")]
    return float(r.tau.iloc[0])
ev = carN & (codeN == 2)
df = pd.DataFrame({"u_e": ntab["u_e"], "correct": ntab["y_A_iou0.5"], "cls": det_class})[ev]
taus = {0.01: tau_clear(0.01), 0.1: tau_clear(0.1)}
fig, ax = plt.subplots(figsize=(85 * MM, 66 * MM), layout="constrained")
pts = []
for c, lab, col in ((0, "clear", mf.INK), (1, "rain", mf.TAU)):
    sub = df[df.cls == c]
    fpr, tpr, auc = mf.roc(sub, "u_e")
    ax.plot(fpr, tpr, color=col, lw=1.0, label=f"{lab}, AUROC {auc:.3f}")
    for alpha, mk in ((0.01, "o"), (0.1, "s")):
        t = taus[alpha]
        x = float((sub.loc[sub.correct == 1, "u_e"] > t).mean()); yv = float((sub.loc[sub.correct == 0, "u_e"] > t).mean())
        ax.plot([x], [yv], marker=mk, ms=4.2, color=col, mfc=col if alpha == 0.01 else "white", mew=0.9, ls="none", zorder=4, clip_on=False)
        pts.append({"condition": lab, "alpha": alpha, "tau_clear": t, "correct_rejected": x, "wrong_rejected": yv, "auroc": auc,
                    "detections": len(sub), "correct": int(sub.correct.sum())})
ax.plot([0, 1], [0, 1], color=mf.GREY, lw=0.6, ls=":")
ax.set_xlabel("correct detections rejected"); ax.set_ylabel("wrong detections rejected")
ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1.0)
h, l = ax.get_legend_handles_labels()
h += [Line2D([], [], marker="o", color=mf.INK, ls="none", ms=4.2), Line2D([], [], marker="s", color=mf.INK, mfc="white", ls="none", ms=4.2)]
l += [r"$\tau_{\mathrm{clear}}$ at $\alpha=10^{-2}$", r"$\tau_{\mathrm{clear}}$ at $\alpha=0.1^{\dagger}$"]
ax.legend(h, l, frameon=False, loc="lower right", handlelength=1.4, borderaxespad=0.2)
fig.savefig(FIG / "roc_existence_indicator_clear_rain.pdf"); plt.close(fig)
write(OUT / "roc_clear_rain_points.csv", pts)
log("ROC points: " + "; ".join(f"{p['condition']} alpha {p['alpha']} tau {p['tau_clear']:.5f}: correct rejected {p['correct_rejected']:.3f}, "
                               f"wrong rejected {p['wrong_rejected']:.3f}" for p in pts))

# ------------------------------------------------------------------ retention against false acceptance, nuScenes near, u_e
info, res = dist[("N", "u_e", 0)]
m_ev = carN & (codeN == 2) & (ntab["rng"] <= info["cut_m"])
cell = n1.Cell(ntab["fpos"][m_ev], ntab["u_e"][m_ev], ntab["y_A_iou0.5"][m_ev])
grid = np.unique(np.r_[np.quantile(cell.u, np.linspace(0, 1, 801)), cell.u.min() - 1e-9])
curve = [{"tau": float(t), "A": float(cell.a_f(t).mean()), "R": cell.retention(t)} for t in grid]
sel = []
for r in res:
    if r["alpha"] in (0.01, 0.05, 0.1) and r["tau"]["near"] is not None:
        t = r["tau"]["near"]; A_, R_ = float(cell.a_f(t).mean()), cell.retention(t)
        rec = M3[(M3.indicator == "u_e") & (M3.seed == 0) & (M3.alpha == r["alpha"]) & (M3.established == "near") & (M3.applied == "near")]
        if not (near(t, rec.tau.iloc[0]) and near(A_, rec.A_hat.iloc[0]) and near(R_, rec.R_hat.iloc[0])):
            sys.exit(f"C2: tau/A/R at alpha {r['alpha']} differ from m3 recorded")
        sel.append({"alpha": r["alpha"], "tau_near": t, "A": A_, "R": R_, "hb_U": float(rec.hb_U.iloc[0]), "outcome": rec.outcome.iloc[0]})
fig, ax = plt.subplots(figsize=(85 * MM, 58 * MM), layout="constrained")
ax.plot([c["A"] for c in curve], [c["R"] for c in curve], color=mf.INK, lw=1.0)
for s_, mk, lab in zip(sel, ("o", "s", "D"), (r"$10^{-2}$", r"$0.05^{\dagger}$", r"$0.1^{\dagger}$")):
    ax.axvline(s_["alpha"], color=mf.GREY, lw=0.6, ls=":", zorder=1)
    ax.plot([s_["A"]], [s_["R"]], marker=mk, ms=4.2, color=mf.TAU, ls="none", zorder=4, label=r"$\tau$ selected at $\alpha=$" + lab)
ax.set_xlabel(r"false acceptance proportion $A_c(\tau)$"); ax.set_ylabel(r"retention $R_c(\tau)$")
ax.set_xlim(0, max(0.12, max(c["A"] for c in curve) * 1.02)); ax.set_ylim(0, 1.0)
ax.legend(frameon=False, loc="lower right", handlelength=1.0, borderaxespad=0.2)
fig.savefig(FIG / "retention_vs_false_acceptance_nuscenes_near.pdf"); plt.close(fig)
write(OUT / "retention_vs_false_acceptance_curve.csv", curve)
write(OUT / "retention_vs_false_acceptance_selected.csv", sel)
log("retention vs false acceptance (evaluation part, split 0, near, u_e): " + "; ".join(f"alpha {s_['alpha']}: tau {s_['tau_near']:.5f}, A {s_['A']:.4f}, R {s_['R']:.4f}, "
                                                           f"{s_['outcome']}" for s_ in sel))

# ------------------------------------------------------------------ KITTI frame for the frame figure by a fixed rule
# A frame qualifies with >= 5 scored car detections, >= 3 correct near ones of which a share >= r_min is accepted,
# no accepted wrong near detection, >= 2 accepted far detections of which >= 1 is wrong, and every accepted wrong
# box inside the image. Of these, the frame whose far-zone false acceptance is closest to the mean over all frames
# with far acceptances is chosen (typical, not extreme); ties by frame id.
tj = json.load(open(REL / "data/tau_kitti_distance_split0.json")); tauK = float(tj["tau"]["near"])
if not near(tauK, dist[("K", "u_s", 0)][1][4]["tau"]["near"]) or dist[("K", "u_s", 0)][1][4]["alpha"] != 0.1:
    sys.exit("D: tau_near of the export differs from the recomputed split-0 tau at alpha 0.1")
car = carK; u = kign["u_s"]; y = kign["y_A_iou0.5"] == 1; far = kign["rng"] > cutK; acc = u <= tauK
codes0 = m1.split_frames(ktab["n_frames"], 0, m1.CFG)
stats = []
for fpos in np.unique(kign["fpos"][car]):
    m = car & (kign["fpos"] == fpos)
    if m.sum() < 5:
        continue
    nr = m & ~far; fr = m & far
    nc = int((nr & y).sum()); nk = int((nr & y & acc).sum())
    stats.append({"fpos": int(fpos), "fid": kign["fids"][fpos], "n": int(m.sum()), "near_correct": nc, "near_ret": nk / nc if nc else 0.0,
                  "near_wrong": int((nr & acc & ~y).sum()), "far_acc": int((fr & acc).sum()), "far_wrong": int((fr & acc & ~y).sum()),
                  "part": {0: "grid", 1: "select", 2: "eval"}[int(codes0[fpos])]})
far_mean = float(np.mean([t["far_wrong"] / t["far_acc"] for t in stats if t["far_acc"] > 0]))
seeds = [{str(e.get("frame_id", "")): e for e in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/kitti_v2").glob("seed*_val.pkl"))]
scK = pickle.load(open(RUM / "detections/kitti_v2/scored_val.pkl", "rb"))


def png_size(p):
    with open(p, "rb") as f:
        h = f.read(24)
    return struct.unpack(">II", h[16:24])


def wrong_inside_image(t):
    """All accepted wrong scored car detections of the frame: every box corner in front of the camera and inside the image."""
    fid, fpos = t["fid"], t["fpos"]
    rows_all = np.where((ktab["cls"] == "Car") & (ktab["fpos"] == fpos))[0]
    mdets = [m2.member_detections(sd[fid], scK["min_confidence"]) for sd in seeds]
    cons = [c for c in m2.consensus_for_frame(mdets, scK["K"], scK["consensus_threshold"], scK["iou_threshold"]) if c["cls"] == "Car"]
    if len(cons) != len(rows_all) or not np.allclose([c["range"] for c in cons], ktab["rng"][rows_all], atol=1e-4):
        sys.exit(f"D: rebuilt boxes of {fid} do not align with the table")
    P2, R0, Tr = m6.read_calib(RUM / f"data/kitti/training/calib/{fid}.txt"); Wd, Ht = png_size(RUM / f"data/kitti/training/image_2/{fid}.png")
    out = []
    for k, c in zip(rows_all, cons):
        if why[k] != "" or ktab["y_A_iou0.5"][k] == 1 or ktab["u_s"][k] > tauK:
            continue
        p = m6.corners3d(np.asarray(c["consensus_box"][:7], float))
        cam = (R0 @ (Tr @ np.c_[p, np.ones(8)].T)).T
        img = (P2 @ np.c_[cam, np.ones(8)].T).T
        uu, vv = img[:, 0] / img[:, 2], img[:, 1] / img[:, 2]
        out.append(bool((cam[:, 2] > 0.1).all() and (uu >= 0).all() and (uu < Wd).all() and (vv >= 0).all() and (vv < Ht).all()))
    return out


def qualifies(t, r_min):
    return t["near_correct"] >= 3 and t["near_ret"] >= r_min and t["near_wrong"] == 0 and t["far_acc"] >= 2 and t["far_wrong"] >= 1


lines = [f"KITTI frame for the frame figure: fixed frame rule (below) with the figure settings (KITTI rule, split-0 tau_near(u_s) "
         f"{tauK:.5f} at alpha 0.1, boundary {cutK:.3f} m), plus: every accepted wrong detection lies inside the annotated image region "
         f"(all eight box corners in front of the camera and inside the image).",
         f"   frames with >= 5 scored car detections: {len(stats)}; mean far-zone false acceptance over frames with far acceptances: {far_mean:.4f}"]
def mark(t):
    if "n_acc_wrong" not in t:
        ins = wrong_inside_image(t); t["n_acc_wrong"] = len(ins); t["acc_wrong_inside"] = sum(ins)
        t["dist"] = abs(t["far_wrong"] / t["far_acc"] - far_mean) if t["far_acc"] else float("nan")


old = next((t for t in stats if t["fid"] == "004289"), None)
for r_min in (0.6, 0.5, 0.4):          # the near retention is relaxed in this order until a frame qualifies
    base = [t for t in stats if qualifies(t, r_min)]
    for t in base:
        mark(t)
    cand = sorted([t for t in base if t["acc_wrong_inside"] == t["n_acc_wrong"]], key=lambda t: (t["dist"], t["fid"]))
    if cand:
        break
lines.append(f"   near retention threshold used: {r_min}; frames meeting the rule: {len(base)}; "
             f"004289 meets it: {old is not None and qualifies(old, r_min)}")
if old is not None:
    mark(old)
    lines.append(f"   004289: accepted wrong {old['n_acc_wrong']}, of these inside the image {old['acc_wrong_inside']}")
lines.append(f"   frames meeting the rule with every accepted wrong detection inside the image: {len(cand)}")
for t in cand[:8]:
    lines.append(f"   {t['fid']} ({t['part']}): scored cars {t['n']}, near correct {t['near_correct']} kept {t['near_ret']:.2f}, "
                 f"far accepted {t['far_acc']} of which wrong {t['far_wrong']}, |far FAP - mean| {t['dist']:.4f}")
if cand:
    pick = cand[0]; pe = next((t for t in cand if t["part"] == "eval"), None)
    lines.append(f"   CHOSEN (all frames, closest to the mean, ties by frame id): {pick['fid']} ({pick['part']} part of split 0)")
    lines.append(f"   closest frame of the evaluation part of split 0: {pe['fid'] if pe else 'none'}")
write(OUT / "frame_rule_candidates.csv", [{k: v for k, v in t.items()} for t in base])
(OUT / "frame_rule_choice.txt").write_text("\n".join(lines) + "\n"); [log(l) for l in lines]
(OUT / "retention_and_causes_log.txt").write_text("\n".join(LOG) + "\n")

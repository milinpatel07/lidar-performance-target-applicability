#!/usr/bin/env python3
"""separation_curves.py (from v25f5-0.2, 2026-10-20; paths adapted to the repository layout) - data of Fig. 5 of the paper.

Columns of Fig. 5: distance (KITTI, u_s, near -> far, KITTI rule); weather (nuScenes, u_e, clear -> rain); change of
dataset and detector (u_s, nuScenes -> KITTI, KITTI rule). Split 0, test part. Row 1: ROC with wrong detections as the
positive class. Row 2: false acceptance proportion A_c(tau) (per-frame mean, frames without accepted detections count 0)
against tau. Thresholds selected in the condition of selection at 0.1 (exploratory) and 1e-2; the HB interval of each
condition at the 0.1 threshold. Every threshold and interval is recomputed with the analysis code and checked against the
recorded run files before anything is written; the script stops on a difference.
Inputs: work/cache/tables.pkl (tools/export_tables.py build), results/m6_five_splits, NUSC_META.
Outputs: work/supporting_analyses/fig_separation_curves.csv (compare with results/supporting_analyses/) and a draft
plot work/figures/fig_separation_draft.pdf. The paper's figure is drawn from the CSV by make_fig_separation.py."""
import csv, importlib.util, json, pickle, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import layout
META = layout.NUSC_META
m6 = layout.load_analysis()
m1, m3, m4 = m6.m1, m6.m3, m6.m4
n1 = m3.m1
MM = 1 / 25.4
SEL, USE, GREY = "black", "#0072B2", "#9E9E9E"
plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral"], "mathtext.fontset": "stix", "font.size": 7,
                     "axes.labelsize": 7, "axes.titlesize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6})
C = pickle.load(open(layout.CACHE, "rb")); ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
kign = m6.subset(ktab, why == "")
M6 = layout.RESULTS / "m6_five_splits"
A6 = pd.read_csv(M6 / "A_kitti_range_protocol.csv"); B6 = pd.read_csv(M6 / "B_shift_seeds_protocol.csv")
C6 = pd.read_csv(M6 / "C_weather_nuscenes.csv")
D = m1.CFG["delta"]


def same(a, b, what):
    if abs(float(a) - float(b)) > 1e-12:
        sys.exit(f"ABORT {what}: recomputed {a} differs from recorded {b}")


def hb(cell, t):
    a = cell.a_f(t); S, n = a.sum(), cell.m
    return S / n, m1.hb_lower(S, n, D / 2), m1.hb_upper(S, n, D / 2)


# ---------------------------------------------------------------- the three settings: cells, thresholds, recorded check
settings = []
# distance, KITTI rule, u_s
T = dict(kign); T["u"] = kign["u_s"]
info, res, _ = m1.analyse(T, kign["y_A_iou0.5"], ["Car"], 0.5, 0, m1.CFG, [0.01, 0.1], boot=False)
codes = m1.split_frames(kign["n_frames"], 0, m1.CFG)[kign["fpos"]]; cid = (kign["rng"] > info["cut_m"]).astype(int)
sel = (kign["cls"] == "Car") & (codes == 2)
cells = {c: m1.Cell(kign["fpos"][sel & (cid == i)], kign["u_s"][sel & (cid == i)], kign["y_A_iou0.5"][sel & (cid == i)]) for i, c in enumerate(("near", "far"))}
taus = {r["alpha"]: r["tau"]["near"] for r in res}
for c in ("near", "far"):
    rec = A6[(A6.protocol == "kitti_ignore") & (A6.indicator == "u_s") & (A6.seed == 0) & (A6.alpha == 0.1) & (A6.established == "near") & (A6.applied == c)]
    same(hb(cells[c], taus[0.1])[2], rec.hb_U.iloc[0], f"KITTI near->{c} U")
settings.append({"title": "distance (KITTI, $u_{\\mathrm{s}}$)", "ind": "u_s", "c": "near", "cp": "far", "cells": cells, "taus": taus})
# weather, nuScenes, u_e
wcls, _ = m6.nusc_weather_classes(META, ntab["fids"]); det_class = wcls[ntab["fpos"]]
codes = m1.split_frames(ntab["n_frames"], 0, m1.CFG)[ntab["fpos"]]
sel = (ntab["cls"] == "car") & (codes == 2)
cells = {c: m1.Cell(ntab["fpos"][sel & (det_class == i)], ntab["u_e"][sel & (det_class == i)], ntab["y_A_iou0.5"][sel & (det_class == i)]) for i, c in enumerate(("clear", "rain"))}
taus = {}
for a in (0.01, 0.1):
    rec = C6[(C6.indicator == "u_e") & (C6.seed == 0) & (C6.alpha == a) & (C6.established == "clear")]
    taus[a] = float(rec.tau.iloc[0])
    for c in ("clear", "rain"):
        same(hb(cells[c], taus[a])[2], rec[rec.applied == c].hb_U.iloc[0], f"weather clear->{c} U at {a}")
settings.append({"title": "weather (nuScenes, $u_{\\mathrm{e}}$)", "ind": "u_e", "c": "clear", "cp": "rain", "cells": cells, "taus": taus})
# dataset and detector, u_s, nuScenes -> KITTI (KITTI rule)
cn = m4.car_cells(ntab, "car", "u_s", 0, 0.5); ck = m4.car_cells(kign, "Car", "u_s", 0, 0.5)
cells = {"nuScenes": cn["eval"], "KITTI": ck["eval"]}; taus = {}
for a in (0.01, 0.1):
    taus[a] = m4.establish_tau(cn["select"], np.array(m4.CFG["grid_levels"]), a, D)
    rec = B6[(B6.protocol == "kitti_ignore") & (B6.indicator == "u_s") & (B6.seed == 0) & (B6.alpha == a) & (B6.source == "nuscenes")]
    same(taus[a], rec.tau.iloc[0], f"dataset tau at {a}")
    for c, tgt in (("nuScenes", "nuscenes"), ("KITTI", "kitti")):
        same(hb(cells[c], taus[a])[2], rec[rec.target == tgt].hb_U.iloc[0], f"dataset nuScenes->{c} U at {a}")
settings.append({"title": "dataset and detector ($u_{\\mathrm{s}}$)", "ind": "u_s", "c": "nuScenes", "cp": "KITTI", "cells": cells, "taus": taus})


# ---------------------------------------------------------------- curves
def roc(cell):
    u, y = cell.u, cell.y
    wrong = y == 0
    t = np.unique(np.r_[u, u.min() - 1e-9])
    us_c, us_w = np.sort(u[~wrong]), np.sort(u[wrong])
    x = 1 - np.searchsorted(us_c, t, side="right") / len(us_c)       # correct withheld: u > t
    yy = 1 - np.searchsorted(us_w, t, side="right") / len(us_w)      # wrong rejected: u > t
    gid, ng = m1.auroc_groups(-u, y)
    return x, yy, m1.auroc_weighted(gid, ng, y, np.ones(len(u)))


def point(cell, t):
    u, y = cell.u, cell.y
    return float((u[y == 1] > t).mean()), float((u[y == 0] > t).mean())


rows = []
fig, ax = plt.subplots(2, 3, figsize=(122 * MM, 78 * MM), gridspec_kw={"height_ratios": [1, 0.9]})
fig.subplots_adjust(left=0.095, right=0.985, top=0.915, bottom=0.11, wspace=0.40, hspace=0.42)
for j, s in enumerate(settings):
    a0, a1 = ax[0, j], ax[1, j]
    tau1, tau01 = s["taus"][0.1], s["taus"][0.01]
    hi = float(np.quantile(np.r_[s["cells"][s["c"]].u, s["cells"][s["cp"]].u], 0.995))
    grid = np.linspace(0, hi, 400)
    for c, col, ls in ((s["c"], SEL, "-"), (s["cp"], USE, "--")):
        cell = s["cells"][c]
        x, y, au = roc(cell)
        a0.plot(x, y, color=col, ls=ls, lw=0.9)
        rows += [{"panel": s["title"], "row": "ROC", "condition": c, "x": float(a), "y": float(b)} for a, b in zip(x[::max(1, len(x) // 400)], y[::max(1, len(y) // 400)])]
        for t, mk, fc in ((tau1, "s", "white"), (tau01, "o", col)):
            px, py = point(cell, t)
            a0.plot([px], [py], marker=mk, ms=3.6, mfc=fc, mec=col, mew=0.8, ls="none", zorder=4, clip_on=False)
            rows.append({"panel": s["title"], "row": "ROC operating point", "condition": c, "x": px, "y": py, "tau": t})
        yl = 0.22 if ls == "-" else 0.09          # direct label with a line sample in the free lower-right corner
        a0.plot([0.40, 0.52], [yl, yl], color=col, ls=ls, lw=0.9, transform=a0.transAxes)
        a0.text(0.55, yl, f"{c} {au:.3f}", color=col, fontsize=6, va="center", transform=a0.transAxes)
        A = np.array([cell.a_f(t).mean() for t in grid])
        a1.plot(grid, np.where(A > 0, A, np.nan), color=col, ls=ls, lw=0.9)
        rows += [{"panel": s["title"], "row": "A_c(tau)", "condition": c, "x": float(t), "y": float(v)} for t, v in zip(grid, A)]
    a0.plot([0, 1], [0, 1], color=GREY, lw=0.5, ls=":")
    a0.set_xlim(0, 1); a0.set_ylim(0, 1); a0.set_aspect("equal"); a0.set_xticks([0, 0.5, 1]); a0.set_yticks([0, 0.5, 1])
    a0.set_title(s["title"], pad=7)
    a0.set_xlabel("correct detections withheld", labelpad=1.5)
    if j == 0:
        a0.set_ylabel("wrong detections rejected", labelpad=1.5)
    for lev in (1e-2, 0.1):
        a1.axhline(lev, color=GREY, lw=0.5, ls=":")
    a1.axvline(tau1, color=SEL, lw=0.7)
    for k, (c, col) in enumerate(((s["c"], SEL), (s["cp"], USE))):
        Ah, L_, U_ = hb(s["cells"][c], tau1)
        xo = tau1 + (k - 0.5) * 0.05 * hi
        a1.plot([xo, xo], [max(L_, 1e-3), U_], color=col, lw=2.0, solid_capstyle="butt")
        rows.append({"panel": s["title"], "row": "HB interval at tau(0.1)", "condition": c, "x": tau1, "y": Ah, "L": L_, "U": U_})
    a1.set_yscale("log"); a1.set_ylim(1e-3, 1); a1.set_xlim(0, hi)
    a1.set_xlabel(r"threshold $\tau$ on " + ("$u_{\\mathrm{s}}$" if s["ind"] == "u_s" else "$u_{\\mathrm{e}}$"), labelpad=1.5)
    if j == 0:
        a1.set_ylabel(r"false acceptance $A_c(\tau)$", labelpad=1.5)
    else:
        a1.set_yticklabels([])
out_fig = layout.WORK / "figures/fig_separation_draft.pdf"; out_fig.parent.mkdir(parents=True, exist_ok=True)
out_csv = layout.WORK / "supporting_analyses/fig_separation_curves.csv"; out_csv.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out_fig)
pd.DataFrame(rows).to_csv(out_csv, index=False)
print(f"wrote {out_fig} and fig_separation_curves.csv ({len(rows)} rows)")
for s in settings:
    print(s["title"], {a: round(t, 5) for a, t in s["taus"].items()},
          {c: [round(v, 4) for v in hb(s["cells"][c], s["taus"][0.1])] for c in (s["c"], s["cp"])})

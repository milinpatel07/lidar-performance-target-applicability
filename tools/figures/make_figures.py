#!/usr/bin/env python3
"""
make_figures.py  -  figures of the causes of an exceeded target and of the change of dataset, from the
split-0 exports of tools/export_tables.py (recorded detections only, no synthetic data).

Input: one CSV per setting, one row per merged detection of the EVALUATION part of one split:
    dataset      KITTI | nuScenes
    frame        frame id (string)
    condition    near | far | clear | rain
    u_s, u_e     spatial / existence indicator
    correct      1 if the detection matches an annotated car at IoU 0.5, else 0
    dist_m       distance of the detection's own box from the sensor (m)
    excluded     1 if the KITTI rule excludes the detection (DontCare region or van), else 0
plus the thresholds selected in the selection part of the same split, as JSON:
    {"alpha": 0.1, "indicator": "u_s", "cut_m": 34.0, "tau": {"near": 0.173, "far": 0.21}}

Usage (from work/data):
    python3 tools/figures/make_figures.py causes --csv kitti_distance_split0.csv --tau tau_kitti_distance_split0.json \
                                  --indicator u_s --out fig_causes_kitti.pdf
    python3 tools/figures/make_figures.py shift  --csv kitti_all.csv --csv2 nuscenes_all.csv \
                                  --tau-kitti T_K --tau-nusc T_N --out fig_shift.pdf [--kitti-rule]

Panel (c) of fig_causes counts the ACCEPTED car detections per 5 m bin under tau_near, stacked correct / wrong,
with the share wrong above each bin holding at least 30 accepted detections. It does not show the per-bin
frame-level proportion of Eq. 1, which is not comparable to alpha: with finer classes more frames hold detections
but no accepted ones and count as 0, so the proportion decreases. --kitti-rule drops KITTI detections with
excluded == 1. All figures 4.8 in wide (LNCS text width), serif text, Computer Modern math, 7 pt.
"""
import argparse, json, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

SCRIPT_VERSION = "make_figures 1.4 (2026-10-12)"
INK = "#1F2937"; OK = "#2E7D32"; DNA = "#C62828"; TAU = "#1565C0"; GREY = "#9AA0A6"
DELTA = 0.05
WIDTH = 4.8                    # LNCS text width (in)
MIN_ACCEPTED_FOR_SHARE = 30
TEX = {"u_s": r"u_{\mathrm{s}}", "u_e": r"u_{\mathrm{e}}"}
plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "cm", "font.size": 7, "axes.labelsize": 7,
                     "axes.titlesize": 7, "legend.fontsize": 7, "legend.title_fontsize": 7, "xtick.labelsize": 7,
                     "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})


def frame_fap(df, u, tau):
    """False acceptance proportion per frame (Eq. 1); frames without accepted detections give 0."""
    acc = df[df[u] <= tau]
    g = acc.groupby("frame")["correct"].agg(["count", "sum"])
    fap = 1.0 - g["sum"] / g["count"]
    return fap.reindex(pd.Index(df["frame"].unique())).fillna(0.0)


def roc(df, u):
    """ROC of the indicator as a detector of wrong detections (positive: correct == 0); AUROC by ranks."""
    y = (df["correct"] == 0).astype(int).values; s = df[u].values
    order = np.argsort(s); y = y[order]
    P = y.sum(); N = len(y) - P
    tpr = np.cumsum(y[::-1])[::-1] / P
    fpr = np.cumsum((1 - y)[::-1])[::-1] / N
    ranks = pd.Series(df[u].values).rank().values
    yy = (df["correct"] == 0).astype(int).values
    auc = (ranks[yy == 1].sum() - P * (P + 1) / 2) / (P * N)
    return fpr, tpr, auc


def fig_causes(csv, tau_json, indicator, out, apply_rule=True):
    df = pd.read_csv(csv, dtype={"frame": str})
    if apply_rule and "excluded" in df:
        df = df[df["excluded"] == 0]
    taus = json.load(open(tau_json)); tau_near = taus["tau"]["near"]
    near, far = df[df.condition == "near"], df[df.condition == "far"]
    # two rows: (a) and (b) on top, (c) across the full width, so the per-bin labels of (c) fit at 7 pt
    fig = plt.figure(figsize=(WIDTH, 3.6), layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.1, 1.0])
    ax = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
    fig.get_layout_engine().set(hspace=0.06, wspace=0.06)

    # (a) separation
    for sub, lab, col in ((near, "near", INK), (far, "far", TAU)):
        fpr, tpr, auc = roc(sub, indicator)
        ax[0].plot(fpr, tpr, color=col, lw=1.0, label=f"{lab} {auc:.3f}")
        print(f"AUROC {lab}: {auc:.3f}")
    ax[0].plot([0, 1], [0, 1], color=GREY, lw=0.6, ls=":")
    ax[0].set_xlabel("correct detections rejected"); ax[0].set_ylabel("wrong detections rejected")
    ax[0].set_xticks([0, 0.5, 1]); ax[0].set_yticks([0, 0.5, 1])
    ax[0].legend(frameon=False, loc="lower right", title="AUROC", handlelength=1.2, borderaxespad=0.1)
    ax[0].set_title("(a) separation", loc="left")

    # (b) indicator distributions; legend below the axes
    bins = np.linspace(0, max(0.6, df[indicator].quantile(0.99)), 40)
    hmax = 0.0
    for sub, col in ((near, INK), (far, TAU)):
        for ok, ls in ((1, "-"), (0, ":")):
            # same values as hist(density=True, histtype="step"), drawn as a line so the dotted style is kept
            h, _ = np.histogram(sub.loc[sub.correct == ok, indicator], bins=bins, density=True)
            ax[1].plot(bins, np.r_[h, h[-1]], drawstyle="steps-post", color=col, lw=0.9, ls=ls)
            hmax = max(hmax, float(np.max(h)))
    ax[1].set_ylim(0, hmax * 2.3)       # headroom above the histograms for the legend
    ax[1].axvline(tau_near, color=DNA, lw=0.9)
    ax[1].text(tau_near, hmax * 1.04, r"$\tau_{\mathrm{near}}$ ", color=DNA, va="bottom", ha="right")
    ax[1].set_xlabel("indicator $" + TEX[indicator] + "$"); ax[1].set_ylabel("density")
    share_near = (near.correct == 0).mean(); share_far = (far.correct == 0).mean()
    print(f"share wrong: near {share_near:.3f}, far {share_far:.3f}")
    handles = [Line2D([], [], color=INK, lw=1.0, ls="-"), Line2D([], [], color=INK, lw=1.0, ls=":"),
               Line2D([], [], color=TAU, lw=1.0, ls="-"), Line2D([], [], color=TAU, lw=1.0, ls=":")]
    ax[1].legend(handles, ["near correct", "near wrong", "far correct", "far wrong"], ncol=1, frameon=False,
                 loc="upper right", handlelength=1.5, handletextpad=0.4, labelspacing=0.2, borderaxespad=0.0,
                 title=f"share wrong:\n{share_near:.2f} near, {share_far:.2f} far")
    ax[1].set_title("(b) share of wrong detections", loc="left")

    # (c) accepted detections per 5 m bin under tau_near, stacked correct / wrong
    acc = df[df[indicator] <= tau_near]
    edges = np.arange(0, math.ceil(df.dist_m.max() / 5) * 5 + 5, 5)
    b = np.digitize(acc.dist_m.values, edges) - 1
    n_ok = np.bincount(b[acc.correct.values == 1], minlength=len(edges) - 1)
    n_wr = np.bincount(b[acc.correct.values == 0], minlength=len(edges) - 1)
    keep = (n_ok + n_wr) > 0
    xs = (edges[:-1] + 2.5)[keep]; ok_, wr_ = n_ok[keep], n_wr[keep]
    ax[2].bar(xs, ok_, width=4.3, color=OK, lw=0)
    ax[2].bar(xs, wr_, width=4.3, bottom=ok_, color=DNA, lw=0)
    top = float((ok_ + wr_).max())
    ax[2].set_ylim(0, top * 1.3)
    ax[2].set_xlim(0, edges[-1])
    for x, c, w in zip(xs, ok_, wr_):
        if c + w >= MIN_ACCEPTED_FOR_SHARE:
            ax[2].text(x, c + w + top * 0.02, f"{w / (c + w):.2f}", ha="center", va="bottom", zorder=3,
                       bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.3})
    cut = taus.get("cut_m")
    if cut:
        ax[2].axvline(cut, color=GREY, lw=0.7, ls=":", zorder=1)
    ax[2].set_xlabel("distance of the detection (m), 5 m bins; numbers: share wrong among accepted"); ax[2].set_ylabel("accepted detections")
    ax[2].legend([Patch(color=OK), Patch(color=DNA)], ["correct", "wrong"], frameon=False, loc="upper right",
                 handlelength=1.0, borderaxespad=0.1)
    ax[2].set_title("(c) accepted detections by distance", loc="left")
    if cut:
        ax[2].text(cut, 0.99, "near | far", color=GREY, ha="center", va="top", transform=ax[2].get_xaxis_transform(),
                   bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})
    for x, c, w in zip(xs, ok_, wr_):
        print(f"bin {x - 2.5:4.0f}-{x + 2.5:<4.0f} m: accepted correct {c:5d}, wrong {w:5d}, share wrong "
              + (f"{w / (c + w):.3f}" if c + w >= MIN_ACCEPTED_FOR_SHARE else f"({w / (c + w):.3f}, not printed: < {MIN_ACCEPTED_FOR_SHARE})"))
    fig.savefig(out); print(SCRIPT_VERSION, "wrote", out)


def fig_shift(csv_k, csv_n, tau_k, tau_n, out, indicator="u_s", kitti_rule=False):
    k = pd.read_csv(csv_k); n = pd.read_csv(csv_n)
    if kitti_rule:
        k = k[k["excluded"] == 0]
    print(f"KITTI rule applied: {kitti_rule}")
    print(f"share of KITTI car detections with {indicator} <= {tau_n} (tau from nuScenes): all {(k[indicator] <= tau_n).mean():.3f}, "
          f"correct {(k.loc[k.correct == 1, indicator] <= tau_n).mean():.3f}, wrong {(k.loc[k.correct == 0, indicator] <= tau_n).mean():.3f}")
    print(f"share of nuScenes car detections with {indicator} <= {tau_k} (tau from KITTI): all {(n[indicator] <= tau_k).mean():.3f}, "
          f"correct {(n.loc[n.correct == 1, indicator] <= tau_k).mean():.3f}, wrong {(n.loc[n.correct == 0, indicator] <= tau_k).mean():.3f}")
    fig, ax = plt.subplots(figsize=(WIDTH, 2.0), layout="constrained")
    for df, lab, col in ((k, "KITTI", INK), (n, "nuScenes", TAU)):
        v = np.sort(df.loc[df.correct == 1, indicator].values); ax.plot(v, np.arange(1, len(v) + 1) / len(v), color=col, lw=1.0, label=f"{lab}, correct")
        w = np.sort(df.loc[df.correct == 0, indicator].values); ax.plot(w, np.arange(1, len(w) + 1) / len(w), color=col, lw=1.0, ls=":", label=f"{lab}, wrong")
        print(f"{lab}: median {indicator} all = {df[indicator].median():.3f}")
    lo, hi = sorted([(tau_k, r"$\tau$ from KITTI", OK), (tau_n, r"$\tau$ from nuScenes", DNA)], key=lambda t: t[0])
    ax.axvline(tau_n, color=DNA, lw=0.9); ax.axvline(tau_k, color=OK, lw=0.9, ls="--")
    ax.text(lo[0], 1.04, lo[1] + " ", color=lo[2], ha="right", va="bottom")      # left of the lower line
    ax.text(hi[0], 1.04, " " + hi[1], color=hi[2], ha="left", va="bottom")       # right of the higher line
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("indicator $" + TEX[indicator] + "$ of a car detection"); ax.set_ylabel("share of detections\nbelow this value")
    ax.set_xlim(0, 0.6); ax.legend(frameon=False, loc="lower right")
    fig.savefig(out); print(SCRIPT_VERSION, "wrote", out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=SCRIPT_VERSION); sp = p.add_subparsers(dest="cmd")
    c = sp.add_parser("causes"); c.add_argument("--csv", required=True); c.add_argument("--tau", required=True)
    c.add_argument("--indicator", default="u_s"); c.add_argument("--out", default="fig_causes.pdf"); c.add_argument("--no-rule", action="store_true")
    s = sp.add_parser("shift"); s.add_argument("--csv", required=True); s.add_argument("--csv2", required=True)
    s.add_argument("--tau-kitti", type=float, required=True); s.add_argument("--tau-nusc", type=float, required=True)
    s.add_argument("--indicator", default="u_s"); s.add_argument("--out", default="fig_shift.pdf")
    s.add_argument("--kitti-rule", action="store_true", help="drop KITTI detections with excluded == 1")
    a = p.parse_args()
    if a.cmd == "causes": fig_causes(a.csv, a.tau, a.indicator, a.out, apply_rule=not a.no_rule)
    elif a.cmd == "shift": fig_shift(a.csv, a.csv2, a.tau_kitti, a.tau_nusc, a.out, a.indicator, a.kitti_rule)
    else: p.print_help()

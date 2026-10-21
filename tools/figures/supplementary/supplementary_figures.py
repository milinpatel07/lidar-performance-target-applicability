#!/usr/bin/env python3
"""supplementary_figures.py (from v25s-0.1, 2026-10-19; paths adapted to the repository layout) - figures of the
supplementary material, from the recorded CSVs in results/ only (no data needed).

  fig_scenesplit.tex/.pdf   nuScenes: outcome counts over five splits per cell, three blocks
                                (division by frame | by recorded scene, frame as unit | by recorded scene, scene as unit)
  fig_drivesplit.tex/.pdf   KITTI (KITTI rule): the same three blocks with the division by recorded drive
  fig_retention_vs_fap.pdf    retention against false acceptance proportion, nuScenes near distance, u_e, split 0

Colours and shapes follow the style of the paper's outcome figure (no red or green; readable in greyscale): applicable = filled blue square,
not applicable = filled vermilion square with a white diagonal, not determined = light orange square with outline,
no threshold selected = empty grey outline. Needs pdflatex with the newtx fonts and TikZ for the two grids.
Run from the repository root:  python3 tools/figures/supplementary/supplementary_figures.py [--out <folder>]
(default: docs/supplementary/figures; the recorded PDFs there are the output of this script).
"""
import csv, subprocess
from collections import Counter, defaultdict
from pathlib import Path

import argparse
_ap = argparse.ArgumentParser(); _ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
_ap.add_argument("--out", default=None)
_a = _ap.parse_args(); ROOT = Path(_a.root)
OUT = Path(_a.out) if _a.out else ROOT / "docs/supplementary/figures"; OUT.mkdir(parents=True, exist_ok=True)
RES = ROOT / "results"
ALPHAS = [0.01, 0.05, 0.1]
ALAB = {0.01: "$10^{-2}$", 0.05: "0.05$^{\\dagger}$", 0.1: "0.1$^{\\dagger}$"}
CODE = {"applies": "a", "not determined": "n", "does not apply": "d", "no threshold established": "x"}


def rows(p):
    return list(csv.DictReader(open(p, newline="")))


def counts(rs, key):
    d = defaultdict(Counter)
    for r in rs:
        d[key(r)][CODE[r["outcome"]]] += 1
    return d


def grid_tex(title_blocks, groups, d):
    """groups: [(group label, [(row label, key prefix)])]; d[(block, prefix..., alpha)] -> Counter of outcome codes."""
    L = [r"\documentclass[border=1pt]{standalone}", r"\usepackage[T1]{fontenc}", r"\usepackage{newtxtext,newtxmath}",
         r"\usepackage{tikz}", r"\definecolor{appl}{HTML}{0072B2}", r"\definecolor{nappl}{HTML}{D55E00}",
         r"\definecolor{nodet}{HTML}{E69F00}", r"\definecolor{none}{HTML}{9E9E9E}",
         r"\newcommand{\us}{u_{\mathrm{s}}}\newcommand{\ue}{u_{\mathrm{e}}}",
         r"\newcommand{\sq}[3]{\ifx#3a\fill[appl] (#1,#2) rectangle ++(0.17,0.17);\fi"
         r"\ifx#3d\fill[nappl] (#1,#2) rectangle ++(0.17,0.17);\draw[white,line width=0.5pt] (#1,#2) -- ++(0.17,0.17);\fi"
         r"\ifx#3n\fill[nodet!45] (#1,#2) rectangle ++(0.17,0.17);\draw[nodet,line width=0.4pt] (#1,#2) rectangle ++(0.17,0.17);\fi"
         r"\ifx#3x\draw[none,line width=0.4pt] (#1+0.01,#2+0.01) rectangle ++(0.15,0.15);\fi}",
         r"\begin{document}", r"\begin{tikzpicture}[font=\scriptsize]", r"\def\xz{3.3}"]
    for g, t in enumerate(title_blocks):
        x0 = 3.3 + g * 4.35
        L.append(rf"\node[font=\scriptsize\bfseries, anchor=west, align=left] at ({x0 - 0.05:.2f},1.05) {{{t}}};")
        for i, a in enumerate(ALPHAS):
            L.append(rf"\node at ({x0 + i * 1.33 + 0.51:.2f},0.5) {{{ALAB[a]}}};")
    y = 0.1
    for glabel, rlist in groups:
        L.append(rf"\node[anchor=west, font=\scriptsize\bfseries] at (0,{y:.2f}) {{{glabel}}};")
        y -= 0.4
        for rlabel, prefix in rlist:
            L.append(rf"\node[anchor=east] at (3.15,{y + 0.085:.2f}) {{{rlabel}}};")
            for g in range(len(title_blocks)):
                for i, a in enumerate(ALPHAS):
                    c = d.get((g,) + prefix + (a,), Counter())
                    seq = "a" * c["a"] + "n" * c["n"] + "d" * c["d"] + "x" * c["x"]
                    if len(seq) != 5:
                        raise SystemExit(f"{(g,) + prefix + (a,)}: {len(seq)} splits instead of 5")
                    x0 = 3.3 + g * 4.35 + i * 1.33
                    L += [rf"\sq{{{x0 + k * 0.205:.3f}}}{{{y:.2f}}}{s}" for k, s in enumerate(seq)]
            y -= 0.32
        y -= 0.08
    y -= 0.25
    leg = [("a", "applicable"), ("n", "not determined"), ("d", "not applicable"), ("x", "no threshold selected")]
    for k, (s, t) in enumerate(leg):
        L += [rf"\sq{{{0.2 + k * 2.6:.2f}}}{{{y:.2f}}}{s}", rf"\node[anchor=west] at ({0.42 + k * 2.6:.2f},{y + 0.085:.2f}) {{{t}}};"]
    L += [rf"\node[anchor=west, font=\tiny] at (0.2,{y - 0.32:.2f}) {{five squares per cell: the five splits; row: threshold selected in $\to$ used in; $^\dagger$ exploratory limit}};",
          r"\end{tikzpicture}", r"\end{document}"]
    return "\n".join(L) + "\n"


def build(name, blocks, groups, d):
    p = OUT / f"{name}.tex"
    p.write_bytes(grid_tex(blocks, groups, d).encode())
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", p.name], cwd=OUT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout[-2000:])
    for ext in (".aux", ".log"):
        (OUT / f"{name}{ext}").unlink(missing_ok=True)
    print(f"wrote {name}.pdf")


# ---------------------------------------------------------------- nuScenes, division by recorded scene
m7 = rows(RES / "m7_scene_split/m7_scene_split.csv")
blk = {"frame": 0, "scene_frame_unit": 1, "scene_scene_unit": 2}
d7 = counts(m7, lambda r: (blk[r["variant"]], r["setting"], r["indicator"], r["established"], r["applied"], float(r["alpha"])))
groups = []
for setting, lab, pairs in (("distance", "nuScenes distance", (("near", "far"), ("far", "near"))),
                            ("rain", "nuScenes weather", (("clear", "rain"), ("rain", "clear")))):
    for ind in ("u_s", "u_e"):
        groups.append((f"{lab}, ${'\\us' if ind == 'u_s' else '\\ue'}$",
                       [(f"{a} $\\to$ {b}", (setting, ind, a, b)) for a, b in pairs]))
build("fig_scenesplit", ["division by frame", "by recorded scene,\\\\frame as unit", "by recorded scene,\\\\scene as unit"], groups, d7)

# ---------------------------------------------------------------- KITTI, division by recorded drive
A6 = [r for r in rows(RES / "m6_protocol_seeds_weather/A_kitti_range_protocol.csv") if r["protocol"] == "kitti_ignore"]
B6 = [r for r in rows(RES / "m6_protocol_seeds_weather/B_shift_seeds_protocol.csv") if r["protocol"] == "kitti_ignore"]
A8 = [r for r in rows(RES / "m8_kitti_drive_split/A_kitti_distance_drive.csv") if r["protocol"] == "kitti_ignore"]
B8 = [r for r in rows(RES / "m8_kitti_drive_split/B_dataset_drive.csv") if r["protocol"] == "kitti_ignore"]
d8 = defaultdict(Counter)
for rs, b in ((A6, None), (A8, "unit")):
    for r in rs:
        g = 0 if b is None else (1 if r["hb_unit"] == "frame" else 2)
        d8[(g, "distance", r["indicator"], r["established"], r["applied"], float(r["alpha"]))][CODE[r["outcome"]]] += 1
for rs, b in ((B6, None), (B8, "unit")):
    for r in rs:
        g = 0 if b is None else (1 if r["hb_unit"] == "frame" else 2)
        d8[(g, "dataset", r["indicator"], r["source"], r["target"], float(r["alpha"]))][CODE[r["outcome"]]] += 1
groups = []
for setting, lab, pairs in (("distance", "KITTI distance", (("near", "far"), ("far", "near"))),
                            ("dataset", "change of dataset and detector", (("nuscenes", "kitti"), ("kitti", "nuscenes")))):
    for ind in ("u_s", "u_e"):
        nice = {"nuscenes": "nuScenes", "kitti": "KITTI"}
        groups.append((f"{lab}, ${'\\us' if ind == 'u_s' else '\\ue'}$",
                       [(f"{nice.get(a, a)} $\\to$ {nice.get(b, b)}", (setting, ind, a, b)) for a, b in pairs]))
build("fig_drivesplit", ["division by frame", "by recorded drive,\\\\frame as unit", "by recorded drive,\\\\drive as unit"], groups, d8)

# ---------------------------------------------------------------- retention against false acceptance 
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "STIXGeneral"], "mathtext.fontset": "stix",
                     "font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6,
                     "pdf.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6})
SA = RES / "supporting_analyses"
cur = rows(SA / "retention_vs_false_acceptance_curve.csv"); sel = rows(SA / "retention_vs_false_acceptance_selected.csv")
fig, ax = plt.subplots(figsize=(85 / 25.4, 58 / 25.4), layout="constrained")
ax.plot([float(r["A"]) for r in cur], [float(r["R"]) for r in cur], color="black", lw=0.9)
for r, mk, lab in zip(sel, ("o", "s", "D"), ("$10^{-2}$", "$0.05^{\\dagger}$", "$0.1^{\\dagger}$")):
    a = float(r["alpha"])
    ax.axvline(a, color="#9E9E9E", lw=0.5, ls=":", zorder=1)
    ax.plot([float(r["A"])], [float(r["R"])], marker=mk, ms=4, color="#0072B2", mfc="white" if mk != "o" else "#0072B2",
            mew=0.9, ls="none", zorder=4, label=r"$\tau$ selected at $\alpha=$" + lab)
ax.set_xlabel(r"false acceptance proportion $A_c(\tau)$"); ax.set_ylabel(r"retention $R_c(\tau)$")
ax.set_xlim(0, 0.18); ax.set_ylim(0, 1.0); ax.legend(frameon=False, loc="lower right", handlelength=1.0)
fig.savefig(OUT / "fig_retention_vs_fap.pdf"); print("wrote fig_retention_vs_fap.pdf")

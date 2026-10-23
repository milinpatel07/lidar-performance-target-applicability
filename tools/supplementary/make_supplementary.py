#!/usr/bin/env python3
"""make_supplementary.py (supp-public-1.0, 2026-10-21) - the supplementary material of the paper, from repository files only.

Writes docs/supplementary/supplementary.tex and docs/supplementary/supplementary_sources.csv. No analysis is recomputed:
every number is read from a file in results/ or docs/ and listed in the sources file with its path, line or row, and
column. With --check, every CSV-sourced value is re-read at its row and column and compared with the printed value, and
every printed value is searched in the .tex; the script exits 1 on any difference.
Compile:  cd docs/supplementary && pdflatex supplementary.tex  (twice, for the table of contents and references).

Run from the repository root:
  python3 tools/supplementary/make_supplementary.py            # write .tex and sources
  python3 tools/supplementary/make_supplementary.py --check    # verify them
"""
import argparse, csv, hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path

VERSION = "supp-public-1.0 (2026-10-21)"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/supplementary"
NAME = "supplementary"
R, SA = "results", "results/supporting_analyses"
F = {
    "m3": f"{R}/m3_nuscenes_distance/matrix_all_variants.csv",
    "m4": f"{R}/m4_dataset_change/shift_matrix.csv",
    "m6A": f"{R}/m6_five_splits/A_kitti_range_protocol.csv",
    "m6Ar": f"{R}/m6_five_splits/A_kitti_range_protocol.csv",
    "m6B": f"{R}/m6_five_splits/B_shift_seeds_protocol.csv",
    "m6C": f"{R}/m6_five_splits/C_weather_nuscenes.csv",
    "m6p": f"{R}/m6_five_splits/provenance.json",
    "m6s": f"{R}/m6_five_splits/summary.txt",
    "m7": f"{R}/m7_nuscenes_by_scene/m7_scene_split.csv",
    "m7summ": f"{R}/m7_nuscenes_by_scene/m7_scene_split_summary.txt",
    "m7repro": f"{R}/m7_nuscenes_by_scene/REPRO_PASSED.txt",
    "m8rep": f"{R}/m8_kitti_by_drive/REPRO_PASSED.txt",
    "m8cnt": f"{SA}/m8_outcome_counts.csv",
    "m8drv": f"{SA}/m8_drives_per_part.csv",
    "bins": f"{SA}/distance_bins_log.txt",
    "tfv": f"{SA}/table_and_figure_values.json",
    "fig1facts": f"{SA}/fig1_two_panel_facts.txt",
    "fig1b": f"{SA}/fig1b_candidates.csv",
    "A1": f"{SA}/retention_applicable_cells.csv",
    "A2": f"{SA}/wrong_share_and_median_split0.csv",
    "A3": f"{SA}/intervals_clear_to_rain.csv",
    "A4": f"{SA}/frames_per_condition.csv",
    "A5": f"{SA}/common_threshold_outcomes.csv",
    "pred": "docs/study_protocol/predictions_frozen_2026-10-01.md",
    "phsum": f"{R}/post_hoc/summary.csv",
    "phau": f"{R}/post_hoc/auroc_bootstrap.csv",
    "phns": f"{R}/post_hoc/ns_per_condition.csv",
    "phep": f"{R}/post_hoc/epoch_check.txt",
    "phgate": f"{R}/post_hoc/GATE_PASSED.txt",
}
SOURCES = []


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def num(value, fmt, src, where, col, ctx):
    """Format a recorded value and log it in the sources file."""
    s = fmt.format(float(value)) if fmt else str(value)
    SOURCES.append({"context": ctx, "value_printed": s, "value_recorded": value, "file": F.get(src, src),
                    "row_or_line": where, "column": col})
    return s


def rows(key):
    with open(ROOT / F[key], newline="") as f:
        return list(csv.DictReader(f))     # row i (0-based) is file line i + 2


def tex(s):
    """Escape plain text for LaTeX (the recorded strings hold no backslashes or braces)."""
    s = str(s)
    for a, b in (("_", "\\_"), ("%", "\\%"), ("&", "\\&"), ("#", "\\#"), ("$", "\\$"), ("~", "\\~{}"), ("^", "\\^{}")):
        s = s.replace(a, b)
    return s


def alpha_tex(a):
    a = float(a)
    return {1e-2: "$10^{-2}$", 1e-3: "$10^{-3}$", 1e-4: "$10^{-4}$", 5e-2: "0.05", 1e-1: "0.1"}[a]


ALPHA_ORDER = [1e-2, 1e-3, 1e-4, 5e-2, 1e-1]


CODE = {"applies": "A", "does not apply": "N", "not determined": "?", "no threshold established": "-"}
SOURCES = []


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def num(value, fmt, src, where, col, ctx):
    """Format a recorded value and log it in the sources file."""
    s = fmt.format(float(value)) if fmt else str(value)
    SOURCES.append({"context": ctx, "value_printed": s, "value_recorded": value, "file": F.get(src, src),
                    "row_or_line": where, "column": col})
    return s


def rows(key):
    with open(ROOT / F[key], newline="") as f:
        return list(csv.DictReader(f))     # row i (0-based) is file line i + 2


def tex(s):
    """Escape plain text for LaTeX (the recorded strings hold no backslashes or braces)."""
    s = str(s)
    for a, b in (("_", "\\_"), ("%", "\\%"), ("&", "\\&"), ("#", "\\#"), ("$", "\\$"), ("~", "\\~{}"), ("^", "\\^{}")):
        s = s.replace(a, b)
    return s


def alpha_tex(a):
    a = float(a)
    return {1e-2: "$10^{-2}$", 1e-3: "$10^{-3}$", 1e-4: "$10^{-4}$", 5e-2: "0.05", 1e-1: "0.1"}[a]


ALPHA_ORDER = [1e-2, 1e-3, 1e-4, 5e-2, 1e-1]


def compact(key, rs, group, cell, ctx):
    """One line per cell: the outcome code of every seed. rs: list of (line, row)."""
    d = defaultdict(dict)
    for ln, r in rs:
        k = tuple(r[g] for g in group) + (float(r["alpha"]),) + tuple(r[c] for c in cell)
        d[k][int(r["seed"])] = (ln, r)
    out = []
    for k in sorted(d, key=lambda k: (k[:len(group)], ALPHA_ORDER.index(k[len(group)]), k[len(group) + 1:])):
        seeds = sorted(d[k])
        codes = "".join(CODE[num(d[k][s][1]["outcome"], None, key, d[k][s][0], "outcome",
                                 f"{ctx} {k} seed {s}")] for s in seeds)
        out.append(" & ".join([tex(x) for x in k[:len(group)]] + [alpha_tex(k[len(group)])] +
                              [tex(x) for x in k[len(group) + 1:]] + [f"\\texttt{{{codes}}}"]) + " \\\\")
    return out


def detailed(key, rs, group, cell, ctx, n_col=None):
    """One line per cell and seed with a threshold: tau, A, HB interval, R (and n if recorded)."""
    out = []
    for ln, r in sorted(rs, key=lambda x: (tuple(x[1][g] for g in group), ALPHA_ORDER.index(float(x[1]["alpha"])),
                                           tuple(x[1][c] for c in cell), int(x[1]["seed"]))):
        if r["A_hat"] in ("", "None"):
            continue
        c = f"{ctx} {[r[g] for g in group]} {r['alpha']} {[r[x] for x in cell]} seed {r['seed']}"
        vals = [num(r["tau"], "{:.4f}", key, ln, "tau", c)] if "tau" in r else []
        vals += [num(r["A_hat"], "{:.4f}", key, ln, "A_hat", c),
                "[" + num(r["hb_L"], "{:.4f}", key, ln, "hb_L", c) + ", " + num(r["hb_U"], "{:.4f}", key, ln, "hb_U", c) + "]",
                num(r["R_hat"], "{:.3f}", key, ln, "R_hat", c)]
        if n_col:
            vals.append(num(r[n_col], None, key, ln, n_col, c))
        out.append(" & ".join([tex(r[g]) for g in group] + [alpha_tex(r["alpha"])] + [tex(r[x]) for x in cell] +
                              [r["seed"]] + vals + [CODE[r["outcome"]]]) + " \\\\")
    return out


def longtable(spec, head, body, caption, label):
    return ["{\\scriptsize", f"\\begin{{longtable}}{{{spec}}}", f"\\caption{{{caption}}}\\label{{{label}}}\\\\",
            "\\toprule", head + " \\\\", "\\midrule", "\\endfirsthead", "\\toprule", head + " \\\\", "\\midrule",
            "\\endhead", "\\bottomrule", "\\endfoot"] + body + ["\\end{longtable}", "}", ""]


def numbered(key):
    return [(i + 2, r) for i, r in enumerate(rows(key))]


def sec_outcomes():
    L = ["\\section{Per-split outcome tables}\\label{sec:outcomes}",
         "Each line is one cell of an applicability matrix: the threshold selected in one condition "
         "(\\emph{sel.}, condition of selection) tested in the condition of use (\\emph{use}) at limit $\\alpha$. The code string gives the outcome "
         "per split, seeds 0 to 4 from left to right: \\texttt{A} applicable, \\texttt{N} not applicable, "
         "\\texttt{?} not determined, \\texttt{-} no threshold selected. The detailed tables give, per split with a "
         "threshold, the threshold $\\tau$, the false acceptance proportion $\\hat A$ with its two-sided HB interval "
         "($\\delta=0.05$) and the retention $\\hat R$, as recorded. Limits $10^{-2}$, $10^{-3}$, $10^{-4}$ are the "
         "target limits; 0.05 and 0.1 are exploratory limits.", ""]
    # m3
    m3 = numbered("m3")
    L += ["\\subsection{nuScenes, distance (m3)}",
          f"Source: \\path{{{(F['m3'])}}}. Variants: overlap setting (IoU 0.5), object set (car; "
          "vehicles), cut quantile of car range in the grid part (0.25, 0.5, 0.75). The primary variant is car, cut "
          "quantile 0.5.", ""]
    L += longtable("lllllll", "objects & cut q. & ind. & $\\alpha$ & sel. & use & seeds 0--4",
                   compact("m3", m3, ["objects", "cut_q", "indicator"], ["established", "applied"], "m3 outcome"),
                   "nuScenes distance (m3), all variants: outcome per split.", "tab:m3c")
    prim = [(ln, r) for ln, r in m3 if r["objects"] == "car" and r["cut_q"] == "0.5"]
    L += longtable("llllrrrrrc", "ind. & $\\alpha$ & sel. & use & seed & $\\tau$ & $\\hat A$ & HB interval & $\\hat R$ & out.",
                   detailed("m3", prim, ["indicator"], ["established", "applied"], "m3 primary"),
                   "nuScenes distance (m3), primary variant (car, median cut): values per split.", "tab:m3d")
    # m6 A
    A = numbered("m6A")
    L += ["\\subsection{KITTI, distance, labels as run and with the KITTI rule (m6 part A)}",
          f"Source: \\path{{{(F['m6A'])}}}. Car detections, median cut of the grid part. Protocol "
          "\\texttt{as\\_run}: labels of the detection pipeline; \\texttt{kitti\\_ignore}: wrong detections in DontCare "
          "regions or on a Van removed (Section~\\ref{sec:rule}).", ""]
    L += longtable("llllll", "protocol & ind. & $\\alpha$ & sel. & use & seeds 0--4",
                   compact("m6A", A, ["protocol", "indicator"], ["established", "applied"], "m6A outcome"),
                   "KITTI distance (m6 A): outcome per split.", "tab:m6Ac")
    L += longtable("lllllrrrrc", "protocol & ind. & $\\alpha$ & sel. & use & seed & $\\hat A$ & HB interval & $\\hat R$ & out.",
                   detailed("m6A", A, ["protocol", "indicator"], ["established", "applied"], "m6A"),
                   "KITTI distance (m6 A): values per split (no $\\tau$ column is recorded in this file).", "tab:m6Ad")
    # m4 and m6 B
    m4 = numbered("m4")
    for _, r in m4:
        r["seed"] = "0"
    L += ["\\subsection{Change of dataset and detector, KITTI and nuScenes (m4, one split; m6 part B, five splits)}",
          f"Sources: \\path{{{(F['m4'])}}} (one split by frame, 50\\,\\% selection, 50\\,\\% test part; "
          f"listed as seed 0) and \\path{{{(F['m6B'])}}} (seeds 0 to 4, labels as run and with the KITTI rule).", ""]
    L += longtable("lllll", "ind. & $\\alpha$ & source & target & split",
                   compact("m4", m4, ["indicator"], ["source", "target"], "m4 outcome"),
                   "Change of dataset and detector (m4): outcome of the recorded split.", "tab:m4c")
    L += longtable("lllllrrrrrc", "ind. & $\\alpha$ & source & target & split & $\\tau$ & $\\hat A$ & HB interval & $\\hat R$ & $n$ & out.",
                   detailed("m4", m4, ["indicator"], ["source", "target"], "m4", n_col="n_eval_frames"),
                   "Change of dataset and detector (m4): values ($n$: test frames).", "tab:m4d")
    B = numbered("m6B")
    L += longtable("llllll", "protocol & ind. & $\\alpha$ & source & target & seeds 0--4",
                   compact("m6B", B, ["protocol", "indicator"], ["source", "target"], "m6B outcome"),
                   "Change of dataset and detector (m6 B): outcome per split.", "tab:m6Bc")
    L += longtable("llllllrrrrc", "protocol & ind. & $\\alpha$ & source & target & seed & $\\tau$ & $\\hat A$ & HB interval & $\\hat R$ & out.",
                   detailed("m6B", B, ["protocol", "indicator"], ["source", "target"], "m6B"),
                   "Change of dataset and detector (m6 B): values per split.", "tab:m6Bd")
    # m6 C
    C = numbered("m6C")
    L += ["\\subsection{nuScenes, recorded rain against clear daytime (m6 part C)}",
          f"Source: \\path{{{(F['m6C'])}}}. A frame's condition comes from its scene description; night and "
          "rain-at-night frames are excluded. Rain frames hold airborne scatterers and a wet road together, so the "
          "condition is recorded rain, not one physical process.", ""]
    L += longtable("lllll", "ind. & $\\alpha$ & sel. & use & seeds 0--4",
                   compact("m6C", C, ["indicator"], ["established", "applied"], "m6C outcome"),
                   "Rain (m6 C): outcome per split.", "tab:m6Cc")
    L += longtable("llllrrrrrrc", "ind. & $\\alpha$ & sel. & use & seed & $\\tau$ & $\\hat A$ & HB interval & $\\hat R$ & $n_{\\mathrm{eval}}$ & out.",
                   detailed("m6C", C, ["indicator"], ["established", "applied"], "m6C", n_col="frames_eval"),
                   "Rain (m6 C): values per split ($n_{\\mathrm{eval}}$: test frames of the condition of use).", "tab:m6Cd")
    return L


def sec_rule():
    prov = json.load(open(ROOT / F["m6p"]))["A"]
    summ = (ROOT / F["m6s"]).read_text().splitlines()
    L = ["\\section{KITTI rule: counts}\\label{sec:rule}",
         "The labels of the detection pipeline count a car detection as wrong when it lies in a KITTI DontCare region or "
         "on a Van. The KITTI rule removes such wrong detections (neither correct nor wrong): a wrong car detection is "
         "removed if its 3D overlap with a Van is at least 0.5, or if its projected 2D box overlaps a DontCare box by "
         "more than half of the detection's own area. Only detections labelled wrong can be removed. "
         f"Sources: \\path{{{(F['m6p'])}}} (key \\texttt{{A}}) and \\path{{{(F['m6s'])}}}.", "",
         "\\begin{table}[H]\\centering\\small",
         "\\caption{Wrong car detections and the detections the KITTI rule removes, by distance class (cut: median car range over all frames).}",
         "\\begin{tabular}{lrrrr}\\toprule class & wrong & in DontCare & on Van & share removed \\\\ \\midrule"]
    for z in ("near", "far"):
        d = prov["diagnostics"][z]
        ln = next(i + 1 for i, s in enumerate(summ) if s.strip().startswith(f"{z}: FP"))
        share = re.search(r"share ignored ([0-9.]+)", summ[ln - 1]).group(1)
        L.append(f"{z} & " + " & ".join(num(d[k], None, "m6p", f"A.diagnostics.{z}", k, f"KITTI rule {z} {k}")
                                       for k in ("fp", "DontCare", "Van")) +
                 f" & {num(share, None, 'm6s', ln, 'share ignored', f'KITTI rule {z} share')} \\\\")
    L += ["\\bottomrule\\end{tabular}\\end{table}", "",
          f"Detections removed in total: {num(prov['ignored_total'], None, 'm6p', 'A.ignored_total', '', 'KITTI rule total')}; "
          f"median car range over all frames: {num(prov['median_car_range_m'], '{:.3f}', 'm6p', 'A.median_car_range_m', '', 'KITTI median range')}\\,m. "
          "The outcome counts with and without the rule are in Tables~\\ref{tab:m6Ac} and~\\ref{tab:m6Bc}.", ""]
    return L


def fig(path, caption, label, width="\\textwidth"):
    return ["\\begin{figure}[H]\\centering", f"\\includegraphics[width={width}]{{{path}}}", f"\\caption{{{caption}}}\\label{{{label}}}",
            "\\end{figure}", ""]


def sec_classes():
    body = ["C1 & airborne scatterers & returns without a surface behind them; fewer distant returns & with C2, as recorded rain \\\\",
            "C2 & surface water, spray & non-rigid clusters; fewer ground returns & with C1, as recorded rain \\\\",
            "C3 & vehicle-like structure & consistent geometry where no vehicle is & no \\\\",
            "C4 & occlusion & partial evidence on a present object & no \\\\",
            "C5 & distance & fewer returns per object & both datasets \\\\"]
    return ["\\section{Condition classes}\\label{sec:classes}",
            "Each condition is represented by a class of frames or detections in which one process acts on the point cloud. "
            "Neither dataset labels classes C3 and C4, and they are not measured.", ""] + \
        longtable("p{0.8cm}p{3.0cm}p{6.2cm}p{3.4cm}", "class & process & effect on detections & measured", body,
                  "Condition classes, defined by the process acting on the point cloud.", "tab:classes")


def sec_per_split_A():
    m3p = lambda r: r["iou"] == "A_iou0.5" and r["objects"] == "car" and r["cut_q"] == "0.5"
    sources = [("KITTI distance", "m6Ar", lambda r: r["protocol"] == "kitti_ignore", "established", "applied"),
               ("nuScenes distance", "m3", m3p, "established", "applied"),
               ("nuScenes weather", "m6C", lambda r: True, "established", "applied"),
               ("dataset and detector", "m6B", lambda r: r["protocol"] == "kitti_ignore", "source", "target")]
    body, into, back = [], [], []
    for setting, key, keep, e, a in sources:
        d = defaultdict(dict)
        for ln, r in numbered(key):
            if keep(r) and float(r["alpha"]) == 0.1 and r[e] != r[a]:
                d[(r["indicator"], r[e], r[a])][int(r["seed"])] = (ln, r)
        for (ind, src, dst), sd in sorted(d.items()):
            vals = []
            for s in range(5):
                ln, r = sd[s]
                v = num(r["A_hat"], "{:.3f}", key, ln, "A_hat", f"A at 0.1, {setting} {ind} {src}->{dst} seed {s}")
                vals.append(f"{v}\\,{CODE[r['outcome']]}")
                (into if dst in ("far", "rain", "kitti") else back).append(float(r["A_hat"]))
            body.append(" & ".join([setting, tex(ind), f"{tex(src)} $\\to$ {tex(dst)}"] + vals) + " \\\\")
    return ["\\section{False acceptance proportion per split at the exploratory limit 0.1}\\label{sec:Aper}",
            "Division by frame, KITTI with the KITTI rule. Each entry gives the false acceptance proportion $A$ on the evaluation "
            "part of the condition of use and the outcome code (A applicable, N not applicable, ? not determined). Over the transfers "
            f"into far distance, rain or KITTI, $A$ ranges from {min(into):.3f} to {max(into):.3f}; over the transfers in the "
            f"opposite direction from {min(back):.3f} to {max(back):.3f} (minimum and maximum of the listed values).", ""] + \
        longtable("p{2.6cm}p{0.6cm}p{2.6cm}lllll", "setting & ind. & transfer & split 0 & split 1 & split 2 & split 3 & split 4",
                  body, "False acceptance proportion at the exploratory limit 0.1 per split.", "tab:Aper")


def sec_review_tables():
    L = ["\\section{Retention, shares of wrong detections, intervals, frames and the common threshold (division by frame)}\\label{sec:review}", ""]
    body = []
    for ln, r in numbered("A1"):
        if float(r["alpha"]) == 0.01 and r["transfer"] == "True":
            c = f"retention at 1e-2 {r['setting']} {r['variant']} {r['indicator']} {r['established']}->{r['applied']} seed {r['seed']}"
            body.append(" & ".join([tex(r["setting"]), tex(r["variant"]), tex(r["indicator"]), f"{tex(r['established'])} $\\to$ {tex(r['applied'])}",
                                    r["seed"], num(r["A_hat"], "{:.4f}", "A1", ln, "A_hat", c),
                                    "[" + num(r["hb_L"], "{:.4f}", "A1", ln, "hb_L", c) + ", " + num(r["hb_U"], "{:.4f}", "A1", ln, "hb_U", c) + "]",
                                    num(r["R_hat"], "{:.4f}", "A1", ln, "R_hat", c)]) + " \\\\")
    L += longtable("p{2.4cm}p{2.4cm}p{0.6cm}p{2.2cm}llll", "setting & division & ind. & transfer & split & $A$ & $[L,U]$ & $R$", body,
                   "Every applicable transfer at $10^{-2}$ with its retention $R$ (share of correct detections kept).", "tab:A1")
    body = []
    for ln, r in numbered("A2"):
        c = f"share wrong {r['setting']} {r['condition']} {r['indicator']} {r['part']}"
        body.append(" & ".join([tex(r["setting"]), tex(r["condition"]), tex(r["indicator"]), r["part"], num(r["detections"], None, "A2", ln, "detections", c),
                                num(r["share_wrong"], "{:.3f}", "A2", ln, "share_wrong", c), num(r["median_all"], "{:.3f}", "A2", ln, "median_all", c),
                                num(r["median_correct"], "{:.3f}", "A2", ln, "median_correct", c), num(r["median_wrong"], "{:.3f}", "A2", ln, "median_wrong", c)]) + " \\\\")
    L += longtable("p{3.0cm}p{2.2cm}p{0.5cm}llllll", "setting & condition & ind. & part & det. & wrong & med. & med. corr. & med. wrong",
                   body, "Car detections, share of wrong ones and median indicator value per condition, split 0 (all parts, and the test part).", "tab:A2")
    body = []
    for ln, r in numbered("A3"):
        if r["A_hat"] in ("", "None"):
            continue
        c = f"clear->rain {r['variant']} {r['indicator']} {r['alpha']} seed {r['seed']}"
        body.append(" & ".join([tex(r["variant"]), tex(r["indicator"]), alpha_tex(r["alpha"]), r["seed"], num(r["A_hat"], "{:.4f}", "A3", ln, "A_hat", c),
                                "[" + num(r["hb_L"], "{:.4f}", "A3", ln, "hb_L", c) + ", " + num(r["hb_U"], "{:.4f}", "A3", ln, "hb_U", c) + "]",
                                num(r["R_hat"], "{:.3f}", "A3", ln, "R_hat", c), CODE[r["outcome"]]]) + " \\\\")
    L += longtable("p{3.0cm}p{0.6cm}lllllp{0.6cm}", "division & ind. & $\\alpha$ & split & $A$ & $[L,U]$ & $R$ & out.", body,
                   "Every clear $\\to$ rain cell with a selected threshold (frame = division by frame; scene (i)/(ii) = division by recorded scene with the frame / scene as unit).", "tab:A3")
    body = []
    for ln, r in numbered("A4"):
        c = f"frames {r['setting']} {r['condition']} seed {r['seed']}"
        body.append(" & ".join([tex(r["setting"]), tex(r["condition"]), r["seed"], num(r["frames_select"], None, "A4", ln, "frames_select", c),
                                num(r["frames_eval"], None, "A4", ln, "frames_eval", c)]) + " \\\\")
    L += longtable("p{4.6cm}p{3.2cm}lll", "setting & condition & split & selection frames & test frames", body,
                   "Frames per condition in the selection and test parts (division by frame).", "tab:A4")
    body = []
    for ln, r in numbered("A5"):
        c = f"tau* {r['setting']} {r['indicator']} {r['alpha']} {r['condition']} seed {r['seed']}"
        if r["outcome"] == "no common threshold":
            body.append(" & ".join([tex(r["setting"]), tex(r["indicator"]), alpha_tex(r["alpha"]), tex(r["condition"]), r["seed"], "", "", "", "-", "", ""]) + " \\\\")
            continue
        body.append(" & ".join([tex(r["setting"]), tex(r["indicator"]), alpha_tex(r["alpha"]), tex(r["condition"]), r["seed"],
                                num(r["tau_star"], "{:.4f}", "A5", ln, "tau_star", c), num(r["A_hat"], "{:.4f}", "A5", ln, "A_hat", c),
                                "[" + num(r["hb_L"], "{:.4f}", "A5", ln, "hb_L", c) + ", " + num(r["hb_U"], "{:.4f}", "A5", ln, "hb_U", c) + "]",
                                CODE[r["outcome"]], num(r["R_tau_star"], "{:.3f}", "A5", ln, "R_tau_star", c),
                                num(r["G"], "{:.3f}", "A5", ln, "G", c) if r.get("G") not in ("", None) else ""]) + " \\\\")
    L += longtable("p{2.9cm}p{0.6cm}llllllllll", "setting & ind. & $\\alpha$ & condition & split & $\\tau^*$ & $A$ & $[L,U]$ & out. & $R(\\tau^*)$ & $G$", body,
                   "The common threshold $\\tau^*$ on the test part of each distance condition, with the retention gap $G=R(\\tau_c)-R(\\tau^*)$.", "tab:A5")
    return L


def sec_m8():
    rep = (ROOT / F["m8rep"]).read_text().strip()
    SOURCES.append({"context": "m8 reproduction check", "value_printed": rep, "value_recorded": rep, "file": F["m8rep"], "row_or_line": 1, "column": ""})
    body = []
    for ln, r in numbered("m8cnt"):
        src, dst = r["direction"].split(" -> ")
        if src == dst:
            continue
        c = f"m8 {r['setting']} {r['unit']} {r['indicator']} {r['alpha']} {r['direction']}"
        body.append(" & ".join([tex(r["setting"]), tex(r["unit"]), tex(r["indicator"]), alpha_tex(r["alpha"]), tex(r["direction"]).replace("-$>$", "$\\to$").replace("->", "$\\to$")] +
                               [num(r[k], None, "m8cnt", ln, k, c) for k in ("applicable", "not_applicable", "not_determined", "no_threshold")]) + " \\\\")
    L = ["\\section{Division of KITTI by recorded drive}\\label{sec:m8}",
         "The KITTI object frames were mapped to their recorded drives with the mapping files of the KITTI object development kit; the "
         "3{,}769 validation frames come from 45 drives. Before the division by drive, the "
         f"division by frame was run again with the same code and compared with the recorded results: ``{tex(rep)}''. Variant (i) keeps "
         "the frame as the unit of the selection test and of the interval; variant (ii) uses the drive, with the mean of the per-frame "
         "false acceptance proportions over the drive's frames in the condition as its loss. In the change of dataset and detector the "
         "nuScenes side is divided by recorded scene.", ""]
    L += longtable("p{3.0cm}p{0.9cm}p{0.6cm}lp{2.6cm}llll", "setting & unit & ind. & $\\alpha$ & transfer & A & N & ? & -", body,
                   "Outcome counts over the five splits, division by recorded drive (KITTI rule).", "tab:m8")
    body = []
    for ln, r in numbered("m8drv"):
        c = f"m8 drives {r['setting']} seed {r['seed']} {r['part']} {r['condition']}"
        body.append(" & ".join([tex(r["setting"]), r["seed"], r["part"], tex(r["condition"]), num(r["drives"], None, "m8drv", ln, "drives", c),
                                num(r["frames"], None, "m8drv", ln, "frames", c)]) + " \\\\")
    L += longtable("p{4.6cm}llp{1.6cm}ll", "setting & split & part & condition & drives & frames", body,
                   "Drives and frames with a car detection per part and condition, division by recorded drive.", "tab:m8drv")
    return L


def sec_posthoc():
    """Post-hoc analyses (07_analysis/code/seq_ratio, seq-0.2), read from their result files."""
    gate = (ROOT / F["phgate"]).read_text().strip()
    SOURCES.append({"context": "post-hoc reproduction check", "value_printed": tex(gate), "value_recorded": gate, "file": F["phgate"],
                    "row_or_line": 1, "column": ""})
    L = ["\\section{Post-hoc analyses}\\label{sec:posthoc}",
         "\\textbf{Post-hoc.} The analyses of this section were added after the parameters of the study were fixed and after the "
         "outcomes were known. They are not part of the predictions fixed in advance. The limits 0.05 and 0.1 are exploratory and "
         "are not safety targets.", "",
         "\\emph{Method A} tests the per-frame target $A_c(\\tau)=\\mathrm{E}[a_f(\\tau)\\mid f\\in c]\\le\\alpha$ with the recorded "
         "sequence (KITTI drive, nuScenes scene) as the independent unit. For sequence $s$, $N_s$ is the number of its frames in "
         "condition $c$ and $S_s(\\tau)$ the sum of $a_f(\\tau)$ over these frames. For independent sequences "
         "$A_c=\\mathrm{E}[S]/\\mathrm{E}[N]$, so with $N_{\\max}(c)$, the largest $N_s$ over all validation sequences of $c$, the "
         "value $Y_s=(S_s-\\alpha N_s+\\alpha N_{\\max})/N_{\\max}$ lies in $[0,1]$ and $\\mathrm{E}[Y]\\le\\alpha$ holds exactly "
         "when $A_c\\le\\alpha$. Selection and test are those of the paper (Hoeffding--Bentkus, $\\delta=0.05$, bounds at "
         "$\\delta/2$) with $Y_s$ as the loss of a unit, on the division by recorded sequence (Sect.~\\ref{sec:m7}, "
         "Sect.~\\ref{sec:m8}). \\emph{Method B} repeats the test with the betting confidence interval of Waudby-Smith and "
         "Ramdas (hedged capital process, each side at $\\delta/2$) and keeps the thresholds of Method A. Before any new number, "
         f"the recorded results were recomputed: ``{tex(gate)}''.", ""]
    d = defaultdict(dict)
    for ln, r in numbered("phsum"):
        d[(r["pair"], r["direction"], r["own_condition"], r["indicator"], float(r["alpha"]))][r["method"]] = (ln, r)
    keys = ("applicable", "not applicable", "not determined", "no threshold selected")
    body = []
    for k in sorted(d, key=lambda k: (k[0], k[2], k[1], k[3], ALPHA_ORDER.index(k[4]))):
        if all(d[k][m][1]["no threshold selected"] == "5" for m in d[k]):
            continue
        cells = []
        for m in ("A", "B"):
            ln, r = d[k][m]
            cells += [num(r[c], None, "phsum", ln, c, f"post-hoc {m} {k}") for c in keys]
        body.append(" & ".join([tex(k[0]), tex(k[1]).replace("->", "$\\to$"), "yes" if k[2] == "True" else "",
                                tex(k[3]), alpha_tex(k[4])] + cells) + " \\\\")
    L += longtable("p{2.8cm}p{2.3cm}p{0.5cm}p{0.6cm}lllllllll",
                   "pair & transfer & own & ind. & $\\alpha$ & A: A & A: N & A: ? & A: -- & B: A & B: N & B: ? & B: --", body,
                   "Post-hoc. Outcome counts over the five splits, Methods A and B (A applicable, N not applicable, ? not determined, "
                   "-- no threshold selected; own: threshold used in its own condition of selection). Rows in which neither method "
                   "selected a threshold on any split are not listed.", "tab:posthoc")
    body = []
    for ln, r in numbered("phau"):
        c = f"post-hoc AUROC {r['pair']} {r['quantity']}"
        body.append(" & ".join([tex(r["pair"]), tex(r["indicator"]), tex(r["quantity"]), num(r["point"], "{:.3f}", "phau", ln, "point", c),
                                "[" + num(r["lo95"], "{:.3f}", "phau", ln, "lo95", c) + ", " + num(r["hi95"], "{:.3f}", "phau", ln, "hi95", c) + "]",
                                tex(r["resampling"])]) + " \\\\")
    L += longtable("p{3.4cm}lp{4.6cm}llp{1.8cm}", "pair & ind. & quantity & AUROC & 95\\,\\% interval & resampling", body,
                   "Post-hoc. AUROC of the three pairs of the separation figure on the test part of split 0, with 95\\,\\% "
                   "percentile bootstrap intervals over recorded sequences (2{,}000 replicates). Near/far: drives resampled once for "
                   "both conditions; clear/rain and the two datasets: sequences resampled within each condition.", "tab:posthoc_auroc")
    body = []
    for ln, r in numbered("phns"):
        if r["split"] != "0":
            continue
        c = f"post-hoc N_s {r['pair']} {r['condition']}"
        body.append(" & ".join([tex(r["pair"]), tex(r["condition"])] +
                               [num(r[k], None, "phns", ln, k, c) for k in ("sequences", "N_s_min", "N_s_median", "N_s_max")]) + " \\\\")
    L += longtable("p{4.6cm}p{1.6cm}llll", "pair & condition & sequences & min $N_s$ & median $N_s$ & max $N_s$", body,
                   "Post-hoc. Frames per sequence in each condition (sequences with $N_s\\ge1$, all parts, split 0).", "tab:posthoc_ns")
    ep = (ROOT / F["phep"]).read_text(encoding="utf-8").splitlines()
    keep = [(i + 1, l.strip()) for i, l in enumerate(ep) if "NUM_EPOCHS:" in l or l.strip().startswith(("Train:", "seed "))]
    for ln, l in keep:
        SOURCES.append({"context": "post-hoc epoch check", "value_printed": l, "value_recorded": l, "file": F["phep"], "row_or_line": ln, "column": ""})
    L += ["\\paragraph{Training epochs of the nuScenes members (post-hoc check).} The training configurations of the nuScenes "
          "ensemble members set 20 epochs, but training ended after epoch 10: each training log reaches the start of epoch 11, "
          "and the checkpoints that inference loaded (\\texttt{latest\\_model.pth}) stop shortly before the end of epoch 10. The "
          "nuScenes members were therefore trained for about 10 epochs, not 20. The configuration of seed 5 belongs to no ensemble member; inference used the members of seeds 1 to 4. Lines of the check (\\path{" + F["phep"] + "}):", "",
          "{\\scriptsize\\begin{verbatim}"] + [l for _, l in keep] + ["\\end{verbatim}}", ""]
    return L


def sec_intro():
    return ["\\section{How to read this document}\\label{sec:intro}",
            "This document lists the recorded results behind the paper in full: the outcome of every cell on every split, the "
            "intervals and retention behind each outcome, the counts behind the KITTI rule, the division by recorded sequence, "
            "the predictions fixed in advance, the selection of the frames shown in Fig.~1 and the post-hoc analyses. Nothing in "
            "it is recomputed: \\path{tools/supplementary/make_supplementary.py} reads every number from a file of the "
            "repository and lists it with file, line or row, and column in \\path{docs/supplementary/supplementary_sources.csv}; "
            "its option \\texttt{-{}-check} re-reads each listed value and compares it with the print.", "",
            "\\paragraph{One cell.} A threshold $\\tau_c$ is selected in the \\emph{condition of selection} $c$ (columns "
            "\\texttt{established} or \\texttt{source} in the files) on the selection part, at limit $\\alpha$ and error probability "
            "$\\delta=0.05$, and tested on the test part of the \\emph{condition of use} $c'$ (\\texttt{applied} or \\texttt{target}). "
            "The one-sided Hoeffding--Bentkus bounds $L$ and $U$ of the false acceptance proportion (FAP) $A_{c'}(\\tau_c)$, each at "
            "$\\delta/2$, decide the outcome: \\textbf{A} applicable ($U\\le\\alpha$), \\textbf{N} not applicable ($L>\\alpha$), "
            "\\textbf{?} not determined (otherwise), \\textbf{-} no threshold selected in $c$. A code string such as "
            "\\texttt{A??NN} gives the outcome on splits 0 to 4 from left to right. A cell with $c'=c$ tests a threshold in its own "
            "condition of selection and checks the selection; a cell with $c'\\ne c$ is a \\emph{transfer}.", "",
            "\\paragraph{Limits.} The target limits $10^{-2}$, $10^{-3}$ and $10^{-4}$ were fixed before the first run. The limits "
            "0.05 and 0.1 were fixed at the same time as exploratory limits, to show which outcomes the data can decide; they are "
            "not safety targets. No threshold could be selected at $10^{-3}$ or $10^{-4}$ in any condition.", "",
            "\\paragraph{Terms and files.} The repository's \\path{docs/glossary.md} defines every term and maps it to the column "
            "names of the files, which keep the names they were written with (for example \\texttt{applies} for applicable, "
            "\\texttt{eval} for the test part). Run names m1 to m8 identify the scripts in \\path{experiments/} and the folders in "
            "\\path{results/}. Distance conditions are assigned per detection (boundary: median distance of the car detections in the "
            "grid part); weather and dataset are assigned per frame. KITTI results apply the KITTI rule unless stated otherwise.", ""]


def sec_bins():
    lines = (ROOT / F["bins"]).read_text().splitlines()
    tv = json.load(open(ROOT / F["tfv"]))
    cutK = num(tv["a_distance"]["KITTI_rule"]["cut_m"], "{:.3f}", "tfv", "a_distance.KITTI_rule.cut_m", "", "bins KITTI cut")
    cutN = num(tv["a_distance"]["nuScenes"]["cut_m"], "{:.3f}", "tfv", "a_distance.nuScenes.cut_m", "", "bins nuScenes cut")
    facts = (ROOT / F["fig1facts"]).read_text().splitlines()
    lnK = next(i + 1 for i, s in enumerate(facts) if "threshold selected at near distance" in s)
    tauK = num(re.search(r"([0-9.]+)$", facts[lnK - 1]).group(1), None, "fig1facts", lnK, "", "bins KITTI tau_near")
    m3r = [(ln, r) for ln, r in numbered("m3") if r["iou"] == "A_iou0.5" and r["objects"] == "car" and r["cut_q"] == "0.5"
           and r["indicator"] == "u_s" and r["seed"] == "0" and float(r["alpha"]) == 0.1 and r["established"] == "near"
           and r["applied"] == "near"]
    tauN = num(m3r[0][1]["tau"], "{:.5f}", "m3", m3r[0][0], "tau", "bins nuScenes tau_near")
    L = ["\\section{Accepted detections per distance bin}\\label{sec:bins}",
         "Car detections of the test part of split 0 accepted by the threshold selected at near distance "
         "($u_{\\mathrm{s}}$, exploratory limit 0.1), per 5\\,m bin of detection distance, divided into correct and wrong. "
         f"KITTI with the KITTI rule: boundary {cutK}\\,m, $\\tau_{{\\mathrm{{near}}}}={tauK}$; nuScenes: boundary {cutN}\\,m, "
         f"$\\tau_{{\\mathrm{{near}}}}={tauN}$. Among the accepted detections the share of wrong ones grows with distance also below "
         "the near/far boundary, so the not applicable outcomes after transfers into far distance are not explained by the position "
         "of the boundary alone (split 0, $u_{\\mathrm{s}}$, 0.1). Shares in parentheses rest on fewer than 30 accepted detections. "
         f"Source: \\path{{{F['bins']}}}, the console output of \\path{{tools/figures/make_figures.py causes}}, which also drew "
         "Fig.~\\ref{fig:causes}.", ""]
    for ds, head in (("KITTI", "==== causes KITTI"), ("nuScenes", "==== causes nuScenes")):
        i = lines.index(head)
        body = []
        for j in range(i + 1, len(lines)):
            m = re.match(r"bin\s+(\S+)\s+m: accepted correct\s+(\d+), wrong\s+(\d+), share wrong \(?([0-9.]+)", lines[j])
            if lines[j].startswith("make_figures"):
                break
            if m:
                paren = "(" in lines[j]
                c = f"bins {ds} {m.group(1)}"
                sh = num(m.group(4), None, "bins", j + 1, "share wrong", c)
                body.append(f"{m.group(1)} & {num(m.group(2), None, 'bins', j + 1, 'accepted correct', c)} & "
                            f"{num(m.group(3), None, 'bins', j + 1, 'wrong', c)} & {'(' + sh + ')' if paren else sh} \\\\")
        L += ["\\begin{table}[H]\\centering\\small", f"\\caption{{{ds}: accepted car detections per 5\\,m bin under $\\tau_{{\\mathrm{{near}}}}$.}}",
              "\\begin{tabular}{lrrr}\\toprule bin (m) & accepted correct & accepted wrong & share wrong \\\\ \\midrule"] + body + \
             ["\\bottomrule\\end{tabular}\\end{table}", ""]
    L += fig("figures/fig_causes_kitti.pdf", "KITTI distance, spatial indicator, KITTI rule, split 0, threshold selected at near "
             "distance at the exploratory limit 0.1: (a) separation per distance condition, (b) indicator distributions, (c) accepted "
             "detections per 5\\,m bin with the share of wrong ones among them (counts in the table above).", "fig:causes")
    return L


def sec_sequence():
    """Division by recorded sequence: nuScenes scenes (m7) and KITTI drives (m8)."""
    repro7 = (ROOT / F["m7repro"]).read_text().strip()
    SOURCES.append({"context": "m7 reproduction check", "value_printed": tex(repro7), "value_recorded": repro7, "file": F["m7repro"],
                    "row_or_line": 1, "column": ""})
    m7 = numbered("m7")
    V = (("frame", "frame"), ("scene_frame_unit", "(i)"), ("scene_scene_unit", "(ii)"))
    d = defaultdict(dict)
    for ln, r in m7:
        d[(r["setting"], r["indicator"], float(r["alpha"]), r["established"], r["applied"])].setdefault(r["variant"], {})[int(r["seed"])] = (ln, r)
    body = []
    for k in sorted(d, key=lambda k: (k[0], k[1], ALPHA_ORDER.index(k[2]), k[3], k[4])):
        if all(d[k][v][s][1]["outcome"] == "no threshold established" for v, _ in V for s in range(5)):
            continue
        cells = []
        for v, lab in V:
            cells.append("\\texttt{" + "".join(CODE[num(d[k][v][s][1]["outcome"], None, "m7", d[k][v][s][0], "outcome",
                                                          f"m7 {lab} {k} seed {s}")] for s in range(5)) + "}")
        rr = []
        for s in range(5):
            ln, r = d[k]["scene_scene_unit"][s]
            rr.append("--" if r["R_hat"] in ("", "None") else num(r["R_hat"], "{:.2f}", "m7", ln, "R_hat", f"m7 (ii) R {k} seed {s}"))
        setting = {"distance": "distance", "rain": "weather"}[k[0]]
        body.append(" & ".join([setting, tex(k[1]), alpha_tex(k[2]), f"{k[3]}$\\to${k[4]}"] + cells + [" ".join(rr)]) + " \\\\")
    L = ["\\section{Division by recorded sequence}\\label{sec:m7}",
         "Frames of one recorded sequence share objects, weather and road, so they are not independent draws. The analysis was "
         "therefore repeated with the grid, selection and test parts drawn by recorded sequence: nuScenes scenes (m7, 150 scenes "
         "in the validation set) and KITTI drives (m8, 45 drives in the validation frames). The sequences are permuted by the split "
         "function of the division by frame, with the same seeds 0 to 4 and the same fractions, and every frame takes the part of "
         "its sequence. Limits, $\\delta$, candidate thresholds and the boundary rule are unchanged. This analysis was added after "
         "the parameters had been fixed.", "",
         "\\paragraph{Variants.} \\emph{Frame}: division by frame, as recorded. \\emph{Variant (i)}: division by recorded sequence, "
         "the frame stays the unit of the selection test and of the HB bounds. \\emph{Variant (ii)}: the same division with the "
         "sequence as the unit. The loss of sequence $s$ in condition $c$ is "
         "$\\ell_s(\\tau)=\\frac{1}{|F_{s,c}|}\\sum_{f\\in F_{s,c}}a_f(\\tau)$, where $F_{s,c}$ are the frames of $s$ that hold a car "
         "detection of $c$; a sequence without accepted detections has loss 0, and each sequence has equal weight. Retention is a "
         "sum over detections and is the same for both units. The post-hoc Method A (Section~\\ref{sec:posthoc}) keeps the "
         "per-frame target exactly with the sequence as the unit.", "",
         f"\\paragraph{{Reproduction check.}} Before the division by scene, the division by frame was rerun with the scripts of the "
         f"scene runs and compared with the recorded results in every row and column: ``{tex(repro7)}'' "
         f"(\\path{{{F['m7repro']}}}).", ""]
    L += longtable("lllllllp{3.6cm}", "pair & ind. & $\\alpha$ & cell & frame & (i) & (ii) & $R$ (ii), splits 0--4", body,
                   "nuScenes, division by recorded scene: outcome per split for the division by frame and variants (i) and (ii), "
                   "and the retention of variant (ii) (--: no threshold). Cells without a selected threshold in any variant and "
                   "split are not listed.", "tab:m7c")
    summ = (ROOT / F["m7summ"]).read_text().splitlines()
    i1 = next(i for i, s in enumerate(summ) if s.startswith("split | grid"))
    sc = []
    for j in range(i1 + 1, len(summ)):
        if "|" not in summ[j]:
            break
        c = [x.strip() for x in summ[j].split("|")]
        SOURCES.append({"context": f"m7 scenes per part, split {c[0]}", "value_printed": " ; ".join(c[1:]), "value_recorded": "",
                        "file": F["m7summ"], "row_or_line": j + 1, "column": ""})
        sc.append(" & ".join(tex(x).replace(" / ", "\\,/\\,") for x in c) + " \\\\")
    L += ["\\begin{table}[H]\\centering\\scriptsize",
          f"\\caption{{nuScenes scenes per condition and part under the division by scene, per split; in brackets the frames with a "
          f"car detection (\\texttt{{{tex(F['m7summ'])}}}, l.~{i1 + 2}--{i1 + 1 + len(sc)}). A scene counts for near or far if it holds a car "
          "detection of that condition; most scenes count for both.}",
          "\\begin{tabular}{lllllll}\\toprule split & grid / sel. / test & boundary & near sel. / test & far sel. / test & "
          "clear sel. / test & rain sel. / test \\\\ \\midrule"] + sc + ["\\bottomrule\\end{tabular}\\end{table}", ""]
    L += fig("figures/fig_scenesplit.pdf", "nuScenes: outcomes per cell on the five splits for the division by frame, by recorded "
             "scene with the frame as unit, and by recorded scene with the scene as unit (drawn by "
             "\\texttt{tools/figures/supplementary/supplementary\\_figures.py} from \\texttt{results/m7\\_scene\\_split/m7\\_scene\\_split.csv}).",
             "fig:scenesplit")
    L += sec_m8()
    L += fig("figures/fig_drivesplit.pdf", "KITTI with the KITTI rule: outcomes per cell on the five splits for the division by "
             "frame, by recorded drive with the frame as unit, and by recorded drive with the drive as unit. In the change of dataset "
             "and detector the nuScenes side is divided by recorded scene.", "fig:drivesplit")
    return L


def sec_predictions():
    pred = (ROOT / F["pred"]).read_text(encoding="utf-8").splitlines()
    lfz = next(i + 1 for i, s in enumerate(pred) if "FROZEN 2026-10-01" in s)
    titles = {p: next((i + 1, s) for i, s in enumerate(pred) if s.startswith(f"**{p}.")) for p in ("P1", "P2", "P3", "P4", "P5")}
    rec = {"P1": ("not tested", "classes C1 and C2 were measured only together as recorded rain, and C3 was not measured, so the "
                  "comparison the prediction names cannot be made", "--"),
           "P2": ("not tested", "how to compare the spread of AUROC with the spread of the FAP in units of interval width was not "
                  "fixed in advance; the comparison was not computed", "--"),
           "P3": ("held", "the retention gap $G$ of the common threshold lies above zero and below the retention at the threshold "
                  "of the condition (KITTI, $u_{\\mathrm{s}}$, split 0)", "\\path{results/supporting_analyses/common_threshold_outcomes.csv}"),
           "P4": ("held", "nuScenes$\\to$KITTI is not applicable on all splits for $u_{\\mathrm{s}}$ at every limit with a threshold, "
                  "KITTI$\\to$nuScenes is applicable; near$\\to$far and far$\\to$near differ in the same way at 0.1",
                  "\\path{results/m6_five_splits/B_shift_seeds_protocol.csv}"),
           "P5": ("held", "cells with the outcome not determined occur in every pair of conditions",
                  "\\path{docs/results.md} (outcome table) and its source files")}
    L = ["\\section{Predictions fixed in advance and their outcomes}\\label{sec:predictions}",
         f"The predictions P1 to P5 and the outcomes that would count as their failure were fixed on 2026-10-01, before the first "
         f"evaluation run (\\path{{{F['pred']}}}, l.~{lfz}). The outcome of each prediction, the reason and the evidence file are "
         "listed below; \\path{docs/study_protocol/outcomes_and_deviations.md} also lists the deviations from the fixed protocol.", "",
         "\\begin{table}[H]\\centering\\small\\caption{Predictions and their outcomes.}",
         "\\begin{tabular}{p{3.9cm}p{1.5cm}p{6.0cm}p{4.0cm}}\\toprule",
         "prediction & outcome & reason & evidence \\\\ \\midrule"]
    for p, (o, why_, ev) in rec.items():
        ln, t = titles[p]
        name = re.sub(r"\*\*", "", t).strip()
        SOURCES.append({"context": f"prediction {p} title", "value_printed": tex(name).replace(chr(34), chr(39) * 2), "value_recorded": name, "file": F["pred"], "row_or_line": ln, "column": ""})
        L.append(f"{tex(name).replace(chr(34), chr(39) * 2)} (l.~{ln}) & {o} & {why_} & {ev} \\\\")
    L += ["\\bottomrule\\end{tabular}\\end{table}", ""]
    return L


def sec_frames():
    """Selection of the two frames of Fig. 1 of the paper (the figure itself shows dataset images and is not published here)."""
    facts = (ROOT / F["fig1facts"]).read_text().splitlines()
    lines = []
    for i, s in enumerate(facts):
        s2 = s.strip()
        if not s2 or s2.startswith("v25_fig1") or s2.startswith("selected from release/"):
            continue
        SOURCES.append({"context": "Fig. 1 facts", "value_printed": s2, "value_recorded": s2, "file": F["fig1facts"], "row_or_line": i + 1, "column": ""})
        lines.append(s2)
    cand = numbered("fig1b")
    body = []
    for ln, r in cand:
        c = f"Fig. 1 nuScenes candidate rank {r['rank']}"
        body.append(" & ".join([num(r["rank"], None, "fig1b", ln, "rank", c), "\\texttt{" + num(r["token"][:8], None, "fig1b", ln, "token", c) + "}",
                                num(r["where"], None, "fig1b", ln, "where", c), num(r["dist"], "{:.1f}", "fig1b", ln, "dist", c),
                                num(r["u_e"], "{:.4f}", "fig1b", ln, "u_e", c), num(r["iou_nearest_car"], "{:.3f}", "fig1b", ln, "iou_nearest_car", c),
                                num(r["acc_correct"], None, "fig1b", ln, "acc_correct", c), num(r["rejected"], None, "fig1b", ln, "rejected", c)]) + " \\\\")
    L = ["\\section{Frames shown in Fig.~1}\\label{sec:frames}",
         "Fig.~1 of the paper shows one KITTI frame and one nuScenes frame in which the transferred threshold accepts a wrong "
         "detection that the threshold selected in the condition of use rejects (split 0, exploratory limit 0.1). The figure shows "
         "dataset images and is not part of the repository; its facts are recorded in "
         f"\\path{{{F['fig1facts']}}} and listed here. Candidates for the nuScenes frame are the rain frames of the test part of split 0 "
         "with exactly one accepted wrong car detection whose $u_{\\mathrm{e}}$ lies between the threshold selected in rain and the "
         "transferred clear-weather threshold (both at 0.1) and whose box lies inside the front camera image; the yaw of its member "
         "boxes spans at most 15 degrees; its 3D IoU with every annotation is 0 or its IoU with the nearest annotated car is below 0.3; "
         "the frame holds 3 to 8 accepted correct and at most 3 rejected car detections, all within 50\\,m forward. Ranking: IoU 0 "
         "with all annotations first, then the larger height of the wrong box in the image, then more accepted correct detections "
         f"(\\path{{{F['fig1b']}}}). Rank 1 was not used, because its wrong detection lies 1.9\\,m below an annotated car "
         "on a ramp at the same position in the bird's-eye view, so its overlap of 0 comes from the height and not from an empty "
         "location. The chosen wrong detection (rank 2) lies 0.26\\,m from an annotated car with a 3D IoU of 0.265: a mislocalised "
         "detection of an annotated car, wrong under the IoU 0.5 rule. The KITTI frame 005345 was chosen by the authors from the "
         "ranked candidates in \\path{results/supporting_analyses/frame_candidates_ranked.csv}. The scripts are in "
         "\\path{tools/figures/paper/frame_figure/}.", "",
         "{\\tiny\\begin{verbatim}"] + lines + ["\\end{verbatim}}", ""]
    L += longtable("llllllll", "rank & token & scene & distance (m) & $u_{\\mathrm{e}}$ & IoU nearest car & accepted correct & rejected",
                   body, "Candidate nuScenes frames for Fig.~1(b).", "tab:fig1b")
    return L


def check():
    """Re-read every CSV-sourced value at its row and column; search every printed value in the .tex."""
    src = list(csv.DictReader(open(OUT / f"{NAME}_sources.csv", encoding="utf-8")))
    texs = (OUT / f"{NAME}.tex").read_text(encoding="utf-8")
    cache, bad, n = {}, [], 0
    for s in src:
        if s["file"].endswith(".csv") and s["row_or_line"].isdigit():
            f = s["file"]
            cache.setdefault(f, (ROOT / f).read_text(encoding="utf-8").splitlines())
            hdr = next(csv.reader([cache[f][0]])); row = next(csv.reader([cache[f][int(s["row_or_line"]) - 1]]))
            rec = row[hdr.index(s["column"])]
            p = s["value_printed"]
            try:
                ok = abs(float(rec) - float(p)) <= 0.5 * 10 ** -(len(p.split(".")[1]) if "." in p else 0) + 1e-12
            except ValueError:
                ok = rec == p or rec.startswith(p)
            n += 1
            if not ok:
                bad.append((s, rec))
        if s["value_printed"] and s["column"] != "outcome" and ";" not in s["value_printed"] and s["value_printed"] not in texs:
            bad.append((s, "not in tex"))
    print(f"checked {n} CSV-sourced values against their rows; {len(src)} entries in total; problems: {len(bad)}")
    for b in bad[:10]:
        print(b)
    return not bad


def main():
    ap = argparse.ArgumentParser(description=VERSION); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        sys.exit(0 if check() else 1)
    hashes = {k: sha(v) for k, v in F.items()}
    body = (sec_intro() + sec_classes() + sec_outcomes() + sec_per_split_A() + sec_rule() + sec_bins() + sec_sequence() +
            sec_review_tables() + sec_posthoc() + sec_predictions() + sec_frames())
    files = sorted(set(F.values()))
    src_tab = ["\\section{Source files}",
               f"Every number in this document is read by \\path{{tools/supplementary/make_supplementary.py}} ({VERSION}) "
               "from the files below and listed with file, line or row, and column in "
               f"\\path{{docs/supplementary/{NAME}_sources.csv}}. CSV rows are numbered by file line (header = line 1).", "",
               "{\\scriptsize\\begin{longtable}{p{7.6cm}p{7.6cm}}\\toprule file & SHA-256 \\\\ \\midrule"]
    for v in files:
        src_tab.append(f"\\path{{{v}}} & {{\\tiny\\texttt{{{sha(v)}}}}} \\\\")
    src_tab += ["\\bottomrule\\end{longtable}}", ""]
    doc = ["% Generated by tools/supplementary/make_supplementary.py (" + VERSION + "). Do not edit by hand; edit the generator.",
           "\\documentclass[10pt,a4paper]{article}", "\\usepackage[T1]{fontenc}", "\\usepackage[utf8]{inputenc}",
           "\\usepackage[margin=2.0cm]{geometry}", "\\usepackage{booktabs,longtable,float,graphicx}", "\\usepackage[hyphens]{url}",
           "\\usepackage{hyperref}",
           "\\title{Supplementary Material\\\\[4pt]\\large Uncertainty Evaluation to Support Safety of the Intended Functionality "
           "Analysis for Determining the Applicability of Performance Targets Across Triggering Conditions in ML-Based "
           "LiDAR Object Detection}", "\\author{Milin Patel \\and Rolf Jung}", "\\date{}", "\\begin{document}", "\\maketitle",
           "\\tableofcontents", ""] + body + src_tab + ["\\end{document}"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NAME}.tex").write_text("\n".join(doc) + "\n", encoding="utf-8")
    with open(OUT / f"{NAME}_sources.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["context", "value_printed", "value_recorded", "file", "row_or_line", "column"])
        w.writeheader(); w.writerows(SOURCES)
    print(f"{VERSION}: {len(SOURCES)} numbers logged; wrote docs/supplementary/{NAME}.tex and {NAME}_sources.csv")


if __name__ == "__main__":
    main()

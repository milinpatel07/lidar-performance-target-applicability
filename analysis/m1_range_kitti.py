#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m1_range_kitti.py

Milestone 1 of the paper on the applicability of acceptance criteria across
triggering conditions. First look at one pair of classes: NEAR and FAR range
among KITTI consensus detections.

Question: a rejection threshold is established in one range class by a
finite-sample risk-control procedure (Learn then Test, Hoeffding-Bentkus
p-value, fixed sequence). Does the false acceptance proportion stay at or
below alpha when the same threshold is applied in the other class?

Needs numpy only. Box overlap uses shapely when installed and a built-in exact clipper otherwise.

Inputs are read-only (RUM repository, mounted at --rum):
  detections/kitti_v2/scored_val.pkl
  detections/kitti_v2/frame_errors_cache.pkl
  third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl
Outputs are written only below --out.

Usage (inside the container):
  python3 m1_range_kitti.py --selftest
  python3 m1_range_kitti.py --rum /rum --out /work/m1_range_kitti/results

Indicator: the saved per-detection value u of the RUM pipeline (a weighted
sum of box spread and confidence spread). It is NOT yet mapped to the
indicators u_s and u_e of the paper. Numbers from this script are therefore
a pipeline validation and feasibility look, not paper numbers.
"""
import argparse
import csv
import hashlib
import json
import math
import pickle
import platform
import sys
import time
from pathlib import Path

import numpy as np

SCRIPT_VERSION = "m1-0.2"

# ----------------------------------------------------------------------------
# Configuration. Every value is reported in provenance.json. Changing a value
# after seeing results is a deviation and has to be logged.
# ----------------------------------------------------------------------------
CFG = {
    "delta": 0.05,
    "alphas_frozen": [1e-2, 1e-3, 1e-4],          # from the frozen predictions
    "alphas_exploratory": [5e-2, 1e-1],            # outside the frozen sweep, labelled exploratory
    "frac_grid": 0.10,                             # frames used only for the u-grid and the range cut
    "frac_select": 0.45,                           # frames for threshold selection; evaluation gets the rest
    "grid_levels": [round(0.01 * i, 2) for i in range(1, 101)],
    "cut_quantiles": [0.50, 0.25, 0.75],           # range cut as quantile of detection range in the grid split
    "n_boot": 2000,
    "seeds": [0, 1, 2, 3, 4],
    "iou_settings": {
        "A_iou0.5": {"Car": 0.5, "Pedestrian": 0.5, "Cyclist": 0.5},   # as in the RUM pipeline
        "B_car0.7": {"Car": 0.7, "Pedestrian": 0.5, "Cyclist": 0.5},   # KITTI benchmark thresholds
    },
    "object_sets": {"Car": ["Car"], "All": ["Car", "Pedestrian", "Cyclist"]},
    "primary": {"iou": "A_iou0.5", "cut_q": 0.50, "objects": "Car", "seed": 0},
    "verify_setting": "A_iou0.5",
}
CLASS_NAMES = ["near", "far"]


# ----------------------------------------------------------------------------
# Box matching. rotated_iou_3d and load_gt are copied from
# scripts/kitti_v2/03_compute_frame_errors.py so that labels follow the same rules.
# ----------------------------------------------------------------------------
BEV_BACKEND = "auto"      # "auto" (shapely if installed, else the built-in clipper), "shapely" or "clip"
_RESOLVED_BACKEND = None


def _resolve_backend():
    global _RESOLVED_BACKEND
    if _RESOLVED_BACKEND is None:
        if BEV_BACKEND == "auto":
            try:
                import shapely.geometry  # noqa: F401
                _RESOLVED_BACKEND = "shapely"
            except ImportError:
                _RESOLVED_BACKEND = "clip"
        else:
            _RESOLVED_BACKEND = BEV_BACKEND
    return _RESOLVED_BACKEND


def _corners_bev(box):
    """Corner points of the bird's-eye-view rectangle (same construction as the RUM pipeline)."""
    x, y, _, l, w, _, ry = box[:7]
    c, s = float(np.cos(ry)), float(np.sin(ry))
    local = np.array([[l / 2, w / 2], [l / 2, -w / 2],
                      [-l / 2, -w / 2], [-l / 2, w / 2]])
    R = np.array([[c, -s], [s, c]])
    return local @ R.T + np.array([x, y])


def _poly_area(p):
    """Signed polygon area, positive for counter-clockwise order."""
    a, n = 0.0, len(p)
    for i in range(n):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return 0.5 * a


def _line_hit(sx, sy, ex, ey, ax, ay, bx, by):
    """Point where the segment s->e meets the infinite line a->b."""
    dx, dy = ex - sx, ey - sy
    fx, fy = bx - ax, by - ay
    t = -(fx * (sy - ay) - fy * (sx - ax)) / (fx * dy - fy * dx)
    return (sx + t * dx, sy + t * dy)


def _clip_area(subject, clip):
    """Area of the intersection of two convex polygons (Sutherland-Hodgman clipping).
    Both polygons are lists of (x, y). Exact up to floating-point rounding."""
    sa, ca = _poly_area(subject), _poly_area(clip)
    if sa == 0.0 or ca == 0.0:
        return 0.0
    out = list(subject) if sa > 0 else list(subject[::-1])
    cl = list(clip) if ca > 0 else list(clip[::-1])
    for i in range(len(cl)):
        ax, ay = cl[i]
        bx, by = cl[(i + 1) % len(cl)]
        inp, out = out, []
        if not inp:
            break
        sx, sy = inp[-1]
        s_in = (bx - ax) * (sy - ay) - (by - ay) * (sx - ax) >= 0
        for ex, ey in inp:
            e_in = (bx - ax) * (ey - ay) - (by - ay) * (ex - ax) >= 0
            if e_in:
                if not s_in:
                    out.append(_line_hit(sx, sy, ex, ey, ax, ay, bx, by))
                out.append((ex, ey))
            elif s_in:
                out.append(_line_hit(sx, sy, ex, ey, ax, ay, bx, by))
            sx, sy, s_in = ex, ey, e_in
    return abs(_poly_area(out)) if len(out) >= 3 else 0.0


def _bev_intersection_area(box_a, box_b):
    """Intersection area of the two bird's-eye-view rectangles; 0.0 for invalid polygons."""
    ca, cb = _corners_bev(box_a), _corners_bev(box_b)
    if _resolve_backend() == "shapely":
        from shapely.geometry import Polygon
        pa, pb = Polygon(ca), Polygon(cb)
        if not pa.is_valid or not pb.is_valid:
            return 0.0
        return pa.intersection(pb).area
    if not (np.isfinite(ca).all() and np.isfinite(cb).all()):
        return 0.0
    # rectangles whose circumscribed circles do not touch cannot intersect (exact)
    ra = 0.5 * math.hypot(float(box_a[3]), float(box_a[4]))
    rb = 0.5 * math.hypot(float(box_b[3]), float(box_b[4]))
    if math.hypot(float(box_a[0]) - float(box_b[0]), float(box_a[1]) - float(box_b[1])) > ra + rb + 1e-6:
        return 0.0
    pa = [(float(u), float(v)) for u, v in ca]
    pb = [(float(u), float(v)) for u, v in cb]
    return _clip_area(pa, pb)


def rotated_iou_3d(box_a, box_b):
    """Rotated 3D IoU. Same rules as rotated_iou_3d in scripts/kitti_v2/03_compute_frame_errors.py
    (bird's-eye-view intersection times height overlap); the polygon intersection comes from
    shapely when installed and from the built-in clipper otherwise."""
    bi = _bev_intersection_area(box_a, box_b)
    if bi <= 0:
        return 0.0
    za_lo, za_hi = box_a[2] - box_a[5] / 2, box_a[2] + box_a[5] / 2
    zb_lo, zb_hi = box_b[2] - box_b[5] / 2, box_b[2] + box_b[5] / 2
    z = max(0.0, min(za_hi, zb_hi) - max(za_lo, zb_lo))
    if z <= 0:
        return 0.0
    i3 = bi * z
    va = box_a[3] * box_a[4] * box_a[5]
    vb = box_b[3] * box_b[4] * box_b[5]
    u = va + vb - i3
    return float(i3 / u) if u > 0 else 0.0


def load_gt(info_path, eval_classes):
    with open(info_path, "rb") as f:
        info = pickle.load(f)
    gt, skipped = {}, 0
    for e in info:
        img_idx = e.get("image_idx") or e.get("point_cloud", {}).get("lidar_idx")
        if img_idx is None:
            continue
        fid = f"{int(img_idx):06d}"
        annos = e.get("annos", {})
        names = list(annos.get("name", []))
        boxes = annos.get("gt_boxes_lidar", np.zeros((0, 7)))
        if not isinstance(boxes, np.ndarray):
            boxes = np.asarray(boxes)
        n_boxes = len(boxes)
        if len(names) > n_boxes:
            names = names[:n_boxes]
        elif len(names) < n_boxes:
            skipped += 1
            continue
        keep = [n in eval_classes for n in names]
        if n_boxes > 0:
            boxes = boxes[keep]
        names = [n for n, k in zip(names, keep) if k]
        gt[fid] = {"gt_boxes": np.asarray(boxes, dtype=np.float32), "gt_names": names}
    return gt, skipped


def iou_matrix(dets, gt_boxes, gt_names):
    M = np.zeros((len(dets), len(gt_boxes)))
    for i, d in enumerate(dets):
        dbox = np.asarray(d["consensus_box"], dtype=np.float32)
        for gi in range(len(gt_boxes)):
            if gt_names[gi] != d["cls"]:
                continue
            M[i, gi] = rotated_iou_3d(dbox, gt_boxes[gi])
    return M


def greedy_match(dets, M, gt_names, thr_by_cls):
    """Same rule as compute_fn_fp of the RUM pipeline: detections in list order,
    each takes the unmatched ground-truth box of its class with the largest IoU
    (first on ties); matched if that IoU reaches the class threshold."""
    matched, y = set(), np.zeros(len(dets), dtype=np.uint8)
    for i, d in enumerate(dets):
        best_iou, best_gi = 0.0, -1
        for gi in range(M.shape[1]):
            if gi in matched or gt_names[gi] != d["cls"]:
                continue
            if M[i, gi] > best_iou:
                best_iou, best_gi = M[i, gi], gi
        if best_gi >= 0 and best_iou >= thr_by_cls[d["cls"]]:
            matched.add(best_gi)
            y[i] = 1
    return y, M.shape[1] - len(matched)


def build_table(scored, gt, settings):
    frames = scored["frames"]
    fids = sorted(frames.keys())
    cols = {"fpos": [], "cls": [], "u": [], "rng": [], "nmem": []}
    ys = {s: [] for s in settings}
    fnfp = {s: {} for s in settings}
    missing = []
    for fpos, fid in enumerate(fids):
        dets = frames[fid]
        if fid not in gt:
            missing.append(fid)
            continue
        g = gt[fid]
        M = iou_matrix(dets, g["gt_boxes"], g["gt_names"]) if len(dets) else np.zeros((0, len(g["gt_names"])))
        for s, thr in settings.items():
            y, fn = greedy_match(dets, M, g["gt_names"], thr)
            ys[s].append(y)
            fnfp[s][fid] = (int(fn), int((y == 0).sum()))
        for d in dets:
            cols["fpos"].append(fpos)
            cols["cls"].append(d["cls"])
            cols["u"].append(d["u"])
            cols["rng"].append(d["range"])
            cols["nmem"].append(d["num_members_detected"])
    if missing:
        raise RuntimeError(f"{len(missing)} frames have no ground truth, first: {missing[:5]}")
    tab = {
        "fids": fids, "n_frames": len(fids),
        "fpos": np.asarray(cols["fpos"], dtype=np.int64),
        "cls": np.asarray(cols["cls"]),
        "u": np.asarray(cols["u"], dtype=np.float64),
        "rng": np.asarray(cols["rng"], dtype=np.float64),
        "nmem": np.asarray(cols["nmem"], dtype=np.int64),
    }
    for s in settings:
        tab["y_" + s] = np.concatenate(ys[s]) if ys[s] else np.zeros(0, dtype=np.uint8)
    return tab, fnfp


def verify_against_cache(fnfp_ours, cache_errors):
    bad = []
    for fid, (fn_c, fp_c) in cache_errors.items():
        if fid not in fnfp_ours or fnfp_ours[fid] != (int(fn_c), int(fp_c)):
            bad.append((fid, fnfp_ours.get(fid), (int(fn_c), int(fp_c))))
    extra = [f for f in fnfp_ours if f not in cache_errors]
    return bad, extra


# ----------------------------------------------------------------------------
# Statistics: Hoeffding-Bentkus p-value and intervals. Written from the
# definition in Angelopoulos et al., Learn then Test (ref 3 of the paper);
# the formula must be checked against that paper before numbers are used.
# ----------------------------------------------------------------------------
def _h1(a, b):
    out = 0.0
    if a > 0:
        out += a * math.log(a / b)
    if a < 1:
        out += (1 - a) * math.log((1 - a) / (1 - b))
    return out


def _log_binom_cdf(k, n, p):
    if k < 0:
        return -math.inf
    if k >= n:
        return 0.0
    lg = math.lgamma
    lp, lq = math.log(p), math.log1p(-p)
    terms = [lg(n + 1) - lg(i + 1) - lg(n - i + 1) + i * lp + (n - i) * lq for i in range(k + 1)]
    m = max(terms)
    return m + math.log(sum(math.exp(t - m) for t in terms))


def hb_pvalue(S, n, alpha):
    """p-value for H: E[loss] > alpha, from n independent losses in [0,1] with sum S."""
    if n <= 0:
        return 1.0
    rhat = S / n
    if rhat >= alpha:
        return 1.0
    p1 = math.exp(-n * _h1(min(rhat, alpha), alpha))
    k = math.ceil(S - 1e-9)
    p2 = math.e * math.exp(_log_binom_cdf(k, n, alpha))
    return min(1.0, p1, p2)


def hb_upper(S, n, delta):
    """Smallest alpha at which H: E[loss] > alpha is rejected at level delta."""
    if n <= 0:
        return 1.0
    lo, hi = S / n, 1.0 - 1e-12
    if hb_pvalue(S, n, hi) > delta:
        return 1.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if hb_pvalue(S, n, mid) <= delta:
            hi = mid
        else:
            lo = mid
    return hi


def hb_lower(S, n, delta):
    if n <= 0:
        return 0.0
    return 1.0 - hb_upper(n - S, n, delta)


def n_required(alpha, delta):
    """Smallest n at which zero observed false acceptances reject H: risk > alpha."""
    lo, hi = 1, 1
    while hb_pvalue(0.0, hi, alpha) > delta:
        hi *= 2
    while lo < hi:
        mid = (lo + hi) // 2
        if hb_pvalue(0.0, mid, alpha) <= delta:
            hi = mid
        else:
            lo = mid + 1
    return lo


def auroc_groups(score, y):
    """Group ids over sorted unique scores (ascending) for weighted AUROC."""
    uniq, gid = np.unique(score, return_inverse=True)
    return gid, len(uniq)


def auroc_weighted(gid, ng, y, w):
    W1 = np.bincount(gid, weights=w * (y == 1), minlength=ng)
    W0 = np.bincount(gid, weights=w * (y == 0), minlength=ng)
    den = W1.sum() * W0.sum()
    if den <= 0:
        return float("nan")
    cum0 = np.cumsum(W0) - W0
    return float((W1 * (cum0 + 0.5 * W0)).sum() / den)


# ----------------------------------------------------------------------------
# One (split, class) cell of frames
# ----------------------------------------------------------------------------
class Cell:
    """Frames of one class in one split. A frame belongs to the class if it holds at
    least one in-class consensus detection. The per-frame false acceptance
    proportion a_f is the share of accepted in-class detections that are
    incorrect, and 0 for a frame without accepted in-class detections (the usual
    false-discovery-proportion convention)."""

    def __init__(self, fpos, u, y):
        self.frames, self.lf = np.unique(fpos, return_inverse=True)
        self.m = len(self.frames)
        self.u, self.y = u, y
        self.correct_per_frame = np.bincount(self.lf[y == 1], minlength=self.m).astype(float)

    def a_f(self, tau):
        acc = self.u <= tau
        na = np.bincount(self.lf[acc], minlength=self.m)
        nw = np.bincount(self.lf[acc & (self.y == 0)], minlength=self.m)
        a = np.zeros(self.m)
        nz = na > 0
        a[nz] = nw[nz] / na[nz]
        return a

    def acc_correct_per_frame(self, tau):
        return np.bincount(self.lf[(self.u <= tau) & (self.y == 1)], minlength=self.m).astype(float)

    def retention(self, tau):
        c = self.correct_per_frame.sum()
        return float(self.acc_correct_per_frame(tau).sum() / c) if c > 0 else float("nan")


# ----------------------------------------------------------------------------
# Analysis of one variant
# ----------------------------------------------------------------------------
def split_frames(n_frames, seed, cfg):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n_frames)
    ng = int(round(cfg["frac_grid"] * n_frames))
    ns = int(round(cfg["frac_select"] * n_frames))
    codes = np.full(n_frames, 2, dtype=np.int8)      # 0 grid, 1 select, 2 eval
    codes[perm[:ng]] = 0
    codes[perm[ng:ng + ns]] = 1
    return codes


def chain_index(pvals_by_class, level):
    """Fixed sequence from the most restrictive grid point upward. Returns the index of
    the last grid point reached before the first non-rejection, or -1."""
    J = len(pvals_by_class[0])
    last = -1
    for j in range(J):
        if all(p[j] <= level for p in pvals_by_class):
            last = j
        else:
            break
    return last


def analyse(tab, y, objects, cut_q, seed, cfg, alphas, boot=False):
    nF = tab["n_frames"]
    delta = cfg["delta"]
    codes = split_frames(nF, seed, cfg)
    sel = np.isin(tab["cls"], objects)
    dcode = codes[tab["fpos"]]
    g = sel & (dcode == 0)
    if g.sum() < 10:
        raise RuntimeError("grid split holds fewer than 10 detections")
    cut = float(np.quantile(tab["rng"][g], cut_q))
    grid = np.unique(np.quantile(tab["u"][g], cfg["grid_levels"]))
    cid = (tab["rng"] > cut).astype(int)

    cells = {}
    for s_name, s_code in (("select", 1), ("eval", 2)):
        for c in (0, 1):
            m = sel & (dcode == s_code) & (cid == c)
            cells[(s_name, c)] = Cell(tab["fpos"][m], tab["u"][m], y[m])

    info = {"cut_m": cut, "grid_size": int(len(grid)), "classes": {}}
    for c in (0, 1):
        ce, cs = cells[("eval", c)], cells[("select", c)]
        info["classes"][CLASS_NAMES[c]] = {
            "frames_select": cs.m, "frames_eval": ce.m,
            "detections_select": int(len(cs.u)), "detections_eval": int(len(ce.u)),
            "share_incorrect_eval": float(1 - ce.y.mean()) if len(ce.y) else float("nan"),
        }

    # sums of a_f on the selection split over the grid, and the descriptive frontier
    S_sel = {c: np.array([cells[("select", c)].a_f(t).sum() for t in grid]) for c in (0, 1)}
    frontier = []
    if boot:      # descriptive table, computed for the primary variant only (it is slow)
        for c in (0, 1):
            cs = cells[("select", c)]
            for j, t in enumerate(grid):
                frontier.append({
                    "class": CLASS_NAMES[c], "tau": float(t),
                    "retention_select": cs.retention(t),
                    "A_hat_select": float(S_sel[c][j] / cs.m) if cs.m else float("nan"),
                    "hb_upper_select": hb_upper(S_sel[c][j], cs.m, delta),
                })
        info["min_pointwise_upper_bound_select"] = {
            CLASS_NAMES[c]: min(r["hb_upper_select"] for r in frontier if r["class"] == CLASS_NAMES[c])
            for c in (0, 1)}

    # discrimination per class on the evaluation split
    auroc = {}
    rng_b = np.random.default_rng(seed + 1000)
    for c in (0, 1):
        ce = cells[("eval", c)]
        if len(ce.u) == 0:
            auroc[CLASS_NAMES[c]] = None
            continue
        gid, ng = auroc_groups(-ce.u, ce.y)
        point = auroc_weighted(gid, ng, ce.y, np.ones(len(ce.u)))
        lo = hi = float("nan")
        if boot:
            W = rng_b.multinomial(ce.m, np.full(ce.m, 1.0 / ce.m), size=cfg["n_boot"])
            vals = np.array([auroc_weighted(gid, ng, ce.y, W[b][ce.lf].astype(float))
                             for b in range(cfg["n_boot"])])
            lo, hi = np.nanpercentile(vals, [100 * delta / 2, 100 * (1 - delta / 2)])
        auroc[CLASS_NAMES[c]] = {"auroc": point, "lo": float(lo), "hi": float(hi)}
    info["auroc_eval"] = auroc

    results = []
    for alpha in alphas:
        p_by_class = {c: [hb_pvalue(S_sel[c][j], cells[("select", c)].m, alpha) for j in range(len(grid))]
                      for c in (0, 1)}
        tau = {}
        for c in (0, 1):
            j = chain_index([p_by_class[c]], delta)
            tau[c] = float(grid[j]) if j >= 0 else None
        jstar = chain_index([p_by_class[0], p_by_class[1]], delta / 2)
        tau_star = float(grid[jstar]) if jstar >= 0 else None

        res = {"alpha": alpha, "tau": {"near": tau[0], "far": tau[1], "star": tau_star}, "cells": [], "gap": {}}
        for c in (0, 1):
            for c2 in (0, 1):
                cell = {"established": CLASS_NAMES[c], "applied": CLASS_NAMES[c2]}
                ce = cells[("eval", c2)]
                if tau[c] is None:
                    cell["outcome"] = "no threshold established"
                    res["cells"].append(cell)
                    continue
                a = ce.a_f(tau[c])
                S, n = a.sum(), ce.m
                U, L = hb_upper(S, n, delta / 2), hb_lower(S, n, delta / 2)
                outcome = "applies" if U <= alpha else ("does not apply" if L > alpha else "not determined")
                cell.update({"tau": tau[c], "A_hat": float(S / n) if n else float("nan"),
                             "hb_L": L, "hb_U": U, "outcome": outcome,
                             "R_hat": ce.retention(tau[c]), "n_eval_frames": n})
                if boot and n > 0:
                    W = np.random.default_rng(seed + 2000).multinomial(n, np.full(n, 1.0 / n), size=cfg["n_boot"])
                    Ab = W @ a / n
                    cell["boot_lo"], cell["boot_hi"] = [float(v) for v in
                                                        np.percentile(Ab, [100 * delta / 2, 100 * (1 - delta / 2)])]
                    ac, cc = ce.acc_correct_per_frame(tau[c]), ce.correct_per_frame
                    with np.errstate(invalid="ignore", divide="ignore"):
                        Rb = (W @ ac) / (W @ cc)
                    cell["R_lo"], cell["R_hi"] = [float(v) for v in
                                                  np.nanpercentile(Rb, [100 * delta / 2, 100 * (1 - delta / 2)])]
                res["cells"].append(cell)
        for c in (0, 1):
            if tau[c] is not None and tau_star is not None:
                ce = cells[("eval", c)]
                gap = ce.retention(tau[c]) - ce.retention(tau_star)
                entry = {"G": float(gap)}
                if boot and ce.m > 0:
                    W = np.random.default_rng(seed + 3000).multinomial(ce.m, np.full(ce.m, 1.0 / ce.m), size=cfg["n_boot"])
                    cc = W @ ce.correct_per_frame
                    with np.errstate(invalid="ignore", divide="ignore"):
                        Gb = (W @ ce.acc_correct_per_frame(tau[c])) / cc - (W @ ce.acc_correct_per_frame(tau_star)) / cc
                    entry["lo"], entry["hi"] = [float(v) for v in
                                                np.nanpercentile(Gb, [100 * delta / 2, 100 * (1 - delta / 2)])]
                res["gap"][CLASS_NAMES[c]] = entry
        results.append(res)
    return info, results, frontier


# ----------------------------------------------------------------------------
# Self-test
# ----------------------------------------------------------------------------
def _synthetic_table(n_frames, rng, range_effect=0.0):
    fpos, rngs, us, ys = [], [], [], []
    for f in range(n_frames):
        k = rng.poisson(6)
        r = rng.uniform(2, 78, size=k)
        p_correct = np.clip(0.97 - 0.004 * r - range_effect * (r > 35), 0.05, 0.99)
        yy = (rng.uniform(size=k) < p_correct).astype(np.uint8)
        u = np.where(yy == 1, 0.03 + rng.gamma(2.0, 0.012, size=k), 0.03 + rng.gamma(2.5, 0.035, size=k))
        fpos.append(np.full(k, f)); rngs.append(r); us.append(u); ys.append(yy)
    tab = {"n_frames": n_frames, "fpos": np.concatenate(fpos), "rng": np.concatenate(rngs),
           "u": np.concatenate(us)}
    tab["cls"] = np.full(len(tab["u"]), "Car")
    return tab, np.concatenate(ys)


def selftest():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail else ""))
        ok = ok and cond

    # 1. sample-size table reproduced from the p-value implementation
    expected = {(1e-2, 0.05): 299, (1e-2, 0.05 / 6): 477, (1e-2, 0.025): 368,
                (1e-3, 0.05): 2995, (1e-3, 0.05 / 6): 4786, (1e-3, 0.025): 3688,
                (1e-4, 0.05): 29956, (1e-4, 0.05 / 6): 47873, (1e-4, 0.025): 36887}
    got = {k: n_required(*k) for k in expected}
    check("zero-failure frame counts equal Table 4 of the draft", got == expected,
          "" if got == expected else str(got))

    # 2. zero-failure upper bound equals 1 - delta^(1/n)
    n, d = 400, 0.025
    check("zero-failure upper bound equals 1 - delta^(1/n)", abs(hb_upper(0.0, n, d) - (1 - d ** (1 / n))) < 1e-9)

    # 3. validity of the p-value at the boundary (risk equal to alpha), mixed loss
    rng = np.random.default_rng(1)
    n, alpha, delta, reps = 300, 0.05, 0.05, 4000
    rej = 0
    for _ in range(reps):
        empty = rng.uniform(size=n) < 0.6
        loss = np.where(empty, 0.0, rng.beta(1, 7, size=n))      # mean = 0.4 * 0.125 = alpha
        rej += hb_pvalue(loss.sum(), n, alpha) <= delta
    rate = rej / reps
    check("false rejection rate at the boundary stays below delta", rate <= delta + 3 * math.sqrt(delta * (1 - delta) / reps),
          f"observed {rate:.4f}")

    # 3b. same check with Bernoulli losses, where the bound is closer to tight
    rej = sum(hb_pvalue(float((rng.uniform(size=n) < alpha).sum()), n, alpha) <= delta for _ in range(reps))
    rate_b = rej / reps
    check("false rejection rate with Bernoulli losses stays below delta",
          rate_b <= delta + 3 * math.sqrt(delta * (1 - delta) / reps), f"observed {rate_b:.4f}")

    # 4. coverage of the two-sided interval
    n, p, reps = 500, 0.02, 3000
    cov = 0
    for _ in range(reps):
        S = float((rng.uniform(size=n) < p).sum())
        cov += hb_lower(S, n, 0.025) <= p <= hb_upper(S, n, 0.025)
    check("two-sided interval covers the true proportion at least 95 percent", cov / reps >= 0.95, f"observed {cov / reps:.4f}")

    # 5. greedy matching on a toy frame (IoU matrix given)
    dets = [{"cls": "Car"}, {"cls": "Car"}, {"cls": "Pedestrian"}]
    M = np.array([[0.8, 0.0], [0.6, 0.0], [0.0, 0.9]])
    y, fn = greedy_match(dets, M, ["Car", "Pedestrian"], {"Car": 0.5, "Pedestrian": 0.5})
    check("greedy match: second detection of one object is a false acceptance, other class matches its own box",
          [int(v) for v in y] == [1, 0, 1] and fn == 0, f"y={[int(v) for v in y]} fn={fn}")

    # 6. box overlap (backend: shapely if installed, otherwise the built-in clipper)
    backend = _resolve_backend()
    a = np.array([0, 0, 0, 4, 2, 2, 0], dtype=np.float32)
    b = np.array([2, 0, 0, 4, 2, 2, 0], dtype=np.float32)
    c = np.array([50, 0, 0, 4, 2, 2, 0], dtype=np.float32)
    check(f"IoU of identical boxes is 1 [{backend}]", abs(rotated_iou_3d(a, a) - 1) < 1e-6)
    check(f"IoU of boxes shifted by half a length is 1/3 [{backend}]", abs(rotated_iou_3d(a, b) - 1 / 3) < 1e-6)
    check(f"IoU of distant boxes is 0 [{backend}]", rotated_iou_3d(a, c) == 0.0)

    def xy(box):
        return [(float(u), float(v)) for u, v in _corners_bev(box)]

    r2 = math.sqrt(2.0)
    sq = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]
    dia = [(r2, 0.0), (0.0, r2), (-r2, 0.0), (0.0, -r2)]
    check("clipper: square and 45-degree square, exact area 8*sqrt(2) - 8",
          abs(_clip_area(sq, dia) - (8 * r2 - 8)) < 1e-9)
    ra = np.array([1.0, 2.0, 0, 4.0, 2.0, 1.5, 0.7])
    rb = np.array([1.0, 2.0, 0, 2.0, 4.0, 1.5, 0.7])
    check("clipper: crossed 4 x 2 and 2 x 4 rectangles, exact area 4",
          abs(_clip_area(xy(ra), xy(rb)) - 4.0) < 1e-9)
    inner = np.array([1.2, 1.9, 0, 1.0, 0.5, 1.5, 0.7])
    check("clipper: rectangle inside another, exact area 0.5", abs(_clip_area(xy(ra), xy(inner)) - 0.5) < 1e-9)
    rt, worst, N = np.random.default_rng(11), 0.0, 300000
    for _ in range(25):
        b1 = np.array([rt.uniform(-2, 2), rt.uniform(-2, 2), 0, rt.uniform(1, 5), rt.uniform(1, 3), 1.5, rt.uniform(-3.1, 3.1)])
        b2 = np.array([rt.uniform(-2, 2), rt.uniform(-2, 2), 0, rt.uniform(1, 5), rt.uniform(1, 3), 1.5, rt.uniform(-3.1, 3.1)])
        pts = rt.uniform(-5.6, 5.6, size=(N, 2))
        inside = np.ones(N, dtype=bool)
        for bx in (b1, b2):
            cx, sx = math.cos(bx[6]), math.sin(bx[6])
            lx = cx * (pts[:, 0] - bx[0]) + sx * (pts[:, 1] - bx[1])
            ly = -sx * (pts[:, 0] - bx[0]) + cx * (pts[:, 1] - bx[1])
            inside &= (np.abs(lx) <= bx[3] / 2) & (np.abs(ly) <= bx[4] / 2)
        p_hat = inside.mean()
        est = 11.2 ** 2 * p_hat
        tol = 5 * 11.2 ** 2 * math.sqrt(max(p_hat, 1.0 / N) / N)
        worst = max(worst, abs(_clip_area(xy(b1), xy(b2)) - est) / tol)
    check("clipper agrees with Monte Carlo area for 25 random rotated rectangle pairs", worst <= 1.0,
          f"worst deviation {worst:.2f} of tolerance")
    if backend == "shapely":
        diff = 0.0
        for _ in range(200):
            b1 = np.array([rt.uniform(-2, 2), rt.uniform(-2, 2), 0, rt.uniform(1, 5), rt.uniform(1, 3), 1.5, rt.uniform(-3.1, 3.1)], dtype=np.float32)
            b2 = np.array([rt.uniform(-2, 2), rt.uniform(-2, 2), 0, rt.uniform(1, 5), rt.uniform(1, 3), 1.5, rt.uniform(-3.1, 3.1)], dtype=np.float32)
            v_sh = rotated_iou_3d(b1, b2)
            global _RESOLVED_BACKEND
            _RESOLVED_BACKEND = "clip"
            v_cl = rotated_iou_3d(b1, b2)
            _RESOLVED_BACKEND = "shapely"
            diff = max(diff, abs(v_sh - v_cl))
        check("shapely and built-in clipper give the same IoU", diff < 1e-9, f"largest difference {diff:.2e}")

    # 7. end-to-end validity of the certification chain on synthetic frames
    cfg = dict(CFG)
    pop, ypop = _synthetic_table(60000, np.random.default_rng(7))
    alpha, reps, fails, certified = 0.05, 60, 0, 0
    for r in range(reps):
        tab, yy = _synthetic_table(3000, np.random.default_rng(100 + r))
        info, results, _ = analyse(tab, yy, ["Car"], 0.5, r, cfg, [alpha])
        cut = info["cut_m"]
        for c, name in ((0, "near"), (1, "far")):
            tau = results[0]["tau"][name]
            if tau is None:
                continue
            certified += 1
            m = (pop["rng"] <= cut) if c == 0 else (pop["rng"] > cut)
            A_pop = Cell(pop["fpos"][m], pop["u"][m], ypop[m]).a_f(tau).mean()
            fails += A_pop > alpha
    check("certified thresholds meet alpha in the population in at least 90 percent of trials",
          certified > 0 and fails / certified <= 0.10, f"{fails} failures in {certified} certified thresholds")

    # 8. smoke test of the bootstrap branch
    tab, yy = _synthetic_table(800, np.random.default_rng(5))
    cfg_small = dict(CFG); cfg_small["n_boot"] = 200
    info, results, _ = analyse(tab, yy, ["Car"], 0.5, 0, cfg_small, [0.1], boot=True)
    cells_ok = all(("boot_lo" in c) or c["outcome"] == "no threshold established" for c in results[0]["cells"])
    check("bootstrap branch runs and fills intervals", cells_ok)

    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    return ok


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(x, nd=4):
    if x is None:
        return "NA"
    if isinstance(x, float) and math.isnan(x):
        return "nan"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def write_summary(out_dir, primary_info, primary_results, tally_rows, verify_msg, cfg):
    L = []
    L.append("M1 SUMMARY  (indicator = saved RUM u, not yet the paper's u_s / u_e)")
    L.append(verify_msg)
    p = cfg["primary"]
    L.append(f"primary variant: iou={p['iou']} objects={p['objects']} cut_q={p['cut_q']} seed={p['seed']}")
    L.append(f"range cut (m): {fmt(primary_info['cut_m'], 2)}   grid points: {primary_info['grid_size']}")
    for name, ci in primary_info["classes"].items():
        L.append(f"  {name}: frames select/eval = {ci['frames_select']}/{ci['frames_eval']}, "
                 f"detections select/eval = {ci['detections_select']}/{ci['detections_eval']}, "
                 f"share incorrect (eval) = {fmt(ci['share_incorrect_eval'])}")
    L.append("smallest pointwise upper bound on A on the selection split (no alpha below this can be certified):")
    for name, v in primary_info["min_pointwise_upper_bound_select"].items():
        L.append(f"  {name}: {fmt(v)}")
    L.append("AUROC of u (correct vs incorrect) on the evaluation split:")
    for name, a in primary_info["auroc_eval"].items():
        L.append(f"  {name}: " + ("NA" if a is None else f"{fmt(a['auroc'])} [{fmt(a['lo'])}, {fmt(a['hi'])}]"))
    for res in primary_results:
        tag = "frozen" if res["alpha"] in cfg["alphas_frozen"] else "EXPLORATORY (outside frozen sweep)"
        L.append("")
        L.append(f"alpha = {res['alpha']:g}  [{tag}]   tau near/far/star = "
                 f"{fmt(res['tau']['near'], 5)} / {fmt(res['tau']['far'], 5)} / {fmt(res['tau']['star'], 5)}")
        for cell in res["cells"]:
            head = f"  T[{cell['established']} -> {cell['applied']}]: {cell['outcome']}"
            if "A_hat" in cell:
                head += (f" | A={fmt(cell['A_hat'])} HB[{fmt(cell['hb_L'])}, {fmt(cell['hb_U'])}]"
                         f" boot[{fmt(cell.get('boot_lo'))}, {fmt(cell.get('boot_hi'))}]"
                         f" | R={fmt(cell['R_hat'])} [{fmt(cell.get('R_lo'))}, {fmt(cell.get('R_hi'))}]"
                         f" | n_eval={cell['n_eval_frames']}")
            L.append(head)
        for name, g in res["gap"].items():
            L.append(f"  retention gap {name}: {fmt(g['G'])} [{fmt(g.get('lo'))}, {fmt(g.get('hi'))}]")
    L.append("")
    L.append("OUTCOME TALLY OVER THE SEEDS, primary variant (all other variants: tally_all_variants.json):")
    for r in tally_rows:
        L.append("  " + " | ".join(f"{k}={v}" for k, v in r.items()))
    text = "\n".join(L)
    (out_dir / "summary.txt").write_text(text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rum", type=str, default="/rum")
    ap.add_argument("--out", type=str, default="results")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--allow-mismatch", action="store_true")
    ap.add_argument("--bev", choices=["auto", "shapely", "clip"], default="auto")
    args = ap.parse_args()
    global BEV_BACKEND
    BEV_BACKEND = args.bev

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    t0 = time.time()
    rum, out = Path(args.rum), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    f_scored = rum / "detections/kitti_v2/scored_val.pkl"
    f_cache = rum / "detections/kitti_v2/frame_errors_cache.pkl"
    f_info = rum / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl"
    for f in (f_scored, f_cache, f_info):
        if not f.exists():
            sys.exit(f"missing input: {f}")

    print(f"box overlap backend: {_resolve_backend()}")
    scored = pickle.load(open(f_scored, "rb"))
    cache = pickle.load(open(f_cache, "rb"))
    gt, skipped = load_gt(f_info, cache["eval_classes"])
    print(f"frames in scored file: {len(scored['frames'])}; ground truth frames: {len(gt)}; skipped infos: {skipped}")

    tab, fnfp = build_table(scored, gt, CFG["iou_settings"])
    print(f"detections: {len(tab['u'])}  ({time.time() - t0:.0f} s)")

    bad, extra = verify_against_cache(fnfp[CFG["verify_setting"]], cache["errors"])
    if bad or extra:
        verify_msg = (f"VERIFICATION FAILED: {len(bad)} frames differ from frame_errors_cache.pkl "
                      f"(first 5 as frame, ours (FN,FP), cache (FN,FP): {bad[:5]}); {len(extra)} frames not in the cache")
        print(verify_msg)
        (out / "verification_failed.txt").write_text(verify_msg)
        if not args.allow_mismatch:
            sys.exit(2)
    else:
        verify_msg = (f"VERIFICATION PASSED: per-frame FN and FP at {CFG['verify_setting']} equal "
                      f"frame_errors_cache.pkl for all {len(cache['errors'])} frames")
        print(verify_msg)

    prov = {"script_version": SCRIPT_VERSION, "bev_backend": _resolve_backend(), "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "python": platform.python_version(), "numpy": np.__version__,
            "inputs_sha256": {str(f): sha256(f) for f in (f_scored, f_cache, f_info)},
            "script_sha256": sha256(__file__), "config": CFG, "verification": verify_msg,
            "n_frames": tab["n_frames"], "n_detections": int(len(tab["u"])),
            "detections_by_class": {c: int((tab["cls"] == c).sum()) for c in np.unique(tab["cls"])},
            "detections_by_members": {int(k): int((tab["nmem"] == k).sum()) for k in np.unique(tab["nmem"])},
            "share_incorrect_by_setting": {s: float(1 - tab["y_" + s].mean()) for s in CFG["iou_settings"]}}
    try:
        import shapely
        prov["shapely"] = shapely.__version__
    except ImportError:
        pass
    (out / "provenance.json").write_text(json.dumps(prov, indent=2))
    with open(out / "detections_table.pkl", "wb") as f:
        pickle.dump(tab, f)

    alphas = CFG["alphas_frozen"] + CFG["alphas_exploratory"]
    rows, tally, primary = [], {}, None
    frontier_rows = []
    for iou in CFG["iou_settings"]:
        y = tab["y_" + iou]
        for obj_name, objs in CFG["object_sets"].items():
            for cut_q in CFG["cut_quantiles"]:
                for seed in CFG["seeds"]:
                    is_primary = (iou == CFG["primary"]["iou"] and obj_name == CFG["primary"]["objects"]
                                  and cut_q == CFG["primary"]["cut_q"] and seed == CFG["primary"]["seed"])
                    info, results, frontier = analyse(tab, y, objs, cut_q, seed, CFG, alphas, boot=is_primary)
                    if is_primary:
                        primary = (info, results)
                        for fr in frontier:
                            frontier_rows.append(fr)
                    for res in results:
                        for cell in res["cells"]:
                            key = (iou, obj_name, cut_q, res["alpha"], cell["established"], cell["applied"])
                            tally.setdefault(key, {})
                            tally[key][cell["outcome"]] = tally[key].get(cell["outcome"], 0) + 1
                            rows.append({"iou": iou, "objects": obj_name, "cut_q": cut_q, "cut_m": info["cut_m"],
                                         "seed": seed, "alpha": res["alpha"],
                                         "frozen_sweep": res["alpha"] in CFG["alphas_frozen"],
                                         "established": cell["established"], "applied": cell["applied"],
                                         "outcome": cell["outcome"], "tau": cell.get("tau"),
                                         "A_hat": cell.get("A_hat"), "hb_L": cell.get("hb_L"), "hb_U": cell.get("hb_U"),
                                         "boot_lo": cell.get("boot_lo"), "boot_hi": cell.get("boot_hi"),
                                         "R_hat": cell.get("R_hat"), "n_eval_frames": cell.get("n_eval_frames"),
                                         "frames_select_near": info["classes"]["near"]["frames_select"],
                                         "frames_select_far": info["classes"]["far"]["frames_select"]})
    with open(out / "matrix_all_variants.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(out / "frontier_primary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(frontier_rows[0].keys()))
        w.writeheader(); w.writerows(frontier_rows)
    tally_rows = [dict(iou=k[0], objects=k[1], cut_q=k[2], alpha=k[3], cell=f"{k[4]}->{k[5]}", **v)
                  for k, v in sorted(tally.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3], kv[0][4], kv[0][5]))]
    text = write_summary(out, primary[0], primary[1], [r for r in tally_rows if r["objects"] == CFG["primary"]["objects"]
                                                       and r["iou"] == CFG["primary"]["iou"]
                                                       and r["cut_q"] == CFG["primary"]["cut_q"]], verify_msg, CFG)
    json.dump(tally_rows, open(out / "tally_all_variants.json", "w"), indent=1)
    print(text)
    print(f"\nfinished in {time.time() - t0:.0f} s; files in {out}")


if __name__ == "__main__":
    main()

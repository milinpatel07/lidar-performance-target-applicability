#!/usr/bin/env python3
"""v25_fig1_two_panel.py (v25f1tp-0.5, 2026-10-20) - Fig. 1 of main_v25 in two columns, 122 x 95 mm.

  (a) KITTI, distance: frame 005345, u_s, split 0, threshold selected at near distance at 0.1 (transferred, solid black;
      decides acceptance) and threshold selected at far distance (dashed blue); KITTI rule.
  (b) nuScenes, rain: sample f0f7fec4524045f4a2f44866d410ec84 (scene-0626), u_e, split 0, threshold selected in clear weather at 0.1
      (transferred, solid black; decides acceptance) and threshold selected in rain (dashed blue).
Each column: camera image with projected boxes (1 = accepted correct with the lowest indicator value, 2 = accepted wrong);
bird's-eye view (annotated cars grey, detections outlined, near|far boundary in (a)); inset of the accepted wrong
detection with its member boxes and the annotated cars; indicator strip.
Style as fig_scenes_005345.pdf (v25_fig1.py): correct #0072B2, wrong #D55E00, rejected dashed, KITTI-rule detections dotted
grey; serif (STIX), 7 pt. Frame data are loaded with code/tools/render_frames.py (render-0.1).
Thresholds: data/tau_kitti_distance_split0.json; m6/results/C_weather_nuscenes.csv on the server (= experiments/m6/run1 locally; u_e, seed 0, 0.1).
Writes figures/v25/fig_scenes.pdf and results/v25/fig1_two_panel_facts.txt.
Usage (server container): python3 code/v25/v25_fig1_two_panel.py
"""
import csv, importlib.util, json, pickle, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
from matplotlib.lines import Line2D

W = Path("/data/work"); REL = W
spec = importlib.util.spec_from_file_location("render_frames", str(REL / "code/tools/render_frames.py"))
rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
m1 = rf.m1
COR, WRG, GTE, NS = rf.COR, rf.WRG, rf.GTE, rf.NS
GTF, PTC, FOV = "#D9D9D9", "#808080", "#BBBBBB"   # annotated-car fill; LiDAR points (alpha 0.5, 0.5 pt, ground included); camera field of view
plt.rcParams.update({"font.size": 7, "axes.labelsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7})
MM = 1 / 25.4
FW, FH = 122, 95
# (b): rank 2 of results/v25/fig1b_candidates.csv (v25_fig1b_candidates.py), scene-0626; rank 1 (8b3831ab) has 3D IoU 0 only
# because it sits 1.9 m below an annotated car on a ramp (same position in the bird's-eye view), so it is not an empty-scene case
KITTI_FID, NUSC_TOK = "005345", "f0f7fec4524045f4a2f44866d410ec84"
# recorded counts (frame CSV of fig_scenes_005345; fig1b_candidates.csv): a changed input stops the script
EXPECTED = {"kitti": (5, 1, 1, 0), "nusc": (5, 1, 2, 0)}   # accepted correct, accepted wrong, rejected, not scored


def overlap(a, b):
    """Intersection of two image rectangles (x0, y0, x1, y1) over the area of the smaller one."""
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return max(w, 0) * max(h, 0) / small if small > 0 else 0.0


def thresholds():
    tj = json.load(open(REL / "data/tau_kitti_distance_split0.json"))
    rows = [r for r in csv.DictReader(open(W / "m6/results/C_weather_nuscenes.csv"))
            if r["indicator"] == "u_e" and r["seed"] == "0" and r["alpha"] == "0.1" and r["established"] == r["applied"]]
    tw = {r["established"]: float(r["tau"]) for r in rows}
    return {"kitti": (float(tj["tau"]["near"]), float(tj["tau"]["far"]), float(tj["cut_m"])), "nusc": (tw["clear"], tw["rain"], None)}


def build(ds, fid, ind, tau_t, cut):
    tab = ds.tab; fpos = tab["fids"].index(fid)
    rows = np.where((tab["cls"] == ds.car) & (tab["fpos"] == fpos))[0]
    f = ds.frame(fid)
    if len(f["boxes"]) != len(rows) or not np.allclose(f["rng"], tab["rng"][rows], atol=1e-4):
        sys.exit(f"ABORT {fid}: rebuilt boxes do not align with the table")
    # IoU with the nearest annotated car in the LiDAR frame, where correctness was decided (KITTI: LiDAR frame = drawing frame)
    if isinstance(ds, rf.Nusc):
        cons = [c for c in rf.m3.consensus_for_frame([rf.m3.member_detections(s[fid], ds.scored["min_confidence"]) for s in ds.seeds],
                                                     ds.scored["K"], ds.scored["consensus_threshold"], ds.scored["iou_threshold"]) if c["cls"] == ds.car]
        bl = [np.asarray(c["consensus_box"][:7], float) for c in cons]
        e = ds.infos[fid]; gl = [g for g, n in zip(np.asarray(e["gt_boxes"])[:, :7], e["gt_names"]) if n == "car"]
        g_all = list(np.asarray(e["gt_boxes"])[:, :7])   # annotations of every class
    else:
        bl, gl, g_all = f["boxes"], f["gt"], None
    det = []
    for i, k in enumerate(rows):
        b = f["boxes"][i]; u, v, z = f["project"](rf.corners_3d(b))
        dist_gt = [float(np.hypot(*(g[:2] - bl[i][:2]))) for g in gl]
        j = int(np.argmin(dist_gt)) if dist_gt else None
        det.append({"box": b, "members": f["members"][i], "u": float(tab[ind][k]), "correct": int(tab["y_A_iou0.5"][k]),
                    "scored": f["rule"](k) == "", "dist": float(tab["rng"][k]), "accepted": bool(tab[ind][k] <= tau_t),
                    "zone": ("far" if tab["rng"][k] > cut else "near") if cut else "rain", "uv": (u, v, z), "in_image": bool((z > 0.1).all()),
                    "near_gt": j, "near_gt_dist": dist_gt[j] if dist_gt else float("nan"),
                    "near_gt_iou": float(m1.rotated_iou_3d(np.asarray(bl[i], np.float32), np.asarray(gl[j], np.float32))) if dist_gt else 0.0,
                    "iou_all": None if g_all is None else max((float(m1.rotated_iou_3d(np.asarray(bl[i], np.float32), np.asarray(g, np.float32)))
                                                               for g in g_all), default=0.0),
                    "yaw_spread": float(np.degrees(np.ptp(np.asarray(f["members"][i])[:, 6])))})
        uu, vv, _ = det[-1]["uv"]; H0, H1 = ds.rows or (0, f["img"].shape[0])
        det[-1]["rect"] = (max(uu.min(), 0), max(vv.min(), H0), min(uu.max(), f["img"].shape[1]), min(vv.max(), H1))
        x0_, y0_, x1_, y1_ = det[-1]["rect"]; full = (uu.max() - uu.min()) * (vv.max() - vv.min())
        # numbered boxes must be shown: at least half of the projected rectangle inside the drawn image
        det[-1]["visible"] = det[-1]["in_image"] and full > 0 and max(x1_ - x0_, 0) * max(y1_ - y0_, 0) >= 0.5 * full
    sc = [d for d in det if d["scored"]]
    cnt = (sum(d["accepted"] and d["correct"] for d in sc), sum(d["accepted"] and not d["correct"] for d in sc),
           sum(not d["accepted"] for d in sc), len(det) - len(sc))
    # 1 = accepted correct detection nearest to the sensor, ahead of it and inside the bird's-eye window (also outside the image)
    cc = [d for d in sc if d["accepted"] and d["correct"] and d["box"][0] > 0 and abs(d["box"][1]) <= 20]
    cw = [d for d in sc if d["accepted"] and not d["correct"] and d["visible"]]
    if cw:
        min(cw, key=lambda d: (d["zone"] != "far", d["u"]))["id"] = 2
    if cc:
        min(cc, key=lambda d: d["dist"])["id"] = 1
    return f, det, cnt


def style(d):
    if not d["scored"]:
        return NS, (0, (1, 1.5)), 0.6
    return (COR if d["correct"] else WRG), ("-" if d["accepted"] else (0, (3, 2))), (0.9 if d["accepted"] else 1.0)


def column(fig, x0, cw, title, ds, f, det, ind_tex, tau_t, tau_o, cut, lab_t, lab_o, xmax_bev):
    img = f["img"]; H0, H1 = ds.rows or (0, img.shape[0]); Wd = img.shape[1]
    fig.text((x0 + 0.5) / FW, 1 - 0.3 / FH, title, ha="left", va="top", fontsize=7)
    # camera
    ch = cw * (H1 - H0) / Wd
    axc = fig.add_axes([x0 / FW, (FH - 4.2 - ch) / FH, cw / FW, ch / FH])
    grey = img @ np.array([0.299, 0.587, 0.114]); soft = 0.8 * (0.5 * img + 0.5 * grey[..., None]) + 0.2
    axc.imshow(np.clip(soft, 0, 1), interpolation="lanczos"); axc.set_xlim(0, Wd); axc.set_ylim(H1, H0); axc.axis("off")
    for d in sorted(det, key=lambda d: (d["scored"], d["accepted"])):
        if not d["in_image"]:
            continue
        u, v, _ = d["uv"]; a0, a1 = max(u.min(), 0), min(u.max(), Wd); b0, b1 = max(v.min(), H0), min(v.max(), H1)
        if a1 <= a0 or b1 <= b0:
            continue
        col, ls, _ = style(d)
        num = "id" in d and d["visible"]   # number (and thick line) only for a numbered box inside the image
        lw = 1.2 if num else 0.5
        if lw == 0.5 and ls != "-":
            ls = (0, (6, 4)) if d["scored"] else (0, (2, 3))   # dash lengths scale with the line width
        axc.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, fill=False, ec=col, ls=ls, lw=lw))
    top_bev = FH - 4.2 - ch - 2.0
    # bird's-eye view
    vis = [d for d in det if (d["in_image"] or "id" in d) and d["box"][0] < xmax_bev]
    ylo = max(-20, min([-10] + [d["box"][1] - 3.0 for d in vis])); yhi = min(23, max([10] + [d["box"][1] + 7.5 for d in vis]))
    bh = 22.0
    axb = fig.add_axes([(x0 + 9) / FW, (top_bev - bh) / FH, (cw - 10) / FW, bh / FH])
    pts = f["pts"]; u, v, z = f["project"](pts)
    m = (pts[:, 0] > -1) & (pts[:, 0] < xmax_bev) & (pts[:, 1] > ylo) & (pts[:, 1] < yhi)   # every point in the plotted range
    axb.scatter(pts[m, 0], pts[m, 1], s=0.5 ** 2, c=PTC, alpha=0.5, lw=0, rasterized=True, zorder=1)
    for sgn in (1, -1):
        axb.plot([0, xmax_bev], [0, sgn * xmax_bev * np.tan(f["fov_half"])], color=FOV, lw=0.5, ls="-", zorder=1)
    for g in f["gt"]:
        axb.add_patch(Polygon(rf.corners_xy(g), closed=True, fc=GTF, ec=GTE, lw=0.5, zorder=2))
    for d in det:
        col, ls, lw = style(d)
        axb.add_patch(Polygon(rf.corners_xy(d["box"]), closed=True, fill=False, ec=col, ls=ls,
                              lw=1.0 if d["scored"] and not d["accepted"] else lw * 0.8, zorder=4))
    if cut:
        th = np.linspace(-f["fov_half"], f["fov_half"], 60)
        axb.plot(cut * np.cos(th), cut * np.sin(th), color="black", lw=0.8, ls="-.", zorder=2)
        lbl = {"fontsize": 7, "va": "center", "zorder": 6, "bbox": {"boxstyle": "square,pad=0.1", "fc": "white", "ec": "none", "alpha": 0.85}}
        axb.text(cut - 0.8, 1.6, "near", ha="right", **lbl); axb.text(cut + 0.8, 1.6, "far", ha="left", **lbl)
    axb.add_patch(Polygon([[1.8, 0], [-0.6, 1.1], [-0.6, -1.1]], closed=True, fc="black", ec="none", zorder=5))
    axb.set_xlim(-1, xmax_bev); axb.set_ylim(ylo, yhi); axb.set_aspect("equal", anchor="N")
    axb.set_xticks(range(0, int(xmax_bev) + 1, 20 if xmax_bev > 50 else 10)); axb.set_yticks([-10, 0, 10]); axb.tick_params(length=2, pad=1)
    axb.set_xlabel("forward (m)", labelpad=0.5); axb.set_ylabel("lateral (m)", labelpad=0.5)
    for s in ("top", "right"):
        axb.spines[s].set_visible(False)
    # inset of the accepted wrong detection
    top_in = top_bev - bh - 9.0
    dw = next(d for d in det if d.get("id") == 2)
    ih = 12.0
    ax = fig.add_axes([(x0 + 3) / FW, (top_in - ih) / FH, 20 / FW, ih / FH])
    cx, cy = dw["box"][0], dw["box"][1]; r = 3.4
    mm = (np.abs(pts[:, 0] - cx) < r) & (np.abs(pts[:, 1] - cy) < r * 0.75)
    ax.scatter(pts[mm, 0], pts[mm, 1], s=0.5 ** 2, c=PTC, alpha=0.5, lw=0, rasterized=True, zorder=1)
    for g in f["gt"]:
        ax.add_patch(Polygon(rf.corners_xy(g), closed=True, fc=GTF, ec=GTE, lw=0.5, zorder=2))
    for mb in dw["members"]:
        ax.add_patch(Polygon(rf.corners_xy(mb), closed=True, fill=False, ec=WRG, lw=0.3, zorder=3))
    ax.add_patch(Polygon(rf.corners_xy(dw["box"]), closed=True, fill=False, ec=WRG, lw=0.9, zorder=4))
    ax.set_xlim(cx - r, cx + r); ax.set_ylim(cy - r * 0.75, cy + r * 0.75); ax.set_aspect("equal", anchor="W")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.5); s.set_color(WRG)
    gt_txt = ("no annotated car\nunder it" if dw["near_gt_iou"] < 0.1
              else f"IoU {dw['near_gt_iou']:.2f} with the\nannotated car (grey)")
    fig.text((x0 + 25.5) / FW, (top_in - ih / 2) / FH, f"wrong: {gt_txt}",
             ha="left", va="center", fontsize=7, color=WRG, linespacing=1.25)
    # indicator strip
    sh = 7.0; sb = 13.5
    axs = fig.add_axes([(x0 + 9) / FW, sb / FH, (cw - 10) / FW, sh / FH])
    lanes = {"near": 1, "far": 0} if cut else {"rain": 0}
    for d in det:
        if not d["scored"]:
            continue
        col = COR if d["correct"] else WRG
        axs.plot([d["u"]], [lanes[d["zone"]]], marker="o" if d["correct"] else "^", ms=3.6, mec=col,
                 mfc=col if d["accepted"] else "white", mew=0.8, ls="none", zorder=3)
    axs.axvline(tau_t, color="black", lw=0.8); axs.axvline(tau_o, color=COR, lw=0.8, ls=(0, (3, 2)))
    xmax = max([0.5] + [d["u"] * 1.05 for d in det if d["scored"]])
    top = max(lanes.values()) + 0.6
    axs.set_xlim(0, xmax); axs.set_ylim(-0.6, top); axs.set_yticks(sorted(lanes.values()))
    axs.set_yticklabels([k for k, _ in sorted(lanes.items(), key=lambda kv: kv[1])])
    axs.set_xlabel(rf"${ind_tex}$ of each detection", labelpad=1)
    axs.legend([Line2D([], [], color="black", lw=0.8), Line2D([], [], color=COR, lw=0.8, ls=(0, (3, 2)))], [lab_t, lab_o],
               loc="lower left", bbox_to_anchor=(0.0, 1.0), frameon=False, handlelength=1.8, borderaxespad=0.1, labelspacing=0.15, fontsize=7)
    for s in ("top", "right"):
        axs.spines[s].set_visible(False)
    axs.tick_params(length=2, pad=1)


def main():
    C = pickle.load(open(REL / "cache/tables.pkl", "rb"))
    T = thresholds()
    dk, dn = rf.Kitti(C), rf.Nusc(C)
    tn, tf, cut = T["kitti"]; tc, tr, _ = T["nusc"]
    fk, detk, cntk = build(dk, KITTI_FID, "u_s", tn, cut)
    fn, detn, cntn = build(dn, NUSC_TOK, "u_e", tc, None)
    for name, got in (("kitti", cntk), ("nusc", cntn)):
        if got != EXPECTED[name]:
            sys.exit(f"ABORT {name}: counts {got} differ from the recorded {EXPECTED[name]}")
    fig = plt.figure(figsize=(FW * MM, FH * MM))
    cw = 59.5
    column(fig, 0, cw, r"(a) KITTI, distance, $u_{\mathrm{s}}$", dk, fk, detk, r"u_{\mathrm{s}}", tn, tf, cut,
           "selected at near distance (transferred)", "selected at far distance", 70)
    column(fig, FW - cw, cw, r"(b) nuScenes, rain, $u_{\mathrm{e}}$", dn, fn, detn, r"u_{\mathrm{e}}", tc, tr, None,
           "selected in clear weather (transferred)", "selected in rain", 50)
    h = [Line2D([], [], color=COR, lw=0.9), Line2D([], [], color=WRG, lw=0.9), Line2D([], [], color="black", lw=1.0, ls=(0, (3, 2))),
         Rectangle((0, 0), 1, 1, fc=GTF, ec=GTE, lw=0.5), Line2D([], [], color=FOV, lw=0.5), Line2D([], [], color="black", lw=0.8, ls="-."),
         Rectangle((0, 0), 1, 1, fill=False, ec=WRG, lw=0.3)]
    fig.legend(h, ["correct", "wrong", "rejected", "annotated car", "camera field of view", "near/far boundary", "thin: member boxes"],
               loc="lower center", ncol=7, frameon=False, bbox_to_anchor=(0.5, -0.01), handlelength=1.0, handletextpad=0.3, columnspacing=0.45)
    out = REL / "figures/v25/fig_scenes.pdf"; fig.savefig(out, dpi=400)
    L = [f"v25_fig1_two_panel.py (v25f1tp-0.5); figure {out.relative_to(W)}, {FW} x {FH} mm", ""]
    for tag, name, fid, where, ind, (t1, l1), (t2, l2), det, cnt in (
            ("(a)", "KITTI", KITTI_FID, dk.where(KITTI_FID), "u_s", (tn, "selected at near distance, transferred, decides acceptance"),
             (tf, "selected at far distance"), detk, cntk),
            ("(b)", "nuScenes", NUSC_TOK, dn.where(NUSC_TOK), "u_e", (tc, "selected in clear weather, transferred, decides acceptance"),
             (tr, "selected in rain"), detn, cntn)):
        L += [f"{tag} {name} frame {fid} ({where}); indicator {ind}; split 0; limit 0.1 (exploratory)",
              f"    threshold {l1}: {t1:.5f}", f"    threshold {l2}: {t2:.5f}",
              f"    car detections: accepted correct {cnt[0]}, accepted wrong {cnt[1]}, rejected {cnt[2]}, not scored (KITTI rule) {cnt[3]}"]
        if cut and name == "KITTI":
            L.append(f"    near/far boundary {cut:.3f} m")
        for d in det:
            if d["scored"] and d["accepted"] and not d["correct"]:
                L.append(f"    accepted wrong detection{' (numbered 2)' if d.get('id') == 2 else ''}: distance {d['dist']:.2f} m, {ind} {d['u']:.4f}, "
                         f"nearest annotated car (centre distance {d['near_gt_dist']:.2f} m): 3D IoU {d['near_gt_iou']:.3f}"
                         + ("" if d["iou_all"] is None else f"; largest 3D IoU with any annotation (all classes) {d['iou_all']:.3f}")
                         + f"; member yaw spread {d['yaw_spread']:.1f} deg"
                         + ("" if d["in_image"] else "; outside the camera image"))
        for d in det:
            if d.get("id") == 1:
                L.append(f"    numbered 1: accepted correct, distance {d['dist']:.2f} m, {ind} {d['u']:.4f}")
        if name == "nuScenes":
            L.append(f"    selected from results/v25/fig1b_candidates.csv (rank 2 of {sum(1 for _ in open(REL / 'results/v25/fig1b_candidates.csv')) - 1})")
        L.append("")
    (REL / "results/v25/fig1_two_panel_facts.txt").write_bytes("\n".join(L).encode())
    print("\n".join(L))


if __name__ == "__main__":
    main()

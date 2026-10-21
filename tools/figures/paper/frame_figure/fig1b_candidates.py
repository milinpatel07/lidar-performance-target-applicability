#!/usr/bin/env python3
"""v25_fig1b_candidates.py (v25f1bc-0.1, 2026-10-20) - candidates for panel (b) of the two-column Fig. 1 (nuScenes, rain, u_e).

Rain frames of the evaluation part of split 0 (m6 weather classes), car detections, u_e, clear-weather threshold at 0.1
(transferred; decides acceptance) and rain threshold at 0.1 (m6/results/C_weather_nuscenes.csv, seed 0). A frame qualifies if
  - exactly one accepted wrong detection, with rain threshold < u_e <= clear threshold (rejected by the rain threshold,
    accepted by the transferred one), and it lies inside the CAM_FRONT image;
  - the yaw of its member boxes spans at most 15 degrees (max - min of the raw yaws, so no wrap-around in the mean);
  - its 3D IoU with every annotation of any class is 0, or else its IoU with the nearest annotated car is below 0.3;
  - 3 to 8 accepted correct and at most 3 rejected car detections; every car detection at most 50 m forward.
Ranking: IoU 0 with all annotations first; then the larger projected height of the wrong box in the image (clearer crop);
then more accepted correct detections. Writes release/figures/v25/fig1b_candidates.png (top 12: camera crop around the
wrong box, margin twice the box size, and the full image with all accepted boxes) and release/results/v25/fig1b_candidates.csv.
Usage (server container): python3 release/code/v25/v25_fig1b_candidates.py
"""
import csv, importlib.util, pickle
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

W = Path("/work"); REL = W / "release"
spec = importlib.util.spec_from_file_location("render_frames", str(REL / "code/tools/render_frames.py"))
rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
m1, m3 = rf.m1, rf.m3
COR, WRG = rf.COR, rf.WRG


def main():
    C = pickle.load(open(REL / "cache/tables.pkl", "rb"))
    rows = [r for r in csv.DictReader(open(W / "m6/results/C_weather_nuscenes.csv"))
            if r["indicator"] == "u_e" and r["seed"] == "0" and r["alpha"] == "0.1" and r["established"] == r["applied"]]
    tw = {r["established"]: float(r["tau"]) for r in rows}; tc, tr = tw["clear"], tw["rain"]
    ds = rf.Nusc(C); tab = ds.tab
    codes = m1.split_frames(tab["n_frames"], 0, m1.CFG); wcls, _ = rf.m6.nusc_weather_classes(rf.META, tab["fids"])
    car = tab["cls"] == ds.car; acc = tab["u_e"] <= tc; y = tab["y_A_iou0.5"]
    pre = []
    for fp in np.where((codes == 2) & (wcls == 1))[0]:
        r = np.where(car & (tab["fpos"] == fp))[0]
        aw = r[acc[r] & (y[r] == 0)]; nac = int((acc[r] & (y[r] == 1)).sum()); nrej = int((~acc[r]).sum())
        if len(aw) == 1 and tr < tab["u_e"][aw[0]] <= tc and 3 <= nac <= 8 and nrej <= 3:
            pre.append((int(fp), r, int(aw[0]), nac, nrej))
    print(f"thresholds clear {tc:.5f}, rain {tr:.5f}; rain evaluation frames {int(((codes == 2) & (wcls == 1)).sum())}; "
          f"after the count and u_e conditions {len(pre)}", flush=True)
    cand = []
    for fp, r, kw, nac, nrej in pre:
        tok = tab["fids"][fp]; f = ds.frame(tok)
        cons = [c for c in m3.consensus_for_frame([m3.member_detections(s[tok], ds.scored["min_confidence"]) for s in ds.seeds],
                                                  ds.scored["K"], ds.scored["consensus_threshold"], ds.scored["iou_threshold"]) if c["cls"] == ds.car]
        if len(cons) != len(r) or not np.allclose([c["range"] for c in cons], tab["rng"][r], atol=1e-4):
            raise SystemExit(f"ABORT {tok}: rebuilt boxes do not align with the table")
        i = list(r).index(kw)
        if max(b[0] for b in f["boxes"]) > 50:
            continue
        u, v, z = f["project"](rf.corners_3d(f["boxes"][i]))
        if not (z > 0.1).all() or u.max() < 0 or u.min() > 1600 or v.max() < rf.NUS_ROWS[0] or v.min() > rf.NUS_ROWS[1]:
            continue
        yaw = np.asarray(cons[i]["member_boxes"])[:, 6]
        spread = float(np.degrees(yaw.max() - yaw.min()))
        if spread > 15:
            continue
        e = ds.infos[tok]; gb = np.asarray(e["gt_boxes"])[:, :7]; gn = list(e["gt_names"])
        b = np.asarray(cons[i]["consensus_box"][:7], np.float32)
        iou_all = max((float(m1.rotated_iou_3d(b, np.asarray(g, np.float32))) for g in gb), default=0.0)
        cars = [g for g, n in zip(gb, gn) if n == "car"]
        jn = int(np.argmin([np.hypot(*(g[:2] - b[:2])) for g in cars])) if cars else None
        iou_car = float(m1.rotated_iou_3d(b, np.asarray(cars[jn], np.float32))) if cars else 0.0
        if iou_all > 0 and iou_car >= 0.3:
            continue
        cand.append({"token": tok, "where": ds.where(tok), "dist": float(tab["rng"][kw]), "u_e": float(tab["u_e"][kw]),
                     "yaw_spread_deg": spread, "iou_all": iou_all, "iou_nearest_car": iou_car, "acc_correct": nac, "rejected": nrej,
                     "box_h_px": float(min(v.max(), rf.NUS_ROWS[1]) - max(v.min(), rf.NUS_ROWS[0])), "uv": (u, v), "f": f, "r": r})
    cand.sort(key=lambda c: (c["iou_all"] > 0, -c["box_h_px"], -c["acc_correct"]))
    print(f"qualifying frames {len(cand)}", flush=True)
    keys = ["token", "where", "dist", "u_e", "yaw_spread_deg", "iou_all", "iou_nearest_car", "acc_correct", "rejected", "box_h_px"]
    with open(REL / "results/v25/fig1b_candidates.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["rank"] + keys)
        for n, c in enumerate(cand, 1):
            w.writerow([n] + [f"{c[k]:.4f}" if isinstance(c[k], float) else c[k] for k in keys])
    top = cand[:12]
    fig, axes = plt.subplots(len(top), 2, figsize=(10, 2.0 * len(top)), gridspec_kw={"width_ratios": [1, 2.2]})
    axes = np.atleast_2d(axes)
    for n, (c, (a0, a1)) in enumerate(zip(top, axes), 1):
        img = c["f"]["img"]; u, v = c["uv"]
        x0, x1, y0, y1 = u.min(), u.max(), v.min(), v.max(); bw, bh = x1 - x0, y1 - y0
        a0.imshow(img); a0.add_patch(Rectangle((x0, y0), bw, bh, fill=False, ec=WRG, lw=1.2))
        a0.set_xlim(max(0, x0 - 2 * bw), min(1600, x1 + 2 * bw)); a0.set_ylim(min(900, y1 + 2 * bh), max(0, y0 - 2 * bh)); a0.axis("off")
        a1.imshow(img); a1.set_xlim(0, 1600); a1.set_ylim(rf.NUS_ROWS[1], rf.NUS_ROWS[0]); a1.axis("off")
        for k, b in zip(c["r"], c["f"]["boxes"]):
            if tab["u_e"][k] > tc:
                continue
            uu, vv, zz = c["f"]["project"](rf.corners_3d(b))
            if (zz > 0.1).all():
                a1.add_patch(Rectangle((uu.min(), vv.min()), uu.max() - uu.min(), vv.max() - vv.min(), fill=False,
                                       ec=COR if tab["y_A_iou0.5"][k] else WRG, lw=1.0))
        a0.set_title(f"{n}. {c['token'][:8]}  {c['dist']:.1f} m  u_e {c['u_e']:.3f}  yaw spread {c['yaw_spread_deg']:.1f} deg  "
                     f"IoU all {c['iou_all']:.2f}, car {c['iou_nearest_car']:.2f}  ({c['where']})", fontsize=8, loc="left")
    fig.tight_layout(); fig.savefig(REL / "figures/v25/fig1b_candidates.png", dpi=110)
    for n, c in enumerate(top, 1):
        print(n, c["token"], c["where"], f"{c['dist']:.1f} m", f"u_e {c['u_e']:.3f}", f"spread {c['yaw_spread_deg']:.1f}",
              f"IoU all {c['iou_all']:.3f} car {c['iou_nearest_car']:.3f}", f"acc correct {c['acc_correct']} rejected {c['rejected']}",
              f"box h {c['box_h_px']:.0f} px")


if __name__ == "__main__":
    main()

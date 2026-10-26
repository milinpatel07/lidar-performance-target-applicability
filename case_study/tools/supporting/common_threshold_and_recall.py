#!/usr/bin/env python3
"""
common_threshold_and_recall.py - from the cached per-detection tables, no experiment rerun:
  (1) common_threshold_outcomes.csv: the common threshold tau* (selected jointly over near and far) evaluated on
      the evaluation part of each distance condition: A_c(tau*), HB interval, outcome and R(tau*), both distance
      settings, both indicators, five splits, alpha 1e-2, 0.05, 0.1;
  (2) recall_denominators.json: annotated nuScenes cars counted by the correctness matching, and for comparison
      under a benchmark-style filter; detector score cut-offs from the configs;
  (3) the accepted wrong boxes of KITTI frame 004289 (frame figure) against the annotations.
Statistics from m1 in experiments/. Writes only below work/supporting_analyses.

Usage: python3 tools/supporting/common_threshold_and_recall.py
"""
import csv, importlib.util, json, pickle, re, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); import layout
REL = layout.WORK; RUM = layout.RUM; OUT = REL / "supporting_analyses"; OUT.mkdir(parents=True, exist_ok=True)
m6 = layout.load_analysis()
m1, m2, m3 = m6.m1, m6.m2, m6.m3
n1 = m3.m1
C = pickle.load(open(layout.CACHE, "rb"))
ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
kign = m6.subset(ktab, why == "")
LOG = []
def log(s): LOG.append(s); print(s, flush=True)


# ------------------------------------------------------------------ (1) tau* on the evaluation part of each condition
def eval_cells(mod, tab, car, ind, seed, cut):
    """The evaluation cells of m1.analyse (same split, cut and Cell)."""
    codes = mod.split_frames(tab["n_frames"], seed, mod.CFG); d = codes[tab["fpos"]]
    sel = np.isin(tab["cls"], [car]) & (d == 2); cid = (tab["rng"] > cut).astype(int)
    return {c: mod.Cell(tab["fpos"][sel & (cid == c)], tab[ind][sel & (cid == c)], tab["y_A_iou0.5"][sel & (cid == c)]) for c in (0, 1)}


rows = []
delta = m1.CFG["delta"]
for setting, mod, tab, car in (("KITTI distance (KITTI rule)", m1, kign, "Car"), ("nuScenes distance", n1, ntab, "car")):
    for ind in ("u_s", "u_e"):
        for seed in range(5):
            T = dict(tab); T["u"] = tab[ind]
            info, res, _ = mod.analyse(T, tab["y_A_iou0.5"], [car], 0.5, seed, mod.CFG, [1e-2, 0.05, 0.1], boot=False)
            cells = eval_cells(mod, tab, car, ind, seed, info["cut_m"])
            for r in res:
                ts = r["tau"]["star"]
                for c, cname in ((0, "near"), (1, "far")):
                    # consistency: R(tau_c) of the recorded c->c cell from analyse must equal the recomputed cell
                    own = next(x for x in r["cells"] if x["established"] == cname and x["applied"] == cname)
                    if "R_hat" in own and abs(cells[c].retention(own["tau"]) - own["R_hat"]) > 1e-12:
                        sys.exit(f"evaluation cell differs from m1.analyse: {setting} {ind} seed {seed} {cname}")
                    row = {"setting": setting, "indicator": ind, "seed": seed, "alpha": r["alpha"],
                           "exploratory": r["alpha"] in (0.05, 0.1), "condition": cname, "cut_m": info["cut_m"],
                           "tau_c": r["tau"][cname], "tau_star": ts, "n_eval_frames": cells[c].m}
                    if ts is None:
                        row["outcome"] = "no common threshold"
                    else:
                        a = cells[c].a_f(ts); S, n = a.sum(), cells[c].m
                        U, L = m1.hb_upper(S, n, delta / 2), m1.hb_lower(S, n, delta / 2)
                        row.update({"A_hat": S / n, "hb_L": L, "hb_U": U, "R_tau_star": cells[c].retention(ts),
                                    "outcome": "applies" if U <= r["alpha"] else ("does not apply" if L > r["alpha"] else "not determined")})
                        if r["tau"][cname] is not None:
                            row["R_tau_c"] = cells[c].retention(r["tau"][cname]); row["G"] = row["R_tau_c"] - row["R_tau_star"]
                    rows.append(row)
keys = []
for r in rows:
    keys += [k for k in r if k not in keys]
with open(OUT / "common_threshold_outcomes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
log(f"(1) wrote common_threshold_outcomes.csv ({len(rows)} rows)")
for r in rows:
    if r["seed"] == 0:
        log(f"   {r['setting']:28s} {r['indicator']} alpha {r['alpha']:<5g} {r['condition']:4s} tau* {r['tau_star']} "
            + (f"A {r['A_hat']:.4f} [{r['hb_L']:.4f}, {r['hb_U']:.4f}] R {r['R_tau_star']:.4f} G {r.get('G', float('nan')):.4f} {r['outcome']}"
               if "A_hat" in r else r["outcome"]))
tally = {}
for r in rows:
    k = (r["setting"], r["indicator"], r["alpha"], r["condition"]); tally.setdefault(k, {}); tally[k][r["outcome"]] = tally[k].get(r["outcome"], 0) + 1
log("   outcome counts over 5 splits:")
for k in sorted(tally):
    log(f"   {k[0]:28s} {k[1]} alpha {k[2]:<5g} {k[3]:4s}: " + ", ".join(f"{o} {n}" for o, n in sorted(tally[k].items())))

# ------------------------------------------------------------------ (2) nuScenes recall denominators
info = pickle.load(open(RUM / "data/nuscenes/v1.0-trainval/nuscenes_infos_10sweeps_val.pkl", "rb"))
fids = set(ntab["fids"]); n_all = n_pts = n_50 = n_both = 0
for e in info:
    if str(e.get("token")) not in fids:
        continue
    names = np.asarray(e.get("gt_names", [])); boxes = np.asarray(e.get("gt_boxes", np.zeros((0, 7))))
    pts = np.asarray(e.get("num_lidar_pts", np.full(len(names), -1)))
    k = names[: len(boxes)] == "car"
    d = np.hypot(boxes[:, 0], boxes[:, 1]) if len(boxes) else np.zeros(0)
    n_all += int(k.sum()); n_pts += int((k & (pts[: len(k)] > 0)).sum()); n_50 += int((k & (d <= 50)).sum())
    n_both += int((k & (pts[: len(k)] > 0) & (d <= 50)).sum())
tp = int(((ntab["cls"] == "car") & (ntab["y_A_iou0.5"] == 1)).sum())
log(f"(2) nuScenes: correct car detections {tp}; annotated cars used by the correctness matching (class filter only) {n_all}, recall {tp / n_all:.4f}")
log(f"   for information, not used by the matching: with >= 1 LiDAR point {n_pts}; within 50 m of the LiDAR {n_50}; both {n_both}")
cfg = {y.name: re.findall(r"SCORE_THRESH:\s*([0-9.]+)", y.read_text()) for y in sorted((RUM / "configs").glob("*.yaml"))}
for ds, key in (("KITTI", "kitti"), ("nuScenes", "nuscenes")):
    log(f"   score cut-off {ds}: " + ", ".join(f"{k} SCORE_THRESH {'/'.join(v)}" for k, v in cfg.items() if key in k))
json.dump({"correct_car_detections": tp, "annotated_cars_matching": n_all, "with_lidar_pts": n_pts, "within_50m": n_50,
           "both": n_both, "score_thresh": cfg}, open(OUT / "recall_denominators.json", "w"), indent=1)

# ------------------------------------------------------------------ (3) frame 004289: accepted wrong boxes against annotations
fid = "004289"; tau = float(json.load(open(REL / "data/tau_kitti_distance_split0.json"))["tau"]["near"])
sc = pickle.load(open(RUM / "detections/kitti_v2/scored_val.pkl", "rb"))
seeds = [{str(e.get("frame_id", "")): e for e in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/kitti_v2").glob("seed*_val.pkl"))]
md = [m2.member_detections(s[fid], sc["min_confidence"]) for s in seeds]
cons = m2.consensus_for_frame(md, sc["K"], sc["consensus_threshold"], sc["iou_threshold"])
kinfo = next(e for e in pickle.load(open(RUM / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl", "rb"))
             if f"{int(e.get('image_idx') or e['point_cloud']['lidar_idx']):06d}" == fid)
an = kinfo["annos"]; names = list(an["name"]); gb = np.asarray(an["gt_boxes_lidar"], np.float32); names3d = names[: len(gb)]
# correctness matching exactly as the table builder: all consensus detections in list order, eval classes only
ec = pickle.load(open(RUM / "detections/kitti_v2/frame_errors_cache.pkl", "rb"))["eval_classes"]
gt, _ = m1.load_gt(RUM / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl", ec); g = gt[fid]
M = m1.iou_matrix(cons, g["gt_boxes"], g["gt_names"])
thr = m1.CFG["iou_settings"]["A_iou0.5"]
y, _ = m1.greedy_match([{"cls": c["cls"]} for c in cons], M, g["gt_names"], thr)
match_of = {}
matched = set()
for i, d in enumerate(cons):          # replay greedy_match to record which annotation each correct detection took
    best, bi = 0.0, -1
    for gi in range(M.shape[1]):
        if gi in matched or g["gt_names"][gi] != d["cls"]:
            continue
        if M[i, gi] > best:
            best, bi = M[i, gi], gi
    if bi >= 0 and best >= thr[d["cls"]]:
        matched.add(bi); match_of[bi] = i
rows_t = np.where((ktab["cls"] == "Car") & (ktab["fpos"] == ktab["fids"].index(fid)))[0]
car_i = [i for i, c in enumerate(cons) if c["cls"] == "Car"]
assert len(car_i) == len(rows_t) and np.array_equal(y[car_i], ktab["y_A_iou0.5"][rows_t]), "replayed matching differs from the table"
log(f"(3) KITTI {fid}: annotations {list(zip(range(len(names3d)), names3d))}; tau_near(u_s) {tau:.5f}")
for j, (i, k) in enumerate(zip(car_i, rows_t)):
    if why[k] != "" or y[i] == 1 or ktab["u_s"][k] > tau:
        continue
    box = np.asarray(cons[i]["consensus_box"][:7], np.float32)
    ious = [(m1.rotated_iou_3d(box, gb[a]), a) for a in range(len(gb))]
    best, a = max(ious) if ious else (0.0, -1)
    bev = m1._bev_intersection_area(box, gb[a]) / min(box[3] * box[4], gb[a][3] * gb[a][4]) if a >= 0 else 0.0
    if a >= 0 and names3d[a] == "Car":
        gi = [x for x in range(len(g["gt_names"])) if np.allclose(g["gt_boxes"][x], gb[a])][0]
        if gi in match_of:
            o = match_of[gi]; ko = rows_t[car_i.index(o)]
            st = (f"annotated Car #{a} is already matched by detection {car_i.index(o)} "
                  f"({'accepted' if ktab['u_s'][ko] <= tau else 'rejected'}, IoU {M[o, gi]:.3f}): duplicate")
        else:
            st = f"annotated Car #{a} is not matched by any detection (IoU {best:.3f} below the 0.5 threshold): unmatched object"
    elif a >= 0 and best > 0:
        st = f"overlaps a {names3d[a]} annotation #{a} (not a car)"
    else:
        st = "overlaps no annotation: no annotated object"
    log(f"   accepted wrong detection {car_i.index(i)} at x {box[0]:.1f} y {box[1]:.1f}, u_s {ktab['u_s'][k]:.4f}: max 3D IoU {best:.3f} "
        f"to annotation #{a} ({names3d[a] if a >= 0 else '-'}), BEV overlap / smaller box {bev:.3f}; {st}")
    log("      3D IoU to every annotation: " + ", ".join(f"#{a2} {names3d[a2]} {v:.3f}" for v, a2 in ious if v > 0))
(OUT / "common_threshold_and_recall_log.txt").write_text("\n".join(LOG) + "\n")

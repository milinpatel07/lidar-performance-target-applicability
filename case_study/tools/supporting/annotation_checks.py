#!/usr/bin/env python3
"""
annotation_checks.py - from the cached per-detection tables, no experiment rerun:
  (a) composition of the KITTI annotated-car denominator of the merge recall (annotation_checks_log.txt);
  (b) unannotated_wrong_boxes.csv: every accepted wrong car detection (KITTI rule, split-0 tau_near(u_s) at
      alpha 0.1) that has no annotated car within 3D IoU 0.1 and lies fully inside the camera image, with its
      overlap with annotations of other classes.
Writes only below work/supporting_analyses.

Usage: python3 tools/supporting/annotation_checks.py   (after tools/export_tables.py)
"""
import csv, json, pickle, struct, sys
from pathlib import Path
from collections import Counter
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); import layout
REL = layout.WORK; RUM = layout.RUM; OUT = REL / "supporting_analyses"; OUT.mkdir(parents=True, exist_ok=True)
m6 = layout.load_analysis()
m1, m2 = m6.m1, m6.m2
C = pickle.load(open(layout.CACHE, "rb")); ktab, why = C["ktab"], C["why"]
LOG = []
def log(s): LOG.append(s); print(s, flush=True)

# ------------------------------------------------------------------ (a)
f_info = RUM / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl"
info = pickle.load(open(f_info, "rb"))
ec = pickle.load(open(RUM / "detections/kitti_v2/frame_errors_cache.pkl", "rb"))["eval_classes"]
gt, skipped = m1.load_gt(f_info, ec)
fids = set(ktab["fids"])
names_all, dc_last, car_pts0, car_rng, car_trunc, car_occ = Counter(), True, 0, [], [], []
annos = {}
for e in info:
    fid = f"{int(e.get('image_idx') or e['point_cloud']['lidar_idx']):06d}"
    if fid not in fids:
        continue
    a = e["annos"]; nm = list(a["name"]); annos[fid] = a
    names_all.update(nm)
    nb = len(a["gt_boxes_lidar"])
    if any(n == "DontCare" for n in nm[:nb]) or any(n != "DontCare" for n in nm[nb:]):
        dc_last = False
    for i, n in enumerate(nm[:nb]):
        if n == "Car":
            car_pts0 += int(a.get("num_points_in_gt", np.ones(nb))[i] <= 0)
            car_rng.append(float(np.hypot(*a["gt_boxes_lidar"][i][:2])))
            car_trunc.append(float(a["truncated"][i])); car_occ.append(int(a["occluded"][i]))
n_den = sum(sum(1 for n in gt[f]["gt_names"] if n == "Car") for f in fids if f in gt)
log(f"(a) KITTI denominator: {n_den} annotated cars over {len(fids)} validation frames (load_gt skipped {skipped} frames)")
log(f"   annotation names in these frames: {dict(names_all)}")
log(f"   gt_boxes_lidar holds every non-DontCare annotation, DontCare entries last: {dc_last}; so DontCare is excluded by the box count, "
    f"and the class filter {list(ec)} keeps only 'Car' for cars (Van, Truck, Misc, ... not in the denominator)")
log(f"   no range, point, truncation, occlusion or height filter: cars with 0 LiDAR points {car_pts0}; range of annotated cars "
    f"{min(car_rng):.1f}-{max(car_rng):.1f} m; truncated > 0.5: {sum(t > 0.5 for t in car_trunc)}; occlusion level 2 or 3: "
    f"{sum(o >= 2 for o in car_occ)}")
assert n_den == len(car_rng) == 14385

# ------------------------------------------------------------------ (b)
tau = float(json.load(open(REL / "data/tau_kitti_distance_split0.json"))["tau"]["near"])
cut = float(json.load(open(REL / "data/tau_kitti_distance_split0.json"))["cut_m"])
y = ktab["y_A_iou0.5"]; car = ktab["cls"] == "Car"
cand = car & (why == "") & (y == 0) & (ktab["u_s"] <= tau)
frames = sorted(set(ktab["fpos"][cand].tolist()))
log(f"(b) tau_near(u_s) {tau:.5f} (split 0, alpha 0.1, KITTI rule), boundary {cut} m; accepted wrong scored car detections {int(cand.sum())} "
    f"in {len(frames)} frames")
sc = pickle.load(open(RUM / "detections/kitti_v2/scored_val.pkl", "rb"))
seeds = [{str(e.get("frame_id", "")): e for e in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/kitti_v2").glob("seed*_val.pkl"))]
codes0 = m1.split_frames(ktab["n_frames"], 0, m1.CFG)
rows = []
for fpos in frames:
    fid = ktab["fids"][fpos]
    rr = np.where(car & (ktab["fpos"] == fpos))[0]
    md = [m2.member_detections(s[fid], sc["min_confidence"]) for s in seeds]
    cons = [c for c in m2.consensus_for_frame(md, sc["K"], sc["consensus_threshold"], sc["iou_threshold"]) if c["cls"] == "Car"]
    if len(cons) != len(rr) or not np.allclose([c["range"] for c in cons], ktab["rng"][rr], atol=1e-4):
        sys.exit(f"rebuilt boxes of {fid} do not align with the table")
    a = annos[fid]; nb = len(a["gt_boxes_lidar"]); nm = list(a["name"])[:nb]; gb = np.asarray(a["gt_boxes_lidar"], np.float32)
    P2, R0, Tr = m6.read_calib(RUM / f"data/kitti/training/calib/{fid}.txt")
    with open(RUM / f"data/kitti/training/image_2/{fid}.png", "rb") as f:
        Wd, Ht = struct.unpack(">II", f.read(24)[16:24])
    for k, c in zip(rr, cons):
        if not cand[k]:
            continue
        box = np.asarray(c["consensus_box"][:7], np.float32)
        iou_car = max([m1.rotated_iou_3d(box, gb[i]) for i in range(nb) if nm[i] == "Car"], default=0.0)
        if iou_car >= 0.1:
            continue
        p = m6.corners3d(box); cam = (R0 @ (Tr @ np.c_[p, np.ones(8)].T)).T; im = (P2 @ np.c_[cam, np.ones(8)].T).T
        u, v = im[:, 0] / im[:, 2], im[:, 1] / im[:, 2]
        if not ((cam[:, 2] > 0.1).all() and (u >= 0).all() and (u < Wd).all() and (v >= 0).all() and (v < Ht).all()):
            continue
        other = [(m1.rotated_iou_3d(box, gb[i]), nm[i]) for i in range(nb) if nm[i] != "Car"]
        best_other = max(other, default=(0.0, "-"))
        rows.append({"frame": fid, "distance_m": round(float(ktab["rng"][k]), 2), "zone": "far" if ktab["rng"][k] > cut else "near",
                     "u_s": round(float(ktab["u_s"][k]), 5), "max_iou_annotated_car": round(iou_car, 3),
                     "max_iou_other_annotation": round(float(best_other[0]), 3), "other_class": best_other[1] if best_other[0] > 0 else "",
                     "part_split0": {0: "grid", 1: "select", 2: "eval"}[int(codes0[fpos])],
                     "accepted_correct_in_frame": int((car[rr] & (why[rr] == "") & (y[rr] == 1) & (ktab["u_s"][rr] <= tau)).sum()),
                     "accepted_wrong_in_frame": int(cand[rr].sum())})
with open(OUT / "unannotated_wrong_boxes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["frame"]); w.writeheader(); w.writerows(rows)
log(f"   qualifying boxes {len(rows)} in {len(set(r['frame'] for r in rows))} frames (near {sum(r['zone'] == 'near' for r in rows)}, "
    f"far {sum(r['zone'] == 'far' for r in rows)}); with another annotation at IoU > 0: {sum(bool(r['other_class']) for r in rows)}")
for r in rows:
    log(f"   {r['frame']} {r['distance_m']:6.2f} m {r['zone']:4s} u_s {r['u_s']:.5f} IoU car {r['max_iou_annotated_car']:.3f} "
        f"other {r['other_class'] or '-'} {r['max_iou_other_annotation']:.3f} ({r['part_split0']}; accepted correct/wrong in frame "
        f"{r['accepted_correct_in_frame']}/{r['accepted_wrong_in_frame']})")
(OUT / "annotation_checks_log.txt").write_text("\n".join(LOG) + "\n")

#!/usr/bin/env python3
"""
frame_candidates.py - candidate KITTI frames for the frame figure and a blind sample for a visual check, from the
cached tables and the dataset images; no experiment rerun. Needs the outputs of retention_and_causes.py,
common_threshold_and_recall.py and annotation_checks.py in work/supporting_analyses.
  (1) frame_candidates_ranked.csv: unannotated accepted wrong boxes (no annotation of any class) at far distance,
      in frames with >= 3 accepted correct, >= 1 rejected and <= 2 accepted wrong detections, ranked by the pixel
      distance of the projected box from the image border;
  (2) work/figures/frame_candidates_top24.png: contact sheet of the top 24 (crop and full image);
  (3) nuscenes_frame_wrong_boxes.csv: the accepted wrong boxes of the nuScenes frame of the frame figure against all
      annotations, with a front-camera crop (work/figures/nuscenes_frame_wrong_crop.png);
  (4) blind_sample_50.csv and work/figures/blind_sample_50.png: 25 near and 25 far unannotated boxes (numpy
      default_rng(0)), numbered crops without indicator value or distance, for a visual check;
  (5) applicable_cells_1e-2.csv: retention and outcome of every applicable cell at alpha 1e-2 for the own-condition,
      transferred and common thresholds.
The PNG files contain dataset images and are not part of the repository.

Usage: python3 tools/supporting/frame_candidates.py
"""
import csv, importlib.util, json, pickle, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); import layout
W = layout.RESULTS; REL = layout.WORK; RUM = layout.RUM; META = layout.NUSC_META
OUT = REL / "supporting_analyses"; FIG = REL / "figures"; FIG.mkdir(parents=True, exist_ok=True)
m6 = layout.load_analysis()
m1, m2, m3 = m6.m1, m6.m2, m6.m3
OK, DNA, GREY = "#2E7D32", "#C62828", "#9AA0A6"
EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
plt.rcParams.update({"font.family": "serif", "font.size": 6})
C = pickle.load(open(layout.CACHE, "rb")); ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
LOG = []
def log(s): LOG.append(s); print(s, flush=True)

tj = json.load(open(REL / "data/tau_kitti_distance_split0.json")); tau = float(tj["tau"]["near"])
car = ktab["cls"] == "Car"; y = ktab["y_A_iou0.5"]; scored = why == ""
scK = pickle.load(open(RUM / "detections/kitti_v2/scored_val.pkl", "rb"))
seedsK = [{str(e.get("frame_id", "")): e for e in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/kitti_v2").glob("seed*_val.pkl"))]


def kitti_frame(fid):
    """Table rows, rebuilt boxes, 2D projections (u, v per corner, depth) and image of one KITTI frame."""
    fpos = ktab["fids"].index(fid); rr = np.where(car & (ktab["fpos"] == fpos))[0]
    md = [m2.member_detections(s[fid], scK["min_confidence"]) for s in seedsK]
    cons = [c for c in m2.consensus_for_frame(md, scK["K"], scK["consensus_threshold"], scK["iou_threshold"]) if c["cls"] == "Car"]
    if len(cons) != len(rr) or not np.allclose([c["range"] for c in cons], ktab["rng"][rr], atol=1e-4):
        sys.exit(f"rebuilt boxes of {fid} do not align with the table")
    P2, R0, Tr = m6.read_calib(RUM / f"data/kitti/training/calib/{fid}.txt")
    proj = []
    for c in cons:
        p = m6.corners3d(np.asarray(c["consensus_box"][:7], float)); cam = (R0 @ (Tr @ np.c_[p, np.ones(8)].T)).T
        im = (P2 @ np.c_[cam, np.ones(8)].T).T
        proj.append((im[:, 0] / im[:, 2], im[:, 1] / im[:, 2], cam[:, 2]))
    return rr, proj, mpimg.imread(str(RUM / f"data/kitti/training/image_2/{fid}.png"))


def find_row(rr, d, u):
    k = [i for i, r in enumerate(rr) if abs(ktab["rng"][r] - d) < 0.006 and abs(ktab["u_s"][r] - u) < 1e-5]
    assert len(k) == 1, "box not identified"
    return k[0]


def wire(ax, pr, col, lw):
    u, v, z = pr
    if (z < 0.1).any():
        return
    for p, q in EDGES:
        ax.plot(u[[p, q]], v[[p, q]], color=col, lw=lw, solid_capstyle="round")


def crop(ax, img, pr, col=DNA):
    u, v, _ = pr; H, Wd = img.shape[:2]
    w, h = u.max() - u.min(), v.max() - v.min()
    ax.imshow(img); wire(ax, pr, col, 0.8)
    ax.set_xlim(max(0, u.min() - 2 * w), min(Wd, u.max() + 2 * w)); ax.set_ylim(min(H, v.max() + 2 * h), max(0, v.min() - 2 * h))
    ax.set_xticks([]); ax.set_yticks([])


# ------------------------------------------------------------------ (1) candidates
df = pd.read_csv(OUT / "unannotated_wrong_boxes.csv", dtype={"frame": str})
df = df[df.other_class.isna()]
n1536 = len(df)
cand = df[(df.zone == "far") & (df.accepted_correct_in_frame >= 3) & (df.accepted_wrong_in_frame <= 2)].copy()
rej, margin = [], []
for r in cand.itertuples():
    fpos = ktab["fids"].index(r.frame); m = car & scored & (ktab["fpos"] == fpos)
    rej.append(int((m & (ktab["u_s"] > tau)).sum()))
cand["rejected_in_frame"] = rej
cand = cand[cand.rejected_in_frame >= 1].copy()
for r in cand.itertuples():
    rr, proj, img = kitti_frame(r.frame); u, v, _ = proj[find_row(rr, r.distance_m, r.u_s)]; H, Wd = img.shape[:2]
    margin.append(float(min(u.min(), Wd - u.max(), v.min(), H - v.max())))
cand["border_distance_px"] = margin
cand = cand.sort_values(["border_distance_px", "frame"], ascending=[False, True])
cand.to_csv(OUT / "frame_candidates_ranked.csv", index=False)
log(f"(1) unannotated boxes (no annotation of any class at IoU > 0 besides cars below 0.1): {n1536}; of these with an annotated car at "
    f"0 < IoU < 0.1: {int((df.max_iou_annotated_car > 0).sum())}. Far, >= 3 accepted correct, >= 1 rejected, <= 2 accepted wrong: "
    f"{len(cand)} boxes in {cand.frame.nunique()} frames; ranked by pixel distance of the projected box from the image border")
for i, r in enumerate(cand.head(24).itertuples(), 1):
    log(f"   {i:2d} {r.frame} {r.distance_m:6.2f} m u_s {r.u_s:.5f} border {r.border_distance_px:5.1f} px; accepted correct/wrong "
        f"{r.accepted_correct_in_frame}/{r.accepted_wrong_in_frame}, rejected {r.rejected_in_frame} ({r.part_split0})")


# ------------------------------------------------------------------ (2) contact sheet, top 24
def sheet(rows, path, labels, with_thumb):
    n = len(rows); cols = 4; rws = int(np.ceil(n / cols)); per = 2 if with_thumb else 1
    fig, axes = plt.subplots(rws * per, cols, figsize=(cols * 2.6, rws * per * (1.15 if with_thumb else 1.5)),
                             **({"gridspec_kw": {"height_ratios": [1.6, 0.7] * rws}} if with_thumb else {}))
    axes = np.atleast_2d(axes)
    for ax in axes.ravel():
        ax.axis("off")
    for j, (r, lab) in enumerate(zip(rows, labels)):
        rr, proj, img = kitti_frame(r.frame); k = find_row(rr, r.distance_m, r.u_s)
        a = axes[(j // cols) * per, j % cols]; a.axis("on"); crop(a, img, proj[k]); a.set_title(lab, pad=1.5)
        if with_thumb:
            t = axes[(j // cols) * per + 1, j % cols]; t.axis("on"); t.imshow(img)
            for i, row in enumerate(rr):
                if scored[row] and ktab["u_s"][row] <= tau:
                    wire(t, proj[i], OK if y[row] == 1 else DNA, 0.5)
            t.set_xlim(0, img.shape[1]); t.set_ylim(img.shape[0], 0); t.set_xticks([]); t.set_yticks([])
    fig.tight_layout(pad=0.3, h_pad=0.4, w_pad=0.3); fig.savefig(path, dpi=200); plt.close(fig)
    log(f"   wrote {path.name}")


top = list(cand.head(24).itertuples())
sheet(top, FIG / "frame_candidates_top24.png", [f"{i}. {r.frame}, {r.distance_m:.1f} m, $u_s$ {r.u_s:.3f}" for i, r in enumerate(top, 1)], True)

# ------------------------------------------------------------------ (3) nuScenes frame of the frame figure
tok = "703ac7e5928a41c7a3138afa74e157ad"
C_rec = pd.read_csv(W / "m6_five_splits/C_weather_nuscenes.csv")
tauN = float(C_rec[(C_rec.indicator == "u_e") & (C_rec.seed == 0) & (C_rec.alpha == 0.1) & (C_rec.established == "clear") & (C_rec.applied == "rain")].tau.iloc[0])
NUS = RUM / "data/nuscenes/v1.0-trainval"
infos = {e["token"]: e for e in pickle.load(open(NUS / "nuscenes_infos_10sweeps_val.pkl", "rb"))}
e = infos[tok]; fp = ntab["fids"].index(tok); rr = np.where((ntab["cls"] == "car") & (ntab["fpos"] == fp))[0]
scN = pickle.load(open(RUM / "detections/nuscenes/scored_val.pkl", "rb"))
seedsN = [{m3._entry_token(x): x for x in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/nuscenes").glob("seed*_val.pkl"))]
md = [m3.member_detections(s[tok], scN["min_confidence"]) for s in seedsN]
cons = [c for c in m3.consensus_for_frame(md, scN["K"], scN["consensus_threshold"], scN["iou_threshold"]) if c["cls"] == "car"]
assert len(cons) == len(rr) and np.allclose([c["range"] for c in cons], ntab["rng"][rr], atol=1e-4)
gb = np.asarray(e["gt_boxes"])[:, :7].astype(np.float32); gn = list(e["gt_names"])[: len(gb)]
sd = next(s for s in json.load(open(META / "sample_data.json")) if s["filename"] == e["cam_front_path"])
pose = next(p for p in json.load(open(META / "ego_pose.json")) if p["token"] == sd["ego_pose_token"])
cs = next(c for c in json.load(open(META / "calibrated_sensor.json")) if c["token"] == sd["calibrated_sensor_token"])


def qR(q):
    w, x, yq, z = q
    return np.array([[1 - 2 * (yq * yq + z * z), 2 * (x * yq - z * w), 2 * (x * z + yq * w)], [2 * (x * yq + z * w), 1 - 2 * (x * x + z * z), 2 * (yq * z - x * w)],
                     [2 * (x * z - yq * w), 2 * (yq * z + x * w), 1 - 2 * (x * x + yq * yq)]])


def Tf(R, t):
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t; return T


T = np.linalg.inv(Tf(qR(cs["rotation"]), cs["translation"])) @ np.linalg.inv(Tf(qR(pose["rotation"]), pose["translation"])) \
    @ np.linalg.inv(e["car_from_global"]) @ np.linalg.inv(e["ref_from_car"])        # as fig_scenes.cam_from_lidar
K = np.asarray(cs["camera_intrinsic"]); imgN = mpimg.imread(str(NUS / e["cam_front_path"]))
nrows = []
fig, axes = plt.subplots(1, 3, figsize=(7.8, 1.9)); [a.axis("off") for a in axes]
j = 0
for k, c in zip(rr, cons):
    if not (ntab["u_e"][k] <= tauN and ntab["y_A_iou0.5"][k] == 0):
        continue
    box = np.asarray(c["consensus_box"][:7], np.float32)
    ious = sorted(((m1.rotated_iou_3d(box, gb[i]), gn[i], i) for i in range(len(gb))), reverse=True)
    dmin = min((float(np.hypot(*(gb[i][:2] - box[:2]))), gn[i]) for i in range(len(gb))) if len(gb) else (np.nan, "-")
    p = m6.corners3d(box); cam = (T @ np.c_[p, np.ones(8)].T).T; uvw = (K @ cam[:, :3].T).T
    pr = (uvw[:, 0] / uvw[:, 2], uvw[:, 1] / uvw[:, 2], cam[:, 2])
    inside = bool((cam[:, 2] > 0.5).all() and (pr[0] >= 0).all() and (pr[0] < 1600).all() and (pr[1] >= 0).all() and (pr[1] < 900).all())
    nrows.append({"token": tok, "distance_m": round(float(ntab["rng"][k]), 2), "u_e": round(float(ntab["u_e"][k]), 5),
                  "max_iou_any": round(float(ious[0][0]), 3) if ious else 0.0, "class_max_iou": ious[0][1] if ious and ious[0][0] > 0 else "",
                  "nearest_annotation_centre_m": round(dmin[0], 2), "nearest_class": dmin[1], "in_front_camera": inside})
    log(f"(3) nuScenes {tok[:8]} accepted wrong box at {ntab['rng'][k]:.2f} m, u_e {ntab['u_e'][k]:.4f} (tau_clear {tauN:.5f}): max 3D IoU "
        f"{nrows[-1]['max_iou_any']:.3f} ({nrows[-1]['class_max_iou'] or 'none'}); nearest annotation centre {dmin[0]:.2f} m ({dmin[1]}); "
        f"inside CAM_FRONT: {inside}")
    if inside and j < 3:
        crop(axes[j], imgN, pr); axes[j].axis("on"); axes[j].set_title(f"{tok[:8]}, {ntab['rng'][k]:.1f} m, $u_e$ {ntab['u_e'][k]:.3f}", pad=1.5); j += 1
fig.tight_layout(pad=0.3); fig.savefig(FIG / "nuscenes_frame_wrong_crop.png", dpi=200); plt.close(fig)
pd.DataFrame(nrows).to_csv(OUT / "nuscenes_frame_wrong_boxes.csv", index=False)

# ------------------------------------------------------------------ (4) blind sample of 50 unannotated boxes
rng = np.random.default_rng(0)
samp = pd.concat([df[df.zone == z].iloc[rng.choice((df.zone == z).sum(), 25, replace=False)] for z in ("near", "far")])
samp = samp.iloc[rng.permutation(len(samp))].reset_index(drop=True); samp.insert(0, "number", range(1, 51))
samp.to_csv(OUT / "blind_sample_50.csv", index=False)
sheet(list(samp.itertuples()), FIG / "blind_sample_50.png", [str(n) for n in samp.number], False)
log(f"(4) blind sample: 25 near and 25 far of the {n1536} unannotated boxes, numpy default_rng(0), order shuffled; key in blind_sample_50.csv")

# ------------------------------------------------------------------ (5) applicable cells at 1e-2
a1 = pd.read_csv(OUT / "retention_applicable_cells.csv"); a1 = a1[a1.alpha == 0.01]
a1 = a1.assign(threshold=np.where(a1.transfer, "transferred tau_c", "own tau_c"), condition=a1.applied)
a5 = pd.read_csv(OUT / "common_threshold_outcomes.csv"); a5 = a5[(a5.alpha == 0.01) & (a5.outcome == "applies")]
a5 = a5.assign(variant="frame", threshold="tau*", established="near+far", applied=a5.condition, R_hat=a5.R_tau_star)
cols = ["setting", "variant", "threshold", "indicator", "seed", "established", "applied", "outcome", "A_hat", "hb_L", "hb_U", "R_hat"]
ap = pd.concat([a1[cols], a5[cols]]).sort_values("R_hat", ascending=False)
ap.to_csv(OUT / "applicable_cells_1e-2.csv", index=False)
fr = ap[ap.variant == "frame"]
log(f"(5) applicable cells at 1e-2: {len(ap)} ({len(fr)} frame split); maximum R {ap.R_hat.max():.4f}: " + ap.iloc[0][["setting", "variant", "threshold", "indicator", "seed", "established", "applied"]].to_dict().__repr__())
log("   maximum R per threshold type (frame split): " + "; ".join(f"{t} {g.R_hat.max():.4f} ({g.iloc[0].setting}, {g.iloc[0].indicator}, {g.iloc[0].established}->{g.iloc[0].applied}, split {g.iloc[0].seed})"
                                                                   for t, g in fr.groupby("threshold")))
k = a5[(a5.setting.str.startswith("KITTI")) & (a5.indicator == "u_e") & (a5.condition == "near")]
log("   KITTI u_e near tau*, applicable: " + "; ".join(f"split {r.seed}: R(tau*) {r.R_tau_star:.4f}, A {r.A_hat:.4f} [{r.hb_L:.4f}, {r.hb_U:.4f}]" for r in k.itertuples()))
(OUT / "frame_candidates_log.txt").write_text("\n".join(LOG) + "\n")

#!/usr/bin/env python3
"""render_frames.py (render-0.1, 2026-10-20) - any KITTI or nuScenes validation frame in the layout of Fig. 1 of main_v25.

Per frame one PNG with three stacked views (camera with the projected merged car detections; bird's-eye view with LiDAR
points, annotated cars, near/far boundary and two numbered detections with their member boxes and zoom insets; u_s strip
with the thresholds selected at near and at far distance) and a header line with the frame, its scene or drive and counts.
Optionally one MP4 of all rendered frames (ffmpeg, in the container).

Settings as in Fig. 1: spatial indicator u_s, car detections, split 0, thresholds selected at the exploratory limit 0.1
(release/data/tau_<dataset>_distance_split0.json); a detection is accepted if u_s <= threshold selected at near distance.
KITTI: KITTI rule (detections it removes are drawn dotted grey, not scored). Numbered detections: 1 = accepted correct near
detection with the lowest u_s; 2 = accepted wrong detection seen by the camera (far preferred, then no annotated car under it, then lowest
u_s). A frame without one of them is drawn without that inset.

Frame selection (one of): --frames ID ... | --frame-list FILE (one id per line) | --drive NAME (KITTI raw drive, e.g.
2011_09_26_drive_0005; the object frames of that drive in recording order) | --scene NAME (nuScenes scene name or token;
key frames in time order) | --all. --limit N keeps the first N.
KITTI object frames of one drive are a sparse sample of the drive, so a KITTI drive video jumps; nuScenes key frames are 2 Hz.

Usage (server container, project root mounted at /work, /rum and /heinrich_nuscenes read-only):
  python3 release/code/tools/render_frames.py --dataset kitti --frames 005345 000323 --out release/frames/kitti_test
  python3 release/code/tools/render_frames.py --dataset kitti --drive 2011_09_26_drive_0005 --mp4
  python3 release/code/tools/render_frames.py --dataset nuscenes --scene scene-0003 --mp4 --fps 2
MP4: MPEG-4 part 2 (the container ffmpeg has no working H.264 encoder); plays in VLC and common players.
Writes <out>/<NNNNN>_<frame>.png, <out>/index.csv (frame, scene or drive, counts) and, with --mp4, <out>/<out name>.mp4.
"""
import argparse, csv, importlib.util, json, pickle, subprocess, sys, time
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Polygon, Rectangle
from matplotlib.lines import Line2D

VERSION = "render-0.1"
W = Path("/work"); REL = W / "release"; RUM = Path("/rum"); CODE = REL / "code/m7v2"
META = Path("/heinrich_nuscenes/v1.0-trainval"); NUS_ROOT = RUM / "data/nuscenes/v1.0-trainval"
sys.path.insert(0, str(CODE))
spec = importlib.util.spec_from_file_location("m6", str(CODE / "m6_protocol_seeds_weather.py"))
m6 = importlib.util.module_from_spec(spec); sys.modules["m6"] = m6; spec.loader.exec_module(m6)
m1, m2, m3 = m6.m1, m6.m2, m6.m3
MM = 1 / 25.4
COR, WRG, GTF, GTE, PTS, NS = "#0072B2", "#D55E00", "#E0E0E0", "#757575", "#BDBDBD", "#9E9E9E"
plt.rcParams.update({"font.family": "serif", "font.serif": ["STIXGeneral"], "mathtext.fontset": "stix", "font.size": 7,
                     "axes.labelsize": 7, "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6, "pdf.fonttype": 42,
                     "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0.5})
NUS_ROWS = (320, 805)   # CAM_FRONT rows shown: same aspect as the KITTI image (1600 / 485 = 1242 / 375)


def corners_xy(b):
    x, y, _, l, w, _, yaw = [float(v) for v in b[:7]]
    c, s = np.cos(yaw), np.sin(yaw); dx = np.array([l, l, -l, -l]) / 2; dy = np.array([w, -w, -w, w]) / 2
    return np.column_stack([c * dx - s * dy + x, s * dx + c * dy + y])


def corners_3d(b):
    xy = corners_xy(b); z, h = float(b[2]), float(b[5])
    return np.vstack([np.column_stack([xy, np.full(4, z - h / 2)]), np.column_stack([xy, np.full(4, z + h / 2)])])


def quat_to_R(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def T_from(R, t):
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t; return T


def hom(T, p):
    return (T @ np.c_[p, np.ones(len(p))].T).T[:, :3]


def to_car(T, b):
    """Box (x, y, z, l, w, h, yaw) from the LiDAR frame into the vehicle frame given by the 4x4 transform T."""
    b = np.array(b, float).reshape(-1, 7).copy()
    b[:, :3] = hom(T, b[:, :3]); b[:, 6] += np.arctan2(T[1, 0], T[0, 0])
    return b


# ------------------------------------------------------------------ datasets
class Kitti:
    name, car, zmin, rows = "KITTI", "Car", -1.45, None   # zmin: ground removal (sensor 1.73 m above the road)

    def __init__(self, C):
        self.tab, self.why = C["ktab"], C["why"]
        self.scored = pickle.load(open(RUM / "detections/kitti_v2/scored_val.pkl", "rb"))
        self.seeds = [{str(e.get("frame_id", "")): e for e in pickle.load(open(f, "rb"))}
                      for f in sorted((RUM / "detections/kitti_v2").glob("seed*_val.pkl"))]
        self.infos = {f"{int(e.get('image_idx') or e['point_cloud']['lidar_idx']):06d}": e
                      for e in pickle.load(open(RUM / "third_party/OpenPCDet/data/kitti/kitti_infos_val.pkl", "rb"))}
        dk = REL / "ext/kitti_devkit/mapping"
        rand = [int(v) for v in (dk / "train_rand.txt").read_text().strip().split(",")]
        mp = [l.split() for l in (dk / "train_mapping.txt").read_text().splitlines() if l.strip()]
        self.drive = {f: (mp[rand[int(f)] - 1][1], int(mp[rand[int(f)] - 1][2])) for f in self.tab["fids"]}

    def select(self, a):
        if a.drive:
            fr = [f for f in self.tab["fids"] if a.drive in self.drive[f][0]]
            return sorted(fr, key=lambda f: self.drive[f][1])
        return list(self.tab["fids"])

    def where(self, fid):
        d, n = self.drive[fid]; return f"drive {d.replace('_sync', '')}, raw frame {n}"

    def frame(self, fid):
        cons = m2.consensus_for_frame([m2.member_detections(s[fid], self.scored["min_confidence"]) for s in self.seeds],
                                      self.scored["K"], self.scored["consensus_threshold"], self.scored["iou_threshold"])
        P2, R0, Tr = m6.read_calib(RUM / f"data/kitti/training/calib/{fid}.txt")
        img = mpimg.imread(str(RUM / f"data/kitti/training/image_2/{fid}.png"))[..., :3]
        pts = np.fromfile(str(RUM / f"data/kitti/training/velodyne/{fid}.bin"), np.float32).reshape(-1, 4)[:, :3]
        an = self.infos[fid]["annos"]; gb = np.asarray(an["gt_boxes_lidar"]).reshape(-1, 7); gn = list(an["name"])[: len(gb)]

        def project(p):
            cam = (R0 @ (Tr @ np.c_[p, np.ones(len(p))].T)).T; im = (P2 @ np.c_[cam, np.ones(len(cam))].T).T
            return im[:, 0] / im[:, 2], im[:, 1] / im[:, 2], cam[:, 2]
        boxes = [np.asarray(c["consensus_box"][:7], float) for c in cons if c["cls"] == self.car]
        members = [np.asarray(c["member_boxes"])[:, :7] for c in cons if c["cls"] == self.car]
        return {"img": img, "pts": pts, "project": project, "boxes": boxes, "members": members,
                "gt": [gb[i] for i in range(len(gb)) if gn[i] == "Car"], "rule": lambda k: str(self.why[k]),
                "fov_half": np.arctan(img.shape[1] / 2 / P2[0, 0]), "rng": [c["range"] for c in cons if c["cls"] == self.car]}


class Nusc:
    name, car, zmin, rows = "nuScenes", "car", 0.3, NUS_ROWS   # vehicle frame: origin on the ground

    def __init__(self, C):
        self.tab = C["ntab"]
        self.scored = pickle.load(open(RUM / "detections/nuscenes/scored_val.pkl", "rb"))
        self.seeds = [{m3._entry_token(e): e for e in pickle.load(open(f, "rb"))}
                      for f in sorted((RUM / "detections/nuscenes").glob("seed*_val.pkl"))]
        self.infos = {e["token"]: e for e in pickle.load(open(NUS_ROOT / "nuscenes_infos_10sweeps_val.pkl", "rb"))}
        val = set(self.tab["fids"])
        self.sample = {s["token"]: s for s in json.load(open(META / "sample.json")) if s["token"] in val}
        self.scene = {s["token"]: s for s in json.load(open(META / "scene.json"))}
        self.sd = None; self.poses = None; self.calibs = None

    def select(self, a):
        fr = list(self.tab["fids"])
        if a.scene:
            fr = [f for f in fr if a.scene in (self.scene[self.sample[f]["scene_token"]]["name"], self.sample[f]["scene_token"])]
        return sorted(fr, key=lambda f: (self.scene[self.sample[f]["scene_token"]]["name"], self.sample[f]["timestamp"]))

    def where(self, tok):
        return self.scene[self.sample[tok]["scene_token"]]["name"]

    def frame(self, tok):
        if self.sd is None:   # camera calibration of every validation key frame, read once
            need = {self.infos[t]["cam_front_path"]: t for t in self.tab["fids"]}
            self.sd = {need[s["filename"]]: s for s in json.load(open(META / "sample_data.json")) if s["filename"] in need}
            self.poses = {p["token"]: p for p in json.load(open(META / "ego_pose.json"))}
            self.calibs = {c["token"]: c for c in json.load(open(META / "calibrated_sensor.json"))}
        e, sd = self.infos[tok], self.sd[tok]
        p, cs = self.poses[sd["ego_pose_token"]], self.calibs[sd["calibrated_sensor_token"]]
        T_global_lidar = np.linalg.inv(e["car_from_global"]) @ np.linalg.inv(e["ref_from_car"])
        T_cam_lidar = (np.linalg.inv(T_from(quat_to_R(cs["rotation"]), cs["translation"]))
                       @ np.linalg.inv(T_from(quat_to_R(p["rotation"]), p["translation"])) @ T_global_lidar)
        car_from_lidar = np.linalg.inv(e["ref_from_car"]); T_cam_car = T_cam_lidar @ e["ref_from_car"]
        K = np.asarray(cs["camera_intrinsic"])
        cons = m3.consensus_for_frame([m3.member_detections(s[tok], self.scored["min_confidence"]) for s in self.seeds],
                                      self.scored["K"], self.scored["consensus_threshold"], self.scored["iou_threshold"])
        cons = [c for c in cons if c["cls"] == self.car]
        img = mpimg.imread(str(NUS_ROOT / e["cam_front_path"]))
        img = (img / 255.0 if img.dtype == np.uint8 else img)[..., :3]
        pts = hom(car_from_lidar, np.fromfile(str(NUS_ROOT / e["lidar_path"]), np.float32).reshape(-1, 5)[:, :3])
        gt = [to_car(car_from_lidar, g)[0] for g, n in zip(np.asarray(e["gt_boxes"])[:, :7], e["gt_names"]) if n == "car"]

        def project(q):
            c = hom(T_cam_car, q); uv = (K @ c.T).T
            with np.errstate(divide="ignore", invalid="ignore"):
                return uv[:, 0] / uv[:, 2], uv[:, 1] / uv[:, 2], c[:, 2]
        return {"img": img, "pts": pts, "project": project, "boxes": [to_car(car_from_lidar, c["consensus_box"][:7])[0] for c in cons],
                "members": [to_car(car_from_lidar, np.asarray(c["member_boxes"])[:, :7]) for c in cons], "gt": gt,
                "rule": lambda k: "", "fov_half": np.arctan(img.shape[1] / 2 / K[0, 0]), "rng": [c["range"] for c in cons]}


# ------------------------------------------------------------------ one frame
def style(d):
    if not d["scored"]:
        return NS, (0, (1, 1.5)), 0.6
    return (COR if d["correct"] else WRG), ("-" if d["accepted"] else (0, (3, 2))), 0.9


def render(ds, fid, tau_n, tau_f, cut, out_png, dpi):
    tab = ds.tab; fpos = tab["fids"].index(fid)
    rows = np.where((tab["cls"] == ds.car) & (tab["fpos"] == fpos))[0]
    f = ds.frame(fid)
    if len(f["boxes"]) != len(rows) or (len(rows) and not np.allclose(f["rng"], tab["rng"][rows], atol=1e-4)):
        sys.exit(f"ABORT {fid}: rebuilt boxes do not align with the table")
    det = []
    for i, k in enumerate(rows):
        b = f["boxes"][i]; u, v, z = f["project"](corners_3d(b))
        det.append({"box": b, "members": f["members"][i], "u_s": float(tab["u_s"][k]), "correct": int(tab["y_A_iou0.5"][k]),
                    "scored": f["rule"](k) == "", "dist": float(tab["rng"][k]), "zone": "far" if tab["rng"][k] > cut else "near",
                    "accepted": bool(tab["u_s"][k] <= tau_n), "uv": (u, v, z), "in_image": bool((z > 0.1).all()),
                    "max_iou_car": max((m1.rotated_iou_3d(np.asarray(b, np.float32), np.asarray(g, np.float32)) for g in f["gt"]), default=0.0)})
    sc = [d for d in det if d["scored"]]
    cc = [d for d in sc if d["accepted"] and d["correct"] and d["zone"] == "near" and d["in_image"]]
    cw = [d for d in sc if d["accepted"] and not d["correct"] and d["in_image"]]
    dc = min(cc, key=lambda d: d["u_s"]) if cc else None
    dw = min(cw, key=lambda d: (d["zone"] != "far", d["max_iou_car"] >= 0.1, d["u_s"])) if cw else None
    for n, d in ((1, dc), (2, dw)):
        if d:
            d["id"] = n
    img, (H0, H1) = f["img"], (ds.rows or (0, f["img"].shape[0]))
    Wd = img.shape[1]

    FH = 108
    fig = plt.figure(figsize=(122 * MM, FH * MM))
    axc = fig.add_axes([0, 1 - 37 / FH, 1, 37 / FH])
    grey = img @ np.array([0.299, 0.587, 0.114]); soft = 0.8 * (0.5 * img + 0.5 * grey[..., None]) + 0.2
    axc.imshow(np.clip(soft, 0, 1)); axc.set_xlim(0, Wd); axc.set_ylim(H1, H0); axc.axis("off")
    for d in sorted(det, key=lambda d: (d["scored"], d["accepted"])):
        if not d["in_image"]:
            continue
        u, v, _ = d["uv"]; x0, x1 = max(u.min(), 0), min(u.max(), Wd); y0, y1 = max(v.min(), H0), min(v.max(), H1)
        if x1 <= x0 or y1 <= y0:
            continue
        col, ls, lw = style(d)
        axc.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=col, ls=ls, lw=lw))
        if "id" in d:
            axc.text(x0, y0 - 4, str(d["id"]), color="white", fontsize=6, ha="left", va="bottom",
                     bbox={"boxstyle": "square,pad=0.15", "fc": col, "ec": "none"})
    n_ac = sum(d["accepted"] and d["correct"] for d in sc); n_aw = sum(d["accepted"] and not d["correct"] for d in sc)
    axc.text(4, H0 + 4, f"{ds.name} {fid[:8]}; {ds.where(fid)}; cars: {n_ac} accepted correct, {n_aw} accepted wrong, "
             f"{sum(not d['accepted'] for d in sc)} rejected" + (f", {len(det) - len(sc)} not scored" if len(det) > len(sc) else ""),
             fontsize=6, ha="left", va="top", bbox={"boxstyle": "square,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85})

    # lateral range: +-12 m, widened (up to +-20 m) to hold every detection seen by the camera within 70 m
    num = [d for d in det if d["in_image"] and d["box"][0] < 70]
    ylo = max(-20, min([-12] + [d["box"][1] - 3.5 for d in num])); yhi = min(20, max([12] + [d["box"][1] + 4.5 for d in num]))
    axb = fig.add_axes([0.075, 36 / FH, 0.665, 33 / FH])
    pts = f["pts"]; u, v, z = f["project"](pts)
    m = (z > 0.1) & (u >= 0) & (u < Wd) & (v >= H0) & (v < H1) & (pts[:, 2] > ds.zmin) & (pts[:, 0] < 70) & (pts[:, 1] > ylo) & (pts[:, 1] < yhi)
    axb.scatter(pts[m, 0], pts[m, 1], s=0.05, c=PTS, lw=0, rasterized=True, zorder=1)
    for sgn in (1, -1):
        axb.plot([0, 70], [0, sgn * 70 * np.tan(f["fov_half"])], color=NS, lw=0.4, ls=":", zorder=1)
    for g in f["gt"]:
        axb.add_patch(Polygon(corners_xy(g), closed=True, fc=GTF, ec=GTE, lw=0.5, zorder=2))
    for d in det:
        col, ls, lw = style(d)
        if "id" in d:
            for mb in d["members"]:
                axb.add_patch(Polygon(corners_xy(mb), closed=True, fill=False, ec=col, lw=0.3, zorder=3))
        axb.add_patch(Polygon(corners_xy(d["box"]), closed=True, fill=False, ec=col, ls=ls, lw=lw, zorder=4))
        if "id" in d:
            axb.text(d["box"][0], d["box"][1] + 2.2, str(d["id"]), color="white", fontsize=6, ha="center", va="bottom", zorder=5,
                     clip_on=True, bbox={"boxstyle": "square,pad=0.15", "fc": col, "ec": "none"})
    th = np.linspace(-f["fov_half"], f["fov_half"], 60)
    axb.plot(cut * np.cos(th), cut * np.sin(th), color="black", lw=0.6, ls=":", zorder=2)
    axb.text(cut - 0.8, 1.6, "near", ha="right", va="center", fontsize=6); axb.text(cut + 0.8, 1.6, "far", ha="left", va="center", fontsize=6)
    axb.add_patch(Polygon([[1.8, 0], [-0.6, 1.1], [-0.6, -1.1]], closed=True, fc="black", ec="none", zorder=5))
    axb.set_xlim(-1, 70); axb.set_ylim(ylo, yhi); axb.set_aspect("equal")
    axb.set_xticks(range(0, 71, 10)); axb.set_yticks([-10, 0, 10]); axb.tick_params(length=2, pad=1)
    axb.set_xlabel("forward (m)", labelpad=0.5); axb.set_ylabel("lateral (m)", labelpad=0.5)
    for s in ("top", "right"):
        axb.spines[s].set_visible(False)

    def inset(rect, d, label):
        ax = fig.add_axes(rect); cx, cy = d["box"][0], d["box"][1]; r = 3.2
        mm = (np.abs(pts[:, 0] - cx) < r) & (np.abs(pts[:, 1] - cy) < r * 0.8) & (pts[:, 2] > ds.zmin)
        ax.scatter(pts[mm, 0], pts[mm, 1], s=0.4, c=PTS, lw=0, zorder=1)
        for g in f["gt"]:
            ax.add_patch(Polygon(corners_xy(g), closed=True, fc=GTF, ec=GTE, lw=0.5, zorder=2))
        col, _, _ = style(d)
        for mb in d["members"]:
            ax.add_patch(Polygon(corners_xy(mb), closed=True, fill=False, ec=col, lw=0.3, zorder=3))
        ax.add_patch(Polygon(corners_xy(d["box"]), closed=True, fill=False, ec=col, lw=0.9, zorder=4))
        ax.set_xlim(cx - r, cx + r); ax.set_ylim(cy - r * 0.8, cy + r * 0.8); ax.set_aspect("equal")
        ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_linewidth(0.5); s.set_color(col)
        ax.set_title(f"{d['id']}: {label}", fontsize=6, pad=1.5, color=col)
    us = lambda d: rf"$u_{{\mathrm{{s}}}}={d['u_s']:.2f}$"
    if dc:
        inset([0.765, 53 / FH, 0.215, 15 / FH], dc, us(dc))
    if dw:
        inset([0.765, 34 / FH, 0.215, 15 / FH], dw, ("no annotated object; " if dw["max_iou_car"] < 0.1 else f"{dw['zone']}; ") + us(dw))

    axs = fig.add_axes([0.075, 10 / FH, 0.905, 15 / FH])
    for d in sc:
        col = COR if d["correct"] else WRG
        axs.plot([d["u_s"]], [1 if d["zone"] == "near" else 0], marker="o" if d["correct"] else "^", ms=3.6, mec=col,
                 mfc=col if d["accepted"] else "white", mew=0.8, ls="none", zorder=3)
    axs.axvline(tau_n, color="black", lw=0.8); axs.axvline(tau_f, color=COR, lw=0.8, ls=(0, (3, 2)))
    xmax = max([0.5] + [d["u_s"] * 1.05 for d in sc])
    axs.set_xlim(0, xmax); axs.set_ylim(-0.6, 2.3); axs.set_yticks([0, 1]); axs.set_yticklabels(["far", "near"])
    axs.set_xlabel(r"spatial uncertainty $u_{\mathrm{s}}$ of each detection", labelpad=1)
    lo, hi = sorted([(tau_n, "black", r"threshold selected at near distance ($\alpha=0.1^{\dagger}$)"),
                     (tau_f, COR, "threshold selected at far distance")])
    axs.text(lo[0] - 0.004 * xmax / 0.5, 1.85, lo[2].replace(" at ", "\nat ", 1), ha="right", va="center", fontsize=6, color=lo[1])
    axs.text(hi[0], 1.95, " " + hi[2], ha="left", va="center", fontsize=6, color=hi[1])
    for s in ("top", "right"):
        axs.spines[s].set_visible(False)
    axs.tick_params(length=2, pad=1)
    h = [Line2D([], [], color=COR, lw=0.9), Line2D([], [], color=WRG, lw=0.9), Line2D([], [], color="black", lw=0.9, ls=(0, (3, 2))),
         Rectangle((0, 0), 1, 1, fc=GTF, ec=GTE, lw=0.5)] + ([Line2D([], [], color=NS, lw=0.6, ls=(0, (1, 1.5)))] if ds.name == "KITTI" else [])
    lab = ["correct", "wrong", "rejected (dashed)", "annotated car"] + (["not scored (KITTI rule)"] if ds.name == "KITTI" else [])
    fig.legend(h, lab, loc="lower center", ncol=len(h), frameon=False, bbox_to_anchor=(0.5, -0.005), handlelength=1.6, columnspacing=1.4)
    fig.savefig(out_png, dpi=dpi, facecolor="white"); plt.close(fig)
    return {"accepted_correct": n_ac, "accepted_wrong": n_aw, "rejected": sum(not d["accepted"] for d in sc), "not_scored": len(det) - len(sc)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", choices=["kitti", "nuscenes"], required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--frames", nargs="+"); g.add_argument("--frame-list"); g.add_argument("--drive"); g.add_argument("--scene")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int); ap.add_argument("--out"); ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--mp4", action="store_true"); ap.add_argument("--fps", type=float, default=2.0)
    a = ap.parse_args()
    t0 = time.time()
    C = pickle.load(open(REL / "cache/tables.pkl", "rb"))
    ds = (Kitti if a.dataset == "kitti" else Nusc)(C)
    tj = json.load(open(REL / f"data/tau_{a.dataset}_distance_split0.json"))
    tau_n, tau_f, cut = float(tj["tau"]["near"]), float(tj["tau"]["far"]), float(tj["cut_m"])
    if a.frames or a.frame_list:
        fr = a.frames or [l.strip() for l in open(a.frame_list) if l.strip()]
        bad = [x for x in fr if x not in ds.tab["fids"]]
        if bad:
            sys.exit(f"not validation frames of {ds.name}: {bad[:5]}")
    else:
        fr = ds.select(a)
        if not fr:
            sys.exit("no frames match the selection")
    fr = fr[: a.limit] if a.limit else fr
    tag = a.drive or a.scene or ("all" if a.all else "list")
    out = Path(a.out) if a.out else REL / f"frames/{a.dataset}_{tag}"
    out.mkdir(parents=True, exist_ok=True)
    print(f"{VERSION}: {ds.name}, {len(fr)} frames -> {out}; tau near {tau_n:.5f}, far {tau_f:.5f}, boundary {cut:.3f} m "
          f"(loaded in {time.time() - t0:.0f} s)", flush=True)
    with open(out / "index.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["n", "frame", "where", "png", "accepted_correct", "accepted_wrong", "rejected", "not_scored"])
        for n, fid in enumerate(fr):
            png = out / f"{n:05d}_{fid}.png"
            c = render(ds, fid, tau_n, tau_f, cut, png, a.dpi)
            w.writerow([n, fid, ds.where(fid), png.name, c["accepted_correct"], c["accepted_wrong"], c["rejected"], c["not_scored"]])
    print(f"rendered {len(fr)} frames in {time.time() - t0:.0f} s", flush=True)
    if a.mp4:
        mp4 = out / f"{out.name}.mp4"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-pattern_type", "glob", "-i", str(out / "*.png"),
                            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "mpeg4", "-q:v", "3", "-pix_fmt", "yuv420p", str(mp4)])
        if r.returncode:
            sys.exit("ffmpeg failed")
        print(f"wrote {mp4}")


if __name__ == "__main__":
    main()

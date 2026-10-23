#!/usr/bin/env python3
"""
frame_figure.py - one KITTI frame and one nuScenes rain frame with every scored car detection, its
acceptance under the transferred threshold and its correctness: camera image with projected boxes,
bird's-eye view of the LiDAR sweep, and the indicator value of each detection.

(a) KITTI frame 004289, KITTI rule, near/far boundary 34.806 m, u_s threshold tau_near 0.16931
    (m6 KITTI-rule run, split 0, alpha 0.1; work/data/tau_kitti_distance_split0.json).
(b) nuScenes rain frame chosen by a fixed rule: the clear-weather u_e threshold (m6 rain run,
    split 0, alpha 0.1) accepts >= 1 wrong and >= 3 correct car detections; of those frames, the one
    closest to the median count of accepted wrong detections. Candidates: rain frames of the
    evaluation part of split 0. Ties: most accepted wrong detections inside the CAM_FRONT field of
    view, then most accepted correct ones there, then token order.
Detection data: per-detection table of work/cache/tables.pkl (verified against frame_errors_cache.pkl),
boxes from the same consensus rebuild (m2 / m3 code), aligned by range. KITTI detections removed by the
KITTI rule are drawn dotted grey (neither correct nor wrong). Before drawing, the counts per frame are
compared with the recorded values in EXPECTED; the figure is not written if they differ.

Usage: python3 tools/figures/frame_figure.py   (writes work/figures/frame_figure.pdf and its log)
"""
import csv, importlib.util, json, pickle, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Polygon, Patch, Wedge
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); import layout

VERSION = "frame-figure-0.4 (2026-10-19)"
FIG_H = 4.3                    # maximum height (in)
W = layout.RESULTS; REL = layout.WORK; RUM = layout.RUM; META = layout.NUSC_META
NUS_ROOT = RUM / "data/nuscenes/v1.0-trainval"
OK, DNA, REJ, PTS, TAUC, EGO = "#2E7D32", "#C62828", "#9AA0A6", "#B8BCC2", "#1565C0", "#424242"
WIDTH = 4.8
plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "cm", "font.size": 7, "axes.labelsize": 7,
                     "axes.titlesize": 7, "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
                     "pdf.fonttype": 42})
EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
LAT, LON_K, LON_N = 30.0, (-5.0, 55.0), (-30.0, 30.0)       # bird's-eye windows (m): same scale and size in both panels
NUS_ROWS = (300, 830)          # CAM_FRONT rows shown (sky and lower road cropped; fixed, not chosen per frame)

m6 = layout.load_analysis()
m1, m2, m3 = m6.m1, m6.m2, m6.m3


# ------------------------------------------------------------------ geometry
def corners_xy(b):
    x, y, _, l, w, _, yaw = [float(v) for v in b[:7]]
    c, s = np.cos(yaw), np.sin(yaw)
    dx = np.array([l, l, -l, -l]) / 2; dy = np.array([w, -w, -w, w]) / 2
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


def rebuild_boxes(entry_lists, scored, cons_fn, member_fn, car, rng_expected):
    mdets = [member_fn(e, scored["min_confidence"]) for e in entry_lists]
    cons = [c for c in cons_fn(mdets, scored["K"], scored["consensus_threshold"], scored["iou_threshold"]) if c["cls"] == car]
    if len(cons) != len(rng_expected) or (len(cons) and not np.allclose([c["range"] for c in cons], rng_expected, atol=1e-4)):
        sys.exit("ABORT: rebuilt boxes do not align with the table")
    return np.array([np.asarray(c["consensus_box"], float)[:7] for c in cons]).reshape(-1, 7)


# ------------------------------------------------------------------ KITTI
def kitti_bundle(C, log):
    ktab, why = C["ktab"], C["why"]
    tj = json.load(open(REL / "data/tau_kitti_distance_split0.json"))
    tau, cut = float(tj["tau"]["near"]), float(tj["cut_m"])
    fid = "004289"; fpos = ktab["fids"].index(fid)
    rows = np.where((ktab["cls"] == "Car") & (ktab["fpos"] == fpos))[0]
    scored = pickle.load(open(RUM / "detections/kitti_v2/scored_val.pkl", "rb"))
    seeds = [{str(e.get("frame_id", "")): e for e in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/kitti_v2").glob("seed*_val.pkl"))]
    boxes = rebuild_boxes([sd[fid] for sd in seeds], scored, m2.consensus_for_frame, m2.member_detections, "Car", ktab["rng"][rows])
    keep = why[rows] == ""
    acc = ktab["u_s"][rows] <= tau; cor = ktab["y_A_iou0.5"][rows] == 1
    calib = m6.read_calib(RUM / f"data/kitti/training/calib/{fid}.txt")
    pts = np.fromfile(str(RUM / f"data/kitti/training/velodyne/{fid}.bin"), np.float32).reshape(-1, 4)[:, :3]
    img = mpimg.imread(str(RUM / f"data/kitti/training/image_2/{fid}.png"))
    P2, R0, Tr = calib
    T = np.eye(4); T[:3, :4] = Tr; R0h = np.eye(4); R0h[:3, :3] = R0
    K34 = P2
    log += [f"KITTI frame {fid}: tau_near(u_s) {tau:.5f}, cut {cut:.3f} m; car detections {len(rows)}, "
            f"not scored (KITTI rule, drawn dotted grey) {int((~keep).sum())}; scored: accepted correct {int((acc & cor & keep).sum())}, "
            f"accepted wrong {int((acc & ~cor & keep).sum())}, rejected {int((~acc & keep).sum())}"]
    for zone, m in (("near", np.hypot(boxes[:, 0], boxes[:, 1]) <= cut), ("far", np.hypot(boxes[:, 0], boxes[:, 1]) > cut)):
        z = m & keep
        log.append(f"   {zone}: accepted correct {int((z & acc & cor).sum())}, accepted wrong {int((z & acc & ~cor).sum())}, rejected {int((z & ~acc).sum())}")
    vis = (np.abs(boxes[:, 1]) <= LAT) & (boxes[:, 0] >= LON_K[0]) & (boxes[:, 0] <= LON_K[1])
    log.append(f"   scored detections outside the bird's-eye window: {int((~vis & keep).sum())} (accepted {int((~vis & keep & acc).sum())})")
    log.append("   not scored (KITTI rule): " + "; ".join(f"forward {boxes[i, 0]:.1f} m, lateral {boxes[i, 1]:.1f} m, {why[rows][i]}, "
                                                          f"{'inside' if vis[i] else 'OUTSIDE'} the window" for i in np.where(~keep)[0]))
    rng_d = np.hypot(boxes[:, 0], boxes[:, 1])
    return {"img": img, "pts_car": pts, "boxes_car": boxes, "acc": acc, "cor": cor, "scored": keep,
            "u": ktab["u_s"][rows], "tau": tau, "zone": np.where(rng_d > cut, "far", "near"),
            "cam_from_car": R0h @ T, "K34": K34, "cut": cut, "fov_half": np.degrees(np.arctan(img.shape[1] / 2 / P2[0, 0])),
            "lon": LON_K}


# ------------------------------------------------------------------ nuScenes
def nusc_bundle(C, log):
    ntab = C["ntab"]
    wcls, wcounts = m6.nusc_weather_classes(META, ntab["fids"])
    rowsC = [r for r in csv.DictReader(open(W / "m6_five_splits/C_weather_nuscenes.csv"))
             if r["indicator"] == "u_e" and r["seed"] == "0" and r["alpha"] == "0.1" and r["established"] == "clear" and r["applied"] == "rain"]
    tau = float(rowsC[0]["tau"])
    det_class = wcls[ntab["fpos"]]
    rr, _ = m6.class_matrix(ntab, det_class, "u_e", 0, [0.1], m1.CFG)          # cross-check of the recorded tau
    tau_re = [r["tau"] for r in rr if r["established"] == "clear"][0]
    if abs(tau_re - tau) > 1e-12:
        sys.exit(f"ABORT: recomputed clear-weather tau {tau_re} differs from m6 {tau}")
    codes = m1.split_frames(ntab["n_frames"], 0, m1.CFG)
    car = ntab["cls"] == "car"; y = ntab["y_A_iou0.5"]; acc_all = ntab["u_e"] <= tau
    cand = []
    for fp in np.where((codes == 2) & (wcls == 1))[0]:
        m = car & (ntab["fpos"] == fp)
        nc, nw = int((m & acc_all & (y == 1)).sum()), int((m & acc_all & (y == 0)).sum())
        if nc >= 3 and nw >= 1:
            cand.append({"fpos": int(fp), "token": ntab["fids"][fp], "acc_correct": nc, "acc_wrong": nw})
    n_rain_eval = int(((codes == 2) & (wcls == 1)).sum())
    med = float(np.median([c["acc_wrong"] for c in cand]))
    # calibration of CAM_FRONT for the candidates (needed for the tie-break and the drawing)
    infos = {e["token"]: e for e in pickle.load(open(NUS_ROOT / "nuscenes_infos_10sweeps_val.pkl", "rb"))}
    need = {infos[c["token"]]["cam_front_path"]: c["token"] for c in cand}
    sd_cam = {}
    for sd in json.load(open(META / "sample_data.json")):
        if sd["filename"] in need:
            sd_cam[need[sd["filename"]]] = sd
    poses_needed = {sd["ego_pose_token"] for sd in sd_cam.values()}
    poses = {p["token"]: p for p in json.load(open(META / "ego_pose.json")) if p["token"] in poses_needed}
    calibs = {c["token"]: c for c in json.load(open(META / "calibrated_sensor.json"))}

    def cam_from_lidar(tok):
        e, sd = infos[tok], sd_cam[tok]
        p, cs = poses[sd["ego_pose_token"]], calibs[sd["calibrated_sensor_token"]]
        T_gl = np.linalg.inv(e["car_from_global"]) @ np.linalg.inv(e["ref_from_car"])
        T_glob_from_car_cam = T_from(quat_to_R(p["rotation"]), p["translation"])
        T_car_from_cam = T_from(quat_to_R(cs["rotation"]), cs["translation"])
        return np.linalg.inv(T_car_from_cam) @ np.linalg.inv(T_glob_from_car_cam) @ T_gl, np.asarray(cs["camera_intrinsic"])

    nseeds = None
    scored = pickle.load(open(RUM / "detections/nuscenes/scored_val.pkl", "rb"))

    def frame_boxes(tok, fp):
        nonlocal nseeds
        if nseeds is None:
            nseeds = [{m3._entry_token(e): e for e in pickle.load(open(f, "rb"))} for f in sorted((RUM / "detections/nuscenes").glob("seed*_val.pkl"))]
        rows = np.where(car & (ntab["fpos"] == fp))[0]
        return rows, rebuild_boxes([sd[tok] for sd in nseeds], scored, m3.consensus_for_frame, m3.member_detections, "car", ntab["rng"][rows])

    def in_fov(boxes_l, T, K):
        if not len(boxes_l):
            return np.zeros(0, bool)
        c = (T @ np.c_[boxes_l[:, :3], np.ones(len(boxes_l))].T).T
        uv = (K @ c[:, :3].T).T; z = c[:, 2]
        with np.errstate(divide="ignore", invalid="ignore"):
            u, v = uv[:, 0] / z, uv[:, 1] / z
        return (z > 0.5) & (u >= 0) & (u < 1600) & (v >= 0) & (v < 900)

    for c in cand:
        c["dist"] = abs(c["acc_wrong"] - med)
    best = min(c["dist"] for c in cand)
    tied = [c for c in cand if c["dist"] == best]
    for c in tied:
        rows, bx = frame_boxes(c["token"], c["fpos"])
        T, K = cam_from_lidar(c["token"])
        v = in_fov(bx, T, K); a = acc_all[rows]; yy = y[rows] == 1
        c["fov_acc_wrong"], c["fov_acc_correct"] = int((v & a & ~yy).sum()), int((v & a & yy).sum())
    tied.sort(key=lambda c: (-c["fov_acc_wrong"], -c["fov_acc_correct"], c["token"]))
    pick = tied[0]
    tok, fp = pick["token"], pick["fpos"]
    rows, boxes_l = frame_boxes(tok, fp)
    T_cam_lidar, K = cam_from_lidar(tok)
    e = infos[tok]
    car_from_lidar = np.linalg.inv(e["ref_from_car"])
    pts_l = np.fromfile(str(NUS_ROOT / e["lidar_path"]), np.float32).reshape(-1, 5)[:, :3]
    pts_car = (car_from_lidar @ np.c_[pts_l, np.ones(len(pts_l))].T).T[:, :3]
    Rcl = car_from_lidar[:3, :3]
    boxes_car = boxes_l.copy()
    boxes_car[:, :3] = (car_from_lidar @ np.c_[boxes_l[:, :3], np.ones(len(boxes_l))].T).T[:, :3]
    boxes_car[:, 6] = boxes_l[:, 6] + np.arctan2(Rcl[1, 0], Rcl[0, 0])
    img = mpimg.imread(str(NUS_ROOT / e["cam_front_path"]))
    acc = acc_all[rows]; cor = y[rows] == 1
    scene = {s["token"]: s for s in json.load(open(META / "scene.json"))}
    sample = next(s for s in json.load(open(META / "sample.json")) if s["token"] == tok)
    sc = scene[sample["scene_token"]]
    vis = (np.abs(boxes_car[:, 1]) <= LAT) & (boxes_car[:, 0] >= LON_N[0]) & (boxes_car[:, 0] <= LON_N[1])
    log += [f"nuScenes: weather counts {wcounts}; clear-weather tau(u_e) {tau:.5f} (m6 C_weather_nuscenes.csv, seed 0, alpha 0.1; recomputed equal)",
            f"   rain frames in the evaluation part of split 0: {n_rain_eval}; qualifying (accepted correct >= 3 and accepted wrong >= 1): {len(cand)}",
            f"   median accepted wrong over qualifying frames: {med:g}; frames at the minimum distance {best:g}: {len(tied)}",
            f"   tie-break (most accepted wrong in CAM_FRONT view, then most accepted correct there, then token): top 5 "
            + str([(c['token'][:8], c['acc_wrong'], c['acc_correct'], c['fov_acc_wrong'], c['fov_acc_correct']) for c in tied[:5]]),
            f"   CHOSEN sample token {tok}, scene {sc['name']} ('{sc['description']}'), lidar {e['lidar_path']}, camera {e['cam_front_path']}",
            f"   car detections {len(rows)}: accepted correct {int((acc & cor).sum())}, accepted wrong {int((acc & ~cor).sum())}, rejected {int((~acc).sum())}; "
            f"in CAM_FRONT view: accepted wrong {pick['fov_acc_wrong']}, accepted correct {pick['fov_acc_correct']}; "
            f"outside the bird's-eye window: {int((~vis).sum())} (accepted {int((~vis & acc).sum())})"]
    return {"img": img, "pts_car": pts_car, "boxes_car": boxes_car, "boxes_lidar": boxes_l, "acc": acc, "cor": cor,
            "scored": np.ones(len(rows), bool), "u": ntab["u_e"][rows], "tau": tau, "zone": np.full(len(rows), "rain"),
            "T_cam_lidar": T_cam_lidar, "K": K, "cut": None, "fov_half": np.degrees(np.arctan(img.shape[1] / 2 / K[0, 0])),
            "lon": LON_N, "token": tok}


# ------------------------------------------------------------------ drawing
EXPECTED = {"kitti": {"accepted correct": 6, "accepted wrong": 2, "rejected": 1, "not scored": 4, "tau": 0.16931},
            "nusc": {"accepted correct": 6, "accepted wrong": 1, "rejected": 2, "not scored": 0, "tau": 0.46385}}  # recorded counts of the published figure
NOT_SCORED_LS = (0, (1.2, 1.2))


def counts(b):
    s, a, c = b["scored"], b["acc"], b["cor"]
    return {"accepted correct": int((s & a & c).sum()), "accepted wrong": int((s & a & ~c).sum()),
            "rejected": int((s & ~a).sum()), "not scored": int((~s).sum()), "tau": round(float(b["tau"]), 5)}


def box_style(b, i):
    """(edge colour, line style, line width, fill colour or None, z-order)"""
    if not b["scored"][i]:
        return REJ, NOT_SCORED_LS, 0.7, None, 2
    if not b["acc"][i]:
        return REJ, "-", 0.7, None, 3
    col = OK if b["cor"][i] else DNA
    return col, "-", 0.9, col, 4


def draw_camera(ax, b, kind):
    img = b["img"]; H, Wd = img.shape[:2]
    ax.imshow(img)
    for i in sorted(range(len(b["acc"])), key=lambda i: box_style(b, i)[4]):
        if kind == "kitti":
            P = corners_3d(b["boxes_car"][i]); cam = (b["cam_from_car"] @ np.c_[P, np.ones(8)].T).T
            uvw = (b["K34"] @ cam.T).T
        else:
            P = corners_3d(b["boxes_lidar"][i]); cam = (b["T_cam_lidar"] @ np.c_[P, np.ones(8)].T).T
            uvw = (b["K"] @ cam[:, :3].T).T
        if (cam[:, 2] < 0.5).any():
            continue
        uv = uvw[:, :2] / uvw[:, 2:3]
        col, ls, lw, _, z = box_style(b, i)
        for p, q in EDGES:
            ax.plot(uv[[p, q], 0], uv[[p, q], 1], color=col, ls=ls, lw=lw * 0.8, solid_capstyle="round", zorder=z)
    ax.set_xlim(0, Wd); ax.set_ylim(*((NUS_ROWS[1], NUS_ROWS[0]) if kind == "nusc" else (H, 0))); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


def draw_bev(ax, b, ylabel):
    disp = lambda xy: np.column_stack([-xy[:, 1], xy[:, 0]])      # forward up, vehicle left to the left
    lo, hi = b["lon"]
    p = b["pts_car"]; m = (np.abs(p[:, 1]) < LAT) & (p[:, 0] > lo) & (p[:, 0] < hi)      # full sweep, ground kept
    d = disp(p[m][:, :2])
    fh = b["fov_half"]
    ax.add_patch(Wedge((0, 0), 200, 90 - fh, 90 + fh, facecolor="#EEF1F5", edgecolor="none", zorder=0))
    ax.scatter(d[:, 0], d[:, 1], s=0.3, c=PTS, alpha=0.6, linewidths=0, rasterized=True, zorder=1)
    if b["cut"]:
        th = np.linspace(0, 2 * np.pi, 400)
        ax.plot(b["cut"] * np.cos(th), b["cut"] * np.sin(th), color="#455A64", ls=":", lw=0.9, zorder=2)
    ego = disp(np.array([[2.25, 0.9], [2.25, -0.9], [-2.25, -0.9], [-2.25, 0.9]]))       # 4.5 m x 1.8 m, heading forward
    ax.add_patch(Polygon(ego, closed=True, fill=False, edgecolor=EGO, lw=0.9, zorder=5))
    for i in range(len(b["acc"])):
        c = disp(corners_xy(b["boxes_car"][i])); col, ls, lw, fill, z = box_style(b, i)
        if fill:
            ax.add_patch(Polygon(c, closed=True, facecolor=fill, alpha=0.35, lw=0, zorder=z))
        ax.add_patch(Polygon(c, closed=True, fill=False, edgecolor=col, ls=ls, lw=lw, zorder=z + 0.1))
    ax.set_xlim(-LAT, LAT); ax.set_ylim(lo, hi); ax.set_aspect("equal")
    ax.set_xticks([-20, 0, 20]); ax.set_xticklabels(["$20$", "$0$", "$-20$"])        # display left = vehicle left = positive
    ax.set_yticks([v for v in (-20, 0, 20, 40) if lo <= v <= hi])
    ax.tick_params(length=2, pad=1.5)
    ax.set_xlabel("lateral (m), left positive", labelpad=1)
    if ylabel:
        ax.set_ylabel("forward (m)", labelpad=1)


def draw_strip(ax, b, rows, xlabel):
    """Every drawn scored detection as a dot on the uncertainty axis; tau as a vertical line."""
    s = b["scored"]; u, cor, zone = b["u"][s], b["cor"][s], b["zone"][s]
    tau = float(b["tau"]); xmax = max(float(u.max()) * 1.08, tau * 1.35)
    jit = np.random.default_rng(0).uniform(-0.14, 0.14, len(u))
    ypos = {name: k for k, name in enumerate(reversed(rows))}
    n_dots = 0
    for i in range(len(u)):
        ax.plot(u[i], ypos[zone[i]] + jit[i], marker="o", ms=3.0, color=OK if cor[i] else DNA,
                markeredgecolor="white", markeredgewidth=0.3, ls="none", zorder=3)
        n_dots += 1
    top = len(rows) - 0.5 + 0.75                     # free band above the dot rows for the two labels
    ax.set_ylim(-0.5, top); ax.set_xlim(0, xmax)
    ax.axvline(tau, color=TAUC, lw=1.0, zorder=2)
    ax.text(tau, top, rf"$\tau = {tau:.3f}$", color=TAUC, ha="center", va="bottom", clip_on=False)
    ax.text(tau - xmax * 0.02, top - 0.06, "accepted", ha="right", va="top", color="#37474F")
    ax.text(tau + xmax * 0.02, top - 0.06, "rejected", ha="left", va="top", color="#37474F")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(list(reversed(rows)))
    ax.tick_params(axis="y", length=0, pad=2); ax.tick_params(axis="x", length=2, pad=1.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_xlabel(xlabel, labelpad=1)
    return n_dots


def main():
    C = pickle.load(open(REL / "cache/tables.pkl", "rb"))
    log = [VERSION]
    bk = kitti_bundle(C, log)
    bn = nusc_bundle(C, log)
    # check before drawing: counts and thresholds equal the recorded ones (EXPECTED)
    for name, b in (("kitti", bk), ("nusc", bn)):
        got = counts(b)
        log.append(f"CHECK {name}: {got}  expected {EXPECTED[name]}  -> {'equal' if got == EXPECTED[name] else 'DIFFERENT'}")
        if got != EXPECTED[name]:
            print("\n".join(log)); sys.exit(f"ABORT: {name} counts or tau differ from the recorded values; figure not saved")
    cam_hk = 1.0 * bk["img"].shape[0] / bk["img"].shape[1]; cam_hn = 1.0 * (NUS_ROWS[1] - NUS_ROWS[0]) / bn["img"].shape[1]
    cam_h = max(cam_hk, cam_hn); bev_h = (LON_K[1] - LON_K[0]) / (2 * LAT); strip_h = 0.2; leg_h = 0.1
    fig = plt.figure(figsize=(WIDTH, FIG_H), layout="constrained")
    gs = fig.add_gridspec(4, 2, height_ratios=[cam_h, bev_h, strip_h, leg_h])
    fig.get_layout_engine().set(h_pad=0.02, hspace=0.0, wspace=0.05)
    ax = {k: fig.add_subplot(gs[r, c]) for k, (r, c) in
          {"ck": (0, 0), "cn": (0, 1), "bk": (1, 0), "bn": (1, 1), "sk": (2, 0), "sn": (2, 1)}.items()}
    draw_camera(ax["ck"], bk, "kitti"); draw_camera(ax["cn"], bn, "nusc")
    ax["ck"].set_anchor("S")
    draw_bev(ax["bk"], bk, True); draw_bev(ax["bn"], bn, False)
    nk = draw_strip(ax["sk"], bk, ["near", "far"], r"$u_{\mathrm{s}}$ of each detection")
    nn = draw_strip(ax["sn"], bn, ["rain"], r"$u_{\mathrm{e}}$ of each detection")
    log.append(f"CHECK dots: (a) {nk} = scored {int(bk['scored'].sum())}; (b) {nn} = scored {int(bn['scored'].sum())}")
    if nk != int(bk["scored"].sum()) or nn != int(bn["scored"].sum()):
        print("\n".join(log)); sys.exit("ABORT: dot count differs from the scored detections; figure not saved")
    ax["ck"].set_title("(a) KITTI: threshold selected at near\ndistance, applied to the whole scene", loc="left")
    ax["cn"].set_title("(b) nuScenes: threshold selected in\nclear weather, applied in rain", loc="left")
    handles = [Patch(facecolor=to_rgba(OK, 0.35), edgecolor=OK, lw=0.9), Patch(facecolor=to_rgba(DNA, 0.35), edgecolor=DNA, lw=0.9),
               Patch(facecolor="none", edgecolor=REJ, lw=0.7), Patch(facecolor="none", edgecolor=REJ, lw=0.7, ls=NOT_SCORED_LS),
               Line2D([], [], color="#455A64", ls=":", lw=0.9)]
    lg = fig.add_subplot(gs[3, :]); lg.axis("off")
    lg.legend(handles, ["accepted correct", "accepted wrong", "rejected", "not scored (KITTI rule)", r"near $|$ far boundary"],
              loc="center", ncol=3, frameon=False, handlelength=1.4, columnspacing=1.2, borderaxespad=0)
    (REL / "figures").mkdir(parents=True, exist_ok=True); fig.savefig(REL / "figures/frame_figure.pdf", dpi=400)
    log.append(f"wrote work/figures/frame_figure.pdf ({WIDTH} x {fig.get_figheight():.2f} in)")
    (REL / "figures/frame_figure.log").write_text("\n".join(log)); print("\n".join(log))


if __name__ == "__main__":
    main()



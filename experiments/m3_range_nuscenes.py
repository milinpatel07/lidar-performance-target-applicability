#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m3_range_nuscenes.py

The applicability matrix of milestone 1 was computed on the saved RUM score u
(a blend of box spread and confidence spread). That blend is defined in neither
the VEHITS paper (ref 7) nor this paper. This script replaces it with the
indicators this paper uses, taken from ref 7:

  u_s  disagreement about where the object is
       = 1 - mean pairwise 3D IoU between contributing members   (VEHITS Eq. 3)
       Rotated IoU is used (a stated refinement of the VEHITS axis-aligned IoU).
       A larger value means a less trustworthy detection.

  u_e  derived from the members' agreement that an object is present
       = 1 - mean confidence over the K members, with non-contributing members
         contributing confidence 0 (VEHITS Eq. 1 is mean confidence; it is
         oriented here so a larger value means less trustworthy, as the paper
         requires for a rejection threshold u(d) <= tau).

  u_v  confidence variance across members (VEHITS Eq. 2), reported for
       completeness; not a headline indicator of this paper.

The consensus and matching rules of the RUM pipeline are reproduced exactly,
so the per-frame FN and FP are first checked against frame_errors_cache.pkl
and the consensus set is checked against scored_val.pkl. Only the per-detection
indicator changes from milestone 1.

This script imports the tested statistics, matching and reporting from
m1_range_kitti.py. Put both files in the same folder.

Usage (inside the container):
  python3 m3_range_nuscenes.py --selftest
  python3 m3_range_nuscenes.py --rum /rum --out /work/m2_indicators_kitti/results

Inputs (read-only): detections/nuscenes/seed1_val.pkl ... seed4_val.pkl,
detections/nuscenes/scored_val.pkl, detections/nuscenes/frame_errors_cache.pkl,
data/nuscenes/v1.0-trainval/nuscenes_infos_10sweeps_val.pkl
Outputs: only below --out.
"""
import argparse
import csv
import importlib.util
import json
import pickle
import platform
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("m1", str(HERE / "m1_range_kitti.py"))
m1 = importlib.util.module_from_spec(spec)
sys.modules["m1"] = m1
spec.loader.exec_module(m1)

SCRIPT_VERSION = "m3-0.4"   # 0.3: option --split scene (parts drawn by recorded scene); --split frame = m3-0.2
                            # 0.4: scene-unit loss = mean of per-frame a_f within the scene (decision 2026-10-19)
ORIG_SPLIT = m1.split_frames
ORIG_CELL = m1.Cell

# nuScenes uses lowercase class names and 10 eval classes. Override the object sets and
# the IoU settings (per-class thresholds) that m1.CFG defined for KITTI. The primary
# object is the car, the most populous class and the one comparable to the KITTI run.
m1.CFG["object_sets"] = {"car": ["car"], "vehicles": ["car", "truck", "bus", "trailer"]}
m1.CFG["iou_settings"] = {
    "A_iou0.5": {c: 0.5 for c in ["car", "truck", "construction_vehicle", "bus", "trailer",
                                   "barrier", "motorcycle", "bicycle", "pedestrian", "traffic_cone"]},
}
m1.CFG["primary"] = {"iou": "A_iou0.5", "cut_q": 0.5, "objects": "car", "seed": 0}
m1.CFG["verify_setting"] = "A_iou0.5"

# the consensus parameters are read from scored_val.pkl at run time; these are the
# values the RUM pipeline used and are asserted against the file.
EXPECTED = {"K": 4, "consensus_threshold": 3, "iou_threshold": 0.5, "min_confidence": 0.1}
NUSC_CLASSES = ["car", "truck", "construction_vehicle", "bus", "trailer",
                "barrier", "motorcycle", "bicycle", "pedestrian", "traffic_cone"]


def _entry_token(entry):
    """nuScenes per-member entries are keyed by the sample token in
    entry['metadata']['token']; entry['frame_id'] is a sweep filename, not the key
    used by scored_val.pkl or the GT info. Fall back to frame_id (KITTI style)."""
    md = entry.get("metadata")
    if isinstance(md, dict) and md.get("token"):
        return str(md["token"])
    return str(entry.get("frame_id", ""))


# ----------------------------------------------------------------------------
# Rebuild consensus from the per-member files, exactly as 02_build_consensus.py,
# but keep every per-member box and confidence so the indicators can be computed.
# ----------------------------------------------------------------------------
def member_detections(entry, min_conf):
    boxes = entry.get("boxes_lidar", np.zeros((0, 7)))
    scores = entry.get("score", np.zeros(0))
    names = entry.get("name", None)
    if names is None:
        labels = entry.get("pred_labels", np.zeros(0, dtype=int))
        names = np.array([NUSC_CLASSES[int(l) - 1] if 1 <= int(l) <= len(NUSC_CLASSES) else "unknown"
                          for l in labels])
    out = []
    for k in range(len(scores)):
        if scores[k] < min_conf:
            continue
        out.append({"cls": str(names[k]), "box": np.asarray(boxes[k], dtype=np.float64),
                    "confidence": float(scores[k])})
    return out


def consensus_for_frame(member_lists, K, thr, iou_match):
    """Reproduces build_consensus_for_frame of 02_build_consensus.py and additionally
    returns, for each consensus detection, the list of contributing member boxes and
    confidences. Matching uses rotated IoU, as in the RUM pipeline."""
    per_member = [list(ml) for ml in member_lists]
    if not per_member[0]:
        anchor = next((k for k in range(K) if per_member[k]), None)
        if anchor is None:
            return []
        per_member = per_member[anchor:] + per_member[:anchor]
    out, used = [], [set() for _ in range(K)]
    for i0, d0 in enumerate(per_member[0]):
        if i0 in used[0]:
            continue
        matches = [(0, i0)]
        for m in range(1, K):
            best_iou, best_idx = 0.0, -1
            for im, dm in enumerate(per_member[m]):
                if im in used[m] or d0["cls"] != dm["cls"]:
                    continue
                iou = m1.rotated_iou_3d(d0["box"], dm["box"])
                if iou > best_iou:
                    best_iou, best_idx = iou, im
            if best_iou >= iou_match:
                matches.append((m, best_idx))
        if len(matches) < thr:
            continue
        for mi, di in matches:
            used[mi].add(di)
        mboxes = np.stack([per_member[mi][di]["box"] for mi, di in matches])
        mconfs = np.array([per_member[mi][di]["confidence"] for mi, di in matches])
        cbox = mboxes.mean(axis=0)
        out.append({"cls": d0["cls"], "consensus_box": cbox.astype(np.float32),
                    "mean_confidence": float(mconfs.mean()),
                    "num_members_detected": len(matches),
                    "range": float(np.sqrt(cbox[0] ** 2 + cbox[1] ** 2)),
                    "member_boxes": mboxes, "member_confs": mconfs,
                    # RUM blend, recomputed, only to check the rebuild against scored_val.pkl
                    "u_rum": float(0.6 * mboxes.std(axis=0).mean() + 0.4 * mconfs.std())})
    return out


def indicators(det, K):
    """u_s, u_e, u_v for one consensus detection. Larger = less trustworthy for u_s and u_e."""
    boxes, confs = det["member_boxes"], det["member_confs"]
    n = len(boxes)
    # u_s : 1 - mean pairwise rotated IoU (VEHITS Eq. 3)
    if n < 2:
        u_s = 0.0
    else:
        ious = [m1.rotated_iou_3d(boxes[i], boxes[j]) for i in range(n) for j in range(i + 1, n)]
        u_s = 1.0 - float(np.mean(ious))
    # u_e : 1 - mean confidence over all K members (missing members contribute 0) (VEHITS Eq. 1)
    mean_conf_K = float(confs.sum()) / K
    u_e = 1.0 - mean_conf_K
    # u_v : confidence variance across contributing members (VEHITS Eq. 2)
    u_v = float(np.var(confs, ddof=1)) if n >= 2 else 0.0
    return u_s, u_e, u_v, mean_conf_K


def load_gt_nuscenes(info_path, eval_classes):
    """nuScenes GT from the OpenPCDet info pickle: a list of dicts with 'token' and
    'gt_boxes' (Nx7 or wider; first 7 columns are x,y,z,l,w,h,yaw in the LiDAR frame)
    and 'gt_names'. Only classes in eval_classes are kept. Returns {token: {gt_boxes, gt_names}}."""
    with open(info_path, "rb") as f:
        info = pickle.load(f)
    ev = set(eval_classes)
    gt = {}
    for e in info:
        tok = e.get("token") or e.get("frame_id") or e.get("sample_token")
        if tok is None:
            continue
        names = list(e.get("gt_names", []))
        boxes = e.get("gt_boxes", np.zeros((0, 7)))
        if not isinstance(boxes, np.ndarray):
            boxes = np.asarray(boxes)
        if boxes.ndim == 2 and boxes.shape[1] > 7:
            boxes = boxes[:, :7]
        n = min(len(names), len(boxes))
        names, boxes = names[:n], boxes[:n]
        keep = [nm in ev for nm in names]
        boxes = boxes[keep] if n > 0 else np.zeros((0, 7))
        names = [nm for nm, k in zip(names, keep) if k]
        gt[str(tok)] = {"gt_boxes": np.asarray(boxes, dtype=np.float32), "gt_names": names}
    return gt


def build(scored_params, seed_data, gt, settings):
    K = scored_params["K"]
    thr = scored_params["consensus_threshold"]
    iou_match = scored_params["iou_threshold"]
    min_conf = scored_params["min_confidence"]
    common = sorted(set.intersection(*[set(sd.keys()) for sd in seed_data]))
    fids = [f for f in common if f in gt]
    cols = {k: [] for k in ("fpos", "cls", "rng", "nmem", "u_s", "u_e", "u_v", "u_rum")}
    ys = {s: [] for s in settings}
    fnfp = {s: {} for s in settings}
    recon_vs_scored = {"matched": 0, "box_mismatch": 0, "count_mismatch": 0}
    for fpos, fid in enumerate(fids):
        mdets = [member_detections(sd[fid], min_conf) for sd in seed_data]
        cons = consensus_for_frame(mdets, K, thr, iou_match)
        g = gt[fid]
        boxes = [c["consensus_box"] for c in cons]
        M = m1.iou_matrix([{"cls": c["cls"], "consensus_box": c["consensus_box"]} for c in cons],
                          g["gt_boxes"], g["gt_names"]) if cons else np.zeros((0, len(g["gt_names"])))
        for s, thr_by_cls in settings.items():
            y, fn = m1.greedy_match([{"cls": c["cls"]} for c in cons], M, g["gt_names"], thr_by_cls)
            ys[s].append(y)
            fnfp[s][fid] = (int(fn), int((y == 0).sum()))
        for c in cons:
            u_s, u_e, u_v, _ = indicators(c, K)
            cols["fpos"].append(fpos); cols["cls"].append(c["cls"]); cols["rng"].append(c["range"])
            cols["nmem"].append(c["num_members_detected"])
            cols["u_s"].append(u_s); cols["u_e"].append(u_e); cols["u_v"].append(u_v)
            cols["u_rum"].append(c["u_rum"])
    tab = {"fids": fids, "n_frames": len(fids),
           "fpos": np.asarray(cols["fpos"], np.int64), "cls": np.asarray(cols["cls"]),
           "rng": np.asarray(cols["rng"], np.float64), "nmem": np.asarray(cols["nmem"], np.int64),
           "u_s": np.asarray(cols["u_s"], np.float64), "u_e": np.asarray(cols["u_e"], np.float64),
           "u_v": np.asarray(cols["u_v"], np.float64), "u_rum": np.asarray(cols["u_rum"], np.float64)}
    for s in settings:
        tab["y_" + s] = np.concatenate(ys[s]) if ys[s] else np.zeros(0, np.uint8)
    return tab, fnfp


def scene_index(meta_dir, fids):
    """Index of each frame's recorded scene (scene_token in sample.json); scenes in sorted token order."""
    scene_of = {s["token"]: s["scene_token"] for s in json.load(open(Path(meta_dir) / "sample.json"))}
    scenes = sorted({scene_of[f] for f in fids})
    pos = {t: i for i, t in enumerate(scenes)}
    return np.array([pos[scene_of[f]] for f in fids], dtype=np.int64), scenes


def scene_cell(sidx):
    """m1.Cell with the scene as the unit (author decision 2026-10-19). The loss of a scene is the mean of the
    per-frame false acceptance proportions a_f (Eq. 1) over the scene's frames in the cell (frames with an
    in-class detection); a scene without accepted detections has loss 0. Retention and the bootstrap resample
    scenes; retention itself is unchanged (a sum over detections)."""
    class SceneCell(m1.Cell):
        def __init__(self, fpos, u, y):
            frames, self.lfr = np.unique(fpos, return_inverse=True)
            self.mf = len(frames)
            self.frames, self.fs = np.unique(sidx[frames], return_inverse=True)   # frame -> scene in this cell
            self.m = len(self.frames)
            self.nf = np.bincount(self.fs, minlength=self.m).astype(float)
            self.lf = self.fs[self.lfr] if len(fpos) else self.lfr                # detection -> scene
            self.u, self.y = u, y
            self.correct_per_frame = np.bincount(self.lf[y == 1], minlength=self.m).astype(float)

        def a_f(self, tau):
            acc = self.u <= tau
            na = np.bincount(self.lfr[acc], minlength=self.mf)
            nw = np.bincount(self.lfr[acc & (self.y == 0)], minlength=self.mf)
            a = np.zeros(self.mf)
            nz = na > 0
            a[nz] = nw[nz] / na[nz]
            return np.bincount(self.fs, weights=a, minlength=self.m) / np.maximum(self.nf, 1)
    return SceneCell


def split_variants(tab, split, meta_dir):
    """(split, hb_unit, table, split function, Cell class) for each analysis variant.
    frame: the original frame split (m3-0.2).
    scene, hb_unit frame: scenes are permuted with the original split function and fractions; every frame
      takes its scene's part; frames stay the unit of the selection test and the HB interval.
    scene, hb_unit scene: the same partition; the scene replaces the frame as the unit of the selection test
      and the HB interval, with the loss of scene_cell."""
    if split == "frame":
        return [("frame", "frame", tab, ORIG_SPLIT, ORIG_CELL)], None
    sidx, scenes = scene_index(meta_dir, tab["fids"])

    def split_by_scene(n_frames, seed, cfg):
        assert n_frames == len(sidx)
        return ORIG_SPLIT(len(scenes), seed, cfg)[sidx]

    return [("scene", "frame", tab, split_by_scene, ORIG_CELL),
            ("scene", "scene", tab, split_by_scene, scene_cell(sidx))], (sidx, scenes)


def scene_counts(tab, sidx, n_scenes, objects, cut_q, seed, cfg):
    """Scenes per part (all, and with an in-class detection per range class) under the scene split."""
    sc = ORIG_SPLIT(n_scenes, seed, cfg)
    dcode = sc[sidx[tab["fpos"]]]
    sel = np.isin(tab["cls"], objects)
    cut = float(np.quantile(tab["rng"][sel & (dcode == 0)], cut_q))
    far = tab["rng"] > cut
    out = {"cut_m": cut}
    for pname, pc in (("grid", 0), ("select", 1), ("eval", 2)):
        out[pname] = {"scenes": int((sc == pc).sum()), "frames": int((sc[sidx] == pc).sum())}
        for cname, cm in (("near", ~far), ("far", far)):
            out[pname][cname] = int(len(np.unique(sidx[tab["fpos"][sel & cm & (dcode == pc)]])))
    return out


def check_rebuild(tab, scored):
    """Compare the rebuilt consensus against scored_val.pkl: for each frame the sorted
    recomputed RUM blend must equal the saved u (same count, values within 1e-4)."""
    saved = scored["frames"]
    n_ok = 0
    fids = tab["fids"]
    for fp, fid in enumerate(fids):
        rebuilt_u = np.sort(tab["u_rum"][tab["fpos"] == fp])
        s_u = np.sort(np.array([d["u"] for d in saved[fid]], dtype=float))
        if len(rebuilt_u) == len(s_u) and (len(s_u) == 0 or np.max(np.abs(rebuilt_u - s_u)) < 1e-4):
            n_ok += 1
    return n_ok, len(fids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rum", default="/rum")
    ap.add_argument("--out", default="results")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--allow-mismatch", action="store_true")
    ap.add_argument("--bev", choices=["auto", "shapely", "clip"], default="auto")
    ap.add_argument("--split", choices=["frame", "scene"], default="frame")
    ap.add_argument("--nusc-meta", default="/heinrich_nuscenes/v1.0-trainval",
                    help="folder with sample.json (only for --split scene)")
    args = ap.parse_args()
    m1.BEV_BACKEND = args.bev

    if args.selftest:
        sys.exit(0 if selftest() else 1)

    t0 = time.time()
    rum, out = Path(args.rum), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    f_scored = rum / "detections/nuscenes/scored_val.pkl"
    f_cache = rum / "detections/nuscenes/frame_errors_cache.pkl"
    f_info = rum / "data/nuscenes/v1.0-trainval/nuscenes_infos_10sweeps_val.pkl"
    seed_files = sorted((rum / "detections/nuscenes").glob("seed*_val.pkl"))
    for f in (f_scored, f_cache, f_info):
        if not f.exists():
            sys.exit(f"missing input: {f}")
    if len(seed_files) < 2:
        sys.exit("need the per-member seed*_val.pkl files")
    f_sample = Path(args.nusc_meta) / "sample.json"
    if args.split == "scene" and not f_sample.exists():
        sys.exit(f"missing input: {f_sample}")
    print(f"box overlap backend: {m1._resolve_backend()}")

    scored = pickle.load(open(f_scored, "rb"))
    for k, v in EXPECTED.items():
        if scored.get(k) != v:
            print(f"WARNING scored_val.pkl has {k}={scored.get(k)}, expected {v}")
    cache = pickle.load(open(f_cache, "rb"))
    gt = load_gt_nuscenes(f_info, cache["eval_classes"])
    seed_data = []
    for sf in seed_files:
        data = pickle.load(open(sf, "rb"))
        seed_data.append({_entry_token(e): e for e in data})
    print(f"members: {len(seed_data)}; frames with gt: {len(gt)}")

    tab, fnfp = build(scored, seed_data, gt, m1.CFG["iou_settings"])
    print(f"consensus detections rebuilt: {len(tab['u_s'])}  ({time.time() - t0:.0f} s)")

    n_ok, n_total = check_rebuild(tab, scored)
    rebuild_msg = f"REBUILD CHECK: consensus set matches scored_val.pkl for {n_ok}/{n_total} frames"
    print(rebuild_msg)
    bad, extra = m1.verify_against_cache(fnfp[m1.CFG["verify_setting"]], cache["errors"])
    verify_msg = ("VERIFICATION PASSED: per-frame FN and FP match frame_errors_cache.pkl for all "
                  f"{len(cache['errors'])} frames" if not (bad or extra)
                  else f"VERIFICATION FAILED: {len(bad)} frames differ (first {bad[:3]}), {len(extra)} extra")
    print(verify_msg)
    hard_fail = (bad or extra or n_ok < n_total) and not args.allow_mismatch
    if hard_fail:
        (out / "verification_failed.txt").write_text(rebuild_msg + "\n" + verify_msg)
        sys.exit(2)

    prov = {"script_version": SCRIPT_VERSION, "bev_backend": m1._resolve_backend(),
            "started": time.strftime("%Y-%m-%d %H:%M:%S"), "python": platform.python_version(),
            "numpy": np.__version__, "m1_version": m1.SCRIPT_VERSION,
            "inputs_sha256": {str(f): m1.sha256(f) for f in [f_scored, f_cache, f_info] + list(seed_files)},
            "script_sha256": m1.sha256(__file__), "config": m1.CFG,
            "indicator_definitions": {"u_s": "1 - mean pairwise rotated 3D IoU between members (VEHITS Eq. 3)",
                                      "u_e": "1 - mean confidence over K members, missing members 0 (VEHITS Eq. 1)",
                                      "u_v": "confidence variance across contributing members (VEHITS Eq. 2)"},
            "rebuild_check": rebuild_msg, "verification": verify_msg,
            "n_frames": tab["n_frames"], "n_detections": int(len(tab["u_s"])),
            "indicator_quantiles": {ind: {str(q): float(np.quantile(tab[ind], q)) for q in (0, .25, .5, .75, .95, 1)}
                                    for ind in ("u_s", "u_e", "u_v")}}
    variants, scn = split_variants(tab, args.split, args.nusc_meta)
    prov["split"] = args.split
    if scn:
        sidx, scenes = scn
        prov["nusc_meta_sha256"] = {str(f_sample): m1.sha256(f_sample)}
        prov["n_scenes"] = len(scenes)
        prov["scene_counts_primary"] = {
            f"seed{s}": scene_counts(tab, sidx, len(scenes), m1.CFG["object_sets"][m1.CFG["primary"]["objects"]],
                                     m1.CFG["primary"]["cut_q"], s, m1.CFG) for s in m1.CFG["seeds"]}
    (out / "provenance.json").write_text(json.dumps(prov, indent=2))

    alphas = m1.CFG["alphas_frozen"] + m1.CFG["alphas_exploratory"]
    rows, tally, summaries = [], {}, {}
    for split, unit, T, split_fn, cell_cls in variants:
        m1.split_frames = split_fn      # m1.analyse draws its parts through this function
        m1.Cell = cell_cls              # and builds its per-unit losses with this class
        for ind in ("u_s", "u_e"):
            tab_ind = dict(T); tab_ind["u"] = T[ind]
            for iou in m1.CFG["iou_settings"]:
                y = T["y_" + iou]
                for obj_name, objs in m1.CFG["object_sets"].items():
                    for cut_q in m1.CFG["cut_quantiles"]:
                        for seed in m1.CFG["seeds"]:
                            is_primary = (iou == m1.CFG["primary"]["iou"] and obj_name == m1.CFG["primary"]["objects"]
                                          and cut_q == m1.CFG["primary"]["cut_q"] and seed == m1.CFG["primary"]["seed"])
                            info, results, _ = m1.analyse(tab_ind, y, objs, cut_q, seed, m1.CFG, alphas, boot=is_primary)
                            if is_primary:
                                summaries[(split, unit, ind)] = (info, results)
                            for res in results:
                                for cell in res["cells"]:
                                    key = (split, unit, ind, iou, obj_name, cut_q, res["alpha"], cell["established"], cell["applied"])
                                    tally.setdefault(key, {})
                                    tally[key][cell["outcome"]] = tally[key].get(cell["outcome"], 0) + 1
                                    rows.append({"indicator": ind, "iou": iou, "objects": obj_name, "cut_q": cut_q,
                                                 "cut_m": info["cut_m"], "seed": seed, "alpha": res["alpha"],
                                                 "frozen_sweep": res["alpha"] in m1.CFG["alphas_frozen"],
                                                 "established": cell["established"], "applied": cell["applied"],
                                                 "outcome": cell["outcome"], "tau": cell.get("tau"),
                                                 "A_hat": cell.get("A_hat"), "hb_L": cell.get("hb_L"),
                                                 "hb_U": cell.get("hb_U"), "R_hat": cell.get("R_hat"),
                                                 "n_eval_frames": cell.get("n_eval_frames"),
                                                 "split": split, "hb_unit": unit,
                                                 "n_select_units": info["classes"][cell["established"]]["frames_select"]})
    m1.split_frames, m1.Cell = ORIG_SPLIT, ORIG_CELL
    with open(out / "matrix_all_variants.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    json.dump([dict(split=k[0], hb_unit=k[1], indicator=k[2], iou=k[3], objects=k[4], cut_q=k[5], alpha=k[6],
                    cell=f"{k[7]}->{k[8]}", **v) for k, v in sorted(tally.items(), key=lambda kv: kv[0])],
              open(out / "tally_all_variants.json", "w"), indent=1)

    L = [f"M2 SUMMARY  indicators from VEHITS (ref 7): u_s = geometric disagreement (Eq. 3, rotated IoU),"
         f" u_e = 1 - mean confidence (Eq. 1)", rebuild_msg, verify_msg, ""]
    for split, unit, ind in summaries:
        info, results = summaries[(split, unit, ind)]
        L.append("=" * 70)
        L.append(f"SPLIT {split}, HB unit {unit}")
        L.append(f"INDICATOR {ind}    primary variant: iou={m1.CFG['primary']['iou']} "
                 f"objects={m1.CFG['primary']['objects']} cut_q={m1.CFG['primary']['cut_q']} "
                 f"seed={m1.CFG['primary']['seed']}   range cut (m): {m1.fmt(info['cut_m'], 2)}")
        for name, a in info["auroc_eval"].items():
            L.append(f"  AUROC {name}: " + ("NA" if a is None else f"{m1.fmt(a['auroc'])} [{m1.fmt(a['lo'])}, {m1.fmt(a['hi'])}]"))
        for res in results:
            tag = "frozen" if res["alpha"] in m1.CFG["alphas_frozen"] else "EXPLORATORY"
            L.append(f"  alpha={res['alpha']:g} [{tag}]  tau near/far/star = "
                     f"{m1.fmt(res['tau']['near'], 5)} / {m1.fmt(res['tau']['far'], 5)} / {m1.fmt(res['tau']['star'], 5)}")
            for cell in res["cells"]:
                head = f"    T[{cell['established']} -> {cell['applied']}]: {cell['outcome']}"
                if "A_hat" in cell:
                    head += (f" | A={m1.fmt(cell['A_hat'])} HB[{m1.fmt(cell['hb_L'])}, {m1.fmt(cell['hb_U'])}]"
                             f" | R={m1.fmt(cell['R_hat'])} | n_eval={cell['n_eval_frames']}")
                L.append(head)
            for name, g in res["gap"].items():
                L.append(f"    retention gap {name}: {m1.fmt(g['G'])} [{m1.fmt(g.get('lo'))}, {m1.fmt(g.get('hi'))}]")
        L.append("")
    text = "\n".join(L)
    (out / "summary.txt").write_text(text)
    print(text)
    print(f"finished in {time.time() - t0:.0f} s; files in {out}")


def selftest():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + name + (("  " + detail) if detail else ""))
        ok = ok and cond

    if not m1.selftest():
        print("m1 selftest failed; fix m1 first")
        return False

    K = 4
    # a detection seen by all 4 members with identical boxes: u_s = 0, u_e = 1 - mean conf
    box = np.array([10, 2, -0.5, 4, 2, 1.5, 0.3], dtype=np.float64)
    det = {"member_boxes": np.stack([box] * 4), "member_confs": np.array([0.8, 0.8, 0.8, 0.8])}
    u_s, u_e, u_v, mc = indicators(det, K)
    check("identical boxes give u_s = 0", abs(u_s) < 1e-9)
    check("u_e = 1 - mean confidence (all members)", abs(u_e - (1 - 0.8)) < 1e-9)
    check("u_v = 0 when confidences equal", abs(u_v) < 1e-12)

    # a detection seen by 3 of 4 members: zero-padded mean confidence
    det2 = {"member_boxes": np.stack([box] * 3), "member_confs": np.array([0.9, 0.9, 0.9])}
    u_s2, u_e2, u_v2, mc2 = indicators(det2, K)
    check("u_e zero-pads missing members (3 of 4, conf 0.9 -> u_e = 1 - 2.7/4)", abs(u_e2 - (1 - 2.7 / 4)) < 1e-9)

    # u_s grows as boxes disagree: shift one member's box far away -> IoU 0 on its pairs
    far = box.copy(); far[0] += 50
    det3 = {"member_boxes": np.stack([box, box, box, far]), "member_confs": np.array([0.8] * 4)}
    u_s3, *_ = indicators(det3, K)
    # pairs: C(4,2)=6; three pairs among the identical boxes have IoU 1, three pairs with 'far' have IoU 0
    check("u_s = 1 - 3/6 = 0.5 for three-agree-one-far", abs(u_s3 - 0.5) < 1e-9)

    # orientation: both indicators larger means less trustworthy (monotone in disagreement / in 1-conf)
    check("u_s orientation: more disagreement gives larger u_s", u_s3 > u_s)
    check("u_e orientation: lower confidence gives larger u_e", (1 - 0.2) > (1 - 0.8) and u_e2 > u_e)

    print("M2 SELFTEST " + ("PASSED" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    main()

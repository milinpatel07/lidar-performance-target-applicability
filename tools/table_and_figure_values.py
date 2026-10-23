#!/usr/bin/env python3
"""table_and_figure_values.py - frame counts per condition and part, shares of wrong detections, and the
split-0 values behind the settings table and the pair figure. Counts come from the cached per-detection tables
of export_tables.py (split functions of m1/m4, unchanged); A, interval and R are read from the recorded results.

Usage: python3 tools/table_and_figure_values.py   (writes work/table_and_figure_values.json)"""
import csv, json, pickle
import numpy as np
import layout

R = layout.RESULTS
m6 = layout.load_analysis()
m1, m4, m1n = m6.m1, m6.m4, m6.m3.m1
C = pickle.load(open(layout.CACHE, "rb"))
ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
kign = m6.subset(ktab, why == "")
out = {}

# ---------------- a) frames per class and part
def distance_counts(tab, car, cfg, mod):
    codes = mod.split_frames(tab["n_frames"], 0, cfg); carm = tab["cls"] == car
    g = carm & (codes[tab["fpos"]] == 0)
    cut = float(np.quantile(tab["rng"][g], 0.5))
    res = {"cut_m": cut}
    for pname, pc in (("grid", 0), ("select", 1), ("eval", 2)):
        fr = np.where(codes == pc)[0]
        m = carm & (codes[tab["fpos"]] == pc)
        near = set(np.unique(tab["fpos"][m & (tab["rng"] <= cut)])); far = set(np.unique(tab["fpos"][m & (tab["rng"] > cut)]))
        res[pname] = {"frames_in_part": int(len(fr)), "frames_with_car": len(near | far), "near": len(near), "far": len(far),
                      "both": len(near & far), "near_only": len(near - far), "far_only": len(far - near),
                      "no_car_detection": int(len(fr)) - len(near | far),
                      "car_detections_near": int((m & (tab["rng"] <= cut)).sum()), "car_detections_far": int((m & (tab["rng"] > cut)).sum())}
    return res

def dataset_counts(tab, car):
    nF = tab["n_frames"]; codes = np.zeros(nF, np.int8)
    codes[np.random.default_rng(0).permutation(nF)[: int(round(m4.CFG["frac_select"] * nF))]] = 1
    carm = tab["cls"] == car; res = {}
    for pname, pc in (("select", 1), ("eval", 0)):
        withcar = len(np.unique(tab["fpos"][carm & (codes[tab["fpos"]] == pc)]))
        res[pname] = {"frames_in_part": int((codes == pc).sum()), "frames_with_car": withcar,
                      "no_car_detection": int((codes == pc).sum()) - withcar}
    cells = m4.car_cells(tab, car, "u_s", 0, m4.CFG["frac_select"])
    assert cells["select"].m == res["select"]["frames_with_car"] and cells["eval"].m == res["eval"]["frames_with_car"]
    return res

out["a_distance"] = {"KITTI_as_run": distance_counts(ktab, "Car", m1.CFG, m1), "KITTI_rule": distance_counts(kign, "Car", m1.CFG, m1),
                     "nuScenes": distance_counts(ntab, "car", m1n.CFG, m1n)}
out["a_dataset"] = {"KITTI_as_run": dataset_counts(ktab, "Car"), "KITTI_rule": dataset_counts(kign, "Car"), "nuScenes": dataset_counts(ntab, "car")}
rain = [r for r in csv.DictReader(open(R / "m6_five_splits/C_weather_nuscenes.csv")) if r["seed"] == "0" and r["indicator"] == "u_s" and r["alpha"] == "0.1"]
out["a_rain_m6_seed0"] = {f"{r['established']}->{r['applied']}": {"frames_select(established)": int(r["frames_select"]), "frames_eval(applied)": int(r["frames_eval"])} for r in rain}

# ---------------- b) KITTI u_s retention at alpha 1e-2, whole-dataset threshold
out["b"] = [{k: r.get(k) for k in ("protocol", "source", "target", "tau", "A_hat", "hb_L", "hb_U", "R_hat", "outcome")}
            for r in csv.DictReader(open(R / "m6_five_splits/B_shift_seeds_protocol.csv"))
            if r["seed"] == "0" and r["indicator"] == "u_s" and r["alpha"] == "0.01" and r["source"] == "kitti"]
m4rows = list(csv.DictReader(open(R / "m4_dataset_change/shift_matrix.csv")))
out["b_m4_header"] = list(m4rows[0].keys())
out["b_m4"] = [r for r in m4rows if r.get("indicator") == "u_s" and r.get("alpha") in ("0.01",) and r.get("source") == "kitti"]

# ---------------- c) share of wrong car detections per distance class
def share(tab, car, cut, codes=None, part=None):
    m = tab["cls"] == car
    if codes is not None: m = m & (codes[tab["fpos"]] == part)
    y = tab["y_A_iou0.5"]; n, f = m & (tab["rng"] <= cut), m & (tab["rng"] > cut)
    return {"near": float(1 - y[n].mean()), "far": float(1 - y[f].mean()), "n_near": int(n.sum()), "n_far": int(f.sum())}
ncut = out["a_distance"]["nuScenes"]["cut_m"]; ncodes = m1n.split_frames(ntab["n_frames"], 0, m1n.CFG)
kcut = out["a_distance"]["KITTI_rule"]["cut_m"]; kcodes = m1.split_frames(ktab["n_frames"], 0, m1.CFG)
kcut0 = out["a_distance"]["KITTI_as_run"]["cut_m"]
out["c"] = {"nuScenes_eval_split0": share(ntab, "car", ncut, ncodes, 2), "nuScenes_all_frames_same_cut": share(ntab, "car", ncut),
            "KITTI_as_run_eval_split0": share(ktab, "Car", kcut0, kcodes, 2), "KITTI_rule_eval_split0": share(kign, "Car", kcut, kcodes, 2)}

# ---------------- d) values of the split-0 pair figure (alpha 0.1), with and without the KITTI rule
def pick(rows, **kw):
    r = [x for x in rows if all(x[k] == v for k, v in kw.items())]
    assert len(r) == 1, (kw, len(r)); return r[0]
A6 = list(csv.DictReader(open(R / "m6_five_splits/A_kitti_range_protocol.csv")))
B6 = list(csv.DictReader(open(R / "m6_five_splits/B_shift_seeds_protocol.csv")))
C6 = list(csv.DictReader(open(R / "m6_five_splits/C_weather_nuscenes.csv")))
M2 = list(csv.DictReader(open(R / "m2_kitti_distance/matrix_all_variants.csv")))
M3 = list(csv.DictReader(open(R / "m3_nuscenes_distance/matrix_all_variants.csv")))
rows = []
for ind in ("u_s", "u_e"):
    for (e, a) in (("near", "far"), ("far", "near")):
        for proto in ("kitti_ignore", "as_run"):
            r = pick(A6, protocol=proto, indicator=ind, seed="0", alpha="0.1", established=e, applied=a)
            rows.append(("KITTI distance", proto, ind, f"{e}->{a}", r, "results/m6_five_splits/A_kitti_range_protocol.csv"))
        r = pick(M3, indicator=ind, iou="A_iou0.5", objects="car", cut_q="0.5", seed="0", alpha="0.1", established=e, applied=a)
        rows.append(("nuScenes distance", "-", ind, f"{e}->{a}", r, "results/m3_nuscenes_distance/matrix_all_variants.csv"))
    for (e, a) in (("clear", "rain"), ("rain", "clear")):
        r = pick(C6, indicator=ind, seed="0", alpha="0.1", established=e, applied=a)
        rows.append(("nuScenes weather", "-", ind, f"{e}->{a}", r, "results/m6_five_splits/C_weather_nuscenes.csv"))
    for (s, t) in (("nuscenes", "kitti"), ("kitti", "nuscenes")):
        for proto in ("kitti_ignore", "as_run"):
            r = pick(B6, protocol=proto, indicator=ind, seed="0", alpha="0.1", source=s, target=t)
            rows.append(("change of dataset", proto, ind, f"{s}->{t}", r, "results/m6_five_splits/B_shift_seeds_protocol.csv"))
out["d"] = [{"pair": p, "protocol": pr, "indicator": i, "direction": d, "A": float(r["A_hat"]), "L": float(r["hb_L"]),
             "U": float(r["hb_U"]), "R": float(r["R_hat"]), "outcome": r["outcome"], "file": f} for p, pr, i, d, r, f in rows]
# m2 primary variant (labels as run) for the KITTI distance pair
out["d_m2_as_run"] = [{"indicator": r["indicator"], "dir": f"{r['established']}->{r['applied']}", "A": r["A_hat"], "L": r["hb_L"], "U": r["hb_U"], "R": r["R_hat"]}
                      for r in M2 if r["iou"] == "A_iou0.5" and r["objects"] == "Car" and r["cut_q"] == "0.5" and r["seed"] == "0"
                      and r["alpha"] == "0.1" and r["established"] != r["applied"]]
json.dump(out, open(layout.WORK / "table_and_figure_values.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))

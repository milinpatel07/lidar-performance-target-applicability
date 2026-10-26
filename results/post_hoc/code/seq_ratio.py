#!/usr/bin/env python3
"""
seq_ratio.py (seq-0.2, 2026-10-21) - POST-HOC analysis (added after the outcomes were known):
sequence-level test of the per-frame target A_c(tau) = E[a_f(tau) | f in c] <= alpha.

Method A (primary). The recorded sequence (KITTI drive, nuScenes scene) is the independent unit and the
per-frame target is kept. For sequence s, N_s = frames of s in condition c (frames with at least one car
detection of c) and S_s(tau) = sum of a_f(tau) over these frames. For independent sequences A_c = E[S] / E[N],
so A_c <= alpha exactly when E[S - alpha N] <= 0. With N_max(c) = largest N_s over all validation sequences
of c (fixed from frame-to-sequence assignment and box positions only, before any outcome),
Y_s = (S_s - alpha N_s + alpha N_max) / N_max lies in [0, 1] and E[Y] <= alpha exactly when A_c <= alpha.
Selection and evaluation are the paper's (m1 HB p-value, fixed sequence from the lowest candidate, one-sided
HB bounds at delta/2), with Y_s as the loss of a unit. Units are the sequences with N_s >= 1.
Method B (sensitivity): the evaluation bounds from the betting confidence interval of Waudby-Smith and Ramdas
(confseq.betting.betting_ci, hedged capital process, theta = 1/2, i.e. each side at delta/2); selection from A.
B2: AUROC of the three pairs of Fig. 5 on the evaluation part of split 0 (frame division, as in the paper) with
a 95 % percentile bootstrap over recorded sequences.

Divisions by recorded sequence as in the paper: m7 (nuScenes scenes, m3.split_variants) and m8 (KITTI drives;
change of dataset: KITTI drives and nuScenes scenes in halves). Statistics come from m1 unchanged (loaded through
code/experiments, as in v24/v25). Gate before any new number: (1) with every frame its own sequence (N_s = 1),
the frame division reproduces the recorded frame-unit rows of the paper; (2) the sequence division with frame
units reproduces the recorded m7/m8 frame-unit rows. The script stops on any difference.
Inputs read-only: cache/tables.pkl, recorded CSVs, /data/nuscenes (sample.json, scene.json),
ext/kitti_devkit (mapping files). Writes only below --out.
"""
import argparse, csv, importlib.util, json, math, pickle, platform, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

SCRIPT_VERSION = "seq-0.2"   # 0.2: configuration check limited to the statistics keys (m3 renames classes)
W = Path("/data/work"); REL = W
CODE = REL / "code/experiments"
spec = importlib.util.spec_from_file_location("m6", str(CODE / "m6_protocol_seeds_weather.py"))
m6 = importlib.util.module_from_spec(spec); sys.modules["m6"] = m6; spec.loader.exec_module(m6)
m1, m3, m4 = m6.m1, m6.m3, m6.m4

DELTA = m1.CFG["delta"]
ALPHAS = m6.ALPHAS                    # 1e-2, 1e-3, 1e-4 (target), 0.05, 0.1 (exploratory)
SEEDS = m6.SEEDS                      # splits 0..4
IND = m6.IND
SEED_BOOT = 20261021                  # B2 bootstrap
SEED_BET = 20261021                   # Method B: order of the units, permutation seed = SEED_BET + split
N_BOOT = 2000
BREAKS = 10000                        # grid of betting_ci; confseq widens each bound by one step (1e-4)
OUT_NAMES = {"applies": "applicable", "does not apply": "not applicable", "not determined": "not determined",
             "no threshold established": "no threshold selected"}


def decide(L, U, alpha):
    return "applicable" if U <= alpha else ("not applicable" if L > alpha else "not determined")


class SeqCell:
    """Sequences of one condition in one part; a sequence is a unit if it holds at least one frame of the condition."""

    def __init__(self, fpos, u, y, unit_f, nmax):
        self.fc = m1.Cell(fpos, u, y)
        self.seqs, self.fs = np.unique(unit_f[self.fc.frames], return_inverse=True)
        self.m = len(self.seqs)
        self.N = np.bincount(self.fs, minlength=self.m).astype(float)
        self.nmax = float(nmax)
        assert self.m == 0 or self.N.max() <= self.nmax, "N_s exceeds N_max"

    def S(self, tau):
        return np.bincount(self.fs, weights=self.fc.a_f(tau), minlength=self.m)

    def Y(self, tau, alpha):
        return np.clip((self.S(tau) - alpha * self.N + alpha * self.nmax) / self.nmax, 0.0, 1.0)

    def retention(self, tau):
        return self.fc.retention(tau)


def select(cell, grid, alpha):
    p = [m1.hb_pvalue(cell.Y(t, alpha).sum(), cell.m, alpha) for t in grid]
    j = m1.chain_index([p], DELTA)
    return float(grid[j]) if j >= 0 else None


def evaluate(cell, tau, alpha):
    Y = cell.Y(tau, alpha); s, n = float(Y.sum()), cell.m
    U, L = m1.hb_upper(s, n, DELTA / 2), m1.hb_lower(s, n, DELTA / 2)
    return {"mean_Y": s / n if n else float("nan"), "L_Y": L, "U_Y": U,
            "ratio": float(cell.S(tau).sum() / cell.N.sum()) if n else float("nan"),
            "outcome": decide(L, U, alpha), "retention": cell.retention(tau)}


def betting_bounds(Y, seed):
    from confseq.betting import betting_ci
    x = np.asarray(Y, float)[np.random.default_rng(seed).permutation(len(Y))]
    l, u = betting_ci(x, alpha=DELTA, breaks=BREAKS)
    return float(l), float(u)


# ------------------------------------------------------------------ divisions and units
def drive_index(devkit, fids):
    """Copy of m8_kitti_drive_split.drive_index (m8-0.1): KITTI object frame -> raw drive."""
    rand = [int(v) for v in (devkit / "mapping/train_rand.txt").read_text().strip().split(",")]
    mp = [l.split() for l in (devkit / "mapping/train_mapping.txt").read_text().splitlines() if l.strip()]
    assert len(rand) == len(mp) == 7481 and sorted(rand) == list(range(1, 7482)), "devkit mapping files incomplete"
    drv = [mp[rand[int(f)] - 1][1] for f in fids]
    drives = sorted(set(drv)); pos = {d: i for i, d in enumerate(drives)}
    return np.array([pos[d] for d in drv], dtype=np.int64), drives


def three_parts(div_f, seed):
    """Grid/selection/evaluation codes per frame (0/1/2), drawn over the units of div_f (m1.split_frames; m7, m8)."""
    return m1.split_frames(int(div_f.max()) + 1, seed, m1.CFG)[div_f]


def halves(div_f, seed):
    """Selection (1) / evaluation (0) per frame, as m4.car_cells and m8.unit_cells."""
    nU = int(div_f.max()) + 1
    codes = np.zeros(nU, dtype=np.int8)
    codes[np.random.default_rng(seed).permutation(nU)[: int(round(m4.CFG["frac_select"] * nU))]] = 1
    return codes[div_f]


def n_per_unit(tab, mask, unit_f):
    frames = np.unique(tab["fpos"][mask])
    return np.bincount(unit_f[frames]) if len(frames) else np.zeros(0, int)


def within(D, kind, ind, seed, div_f, unit_f):
    """KITTI/nuScenes distance (kind 'distance') or nuScenes weather (kind 'weather'), as m1.analyse / m6.class_matrix."""
    tab, car = D["tab"], D["car"]
    dcode = three_parts(div_f, seed)[tab["fpos"]]
    car_m = tab["cls"] == car
    if kind == "distance":
        g = car_m & (dcode == 0)
        cut = float(np.quantile(tab["rng"][g], 0.5))
        cond = (tab["rng"] > cut).astype(int); names = ("near", "far")
    else:
        cond = D["det_class"]; g = car_m & (cond >= 0) & (dcode == 0); cut = None; names = ("clear", "rain")
    grid = np.unique(np.quantile(tab[ind][g], m1.CFG["grid_levels"]))
    ns = {c: n_per_unit(tab, car_m & (cond == i), unit_f) for i, c in enumerate(names)}
    nmax = {c: int(v.max()) for c, v in ns.items()}
    y = tab["y_A_iou0.5"]; cells = {}
    for part, code in (("select", 1), ("eval", 2)):
        for i, c in enumerate(names):
            m = car_m & (cond == i) & (dcode == code)
            cells[(part, c)] = SeqCell(tab["fpos"][m], tab[ind][m], y[m], unit_f, nmax[c])
    return names, cells, grid, nmax, {"cut_m": cut, "ns": ns}


def dataset(DK, DN, ind, seed, div, unit):
    """Change of dataset and detector, as m6 part B / m8 part B; div and unit map 'KITTI'/'nuScenes' to arrays."""
    names = ("nuScenes", "KITTI"); cells, nmax, ns = {}, {}, {}
    for name, D in (("KITTI", DK), ("nuScenes", DN)):
        tab = D["tab"]; car_m = tab["cls"] == D["car"]
        dcode = halves(div[name], seed)[tab["fpos"]]
        ns[name] = n_per_unit(tab, car_m, unit[name]); nmax[name] = int(ns[name].max())
        for part, code in (("select", 1), ("eval", 0)):
            m = car_m & (dcode == code)
            cells[(part, name)] = SeqCell(tab["fpos"][m], tab[ind][m], tab["y_A_iou0.5"][m], unit[name], nmax[name])
    return names, cells, np.array(m4.CFG["grid_levels"]), nmax, {"cut_m": None, "ns": ns}


PAIRS = ("KITTI distance", "nuScenes distance", "nuScenes weather", "change of dataset and detector")


def build(pair, data, ind, seed, mode):
    """mode: 'frame/frame' (gate 1), 'seq/frame' (gate 2), 'seq/seq' (Method A): division / unit."""
    K, N = data["K"], data["N"]
    fk, fn = np.arange(K["tab"]["n_frames"]), np.arange(N["tab"]["n_frames"])
    div_seq, unit_seq = mode.split("/")[0] == "seq", mode.split("/")[1] == "seq"
    dk, dn = (K["seq"] if div_seq else fk), (N["seq"] if div_seq else fn)
    uk, un = (K["seq"] if unit_seq else fk), (N["seq"] if unit_seq else fn)
    if pair == "KITTI distance":
        return within(K, "distance", ind, seed, dk, uk)
    if pair == "nuScenes distance":
        return within(N, "distance", ind, seed, dn, un)
    if pair == "nuScenes weather":
        return within(N, "weather", ind, seed, dn, un)
    return dataset(K, N, ind, seed, {"KITTI": dk, "nuScenes": dn}, {"KITTI": uk, "nuScenes": un})


def run(pair, data, ind, seed, mode, alphas=ALPHAS):
    names, cells, grid, nmax, info = build(pair, data, ind, seed, mode)
    rows = []
    for alpha in alphas:
        tau = {c: select(cells[("select", c)], grid, alpha) for c in names}
        for c in names:
            for c2 in names:
                r = {"pair": pair, "direction": f"{c}->{c2}", "established": c, "applied": c2, "indicator": ind,
                     "alpha": alpha, "limit": "target" if alpha in m1.CFG["alphas_frozen"] else "exploratory",
                     "split": seed, "own_condition": c == c2, "tau_c": tau[c],
                     "n_select_seq": cells[("select", c)].m, "n_eval_seq": cells[("eval", c2)].m,
                     "N_max_select": nmax[c], "N_max_eval": nmax[c2],
                     "n_eval_frames": int(cells[("eval", c2)].N.sum()), "cut_m": info["cut_m"]}
                if tau[c] is None:
                    r["outcome"] = "no threshold selected"
                else:
                    r.update(evaluate(cells[("eval", c2)], tau[c], alpha))
                rows.append(r)
    return rows, cells, info


# ------------------------------------------------------------------ gate
def recorded():
    A6 = pd.read_csv(W / "m6/results/A_kitti_range_protocol.csv"); A6 = A6[A6.protocol == "kitti_ignore"]
    B6 = pd.read_csv(W / "m6/results/B_shift_seeds_protocol.csv"); B6 = B6[B6.protocol == "kitti_ignore"]
    M7 = pd.read_csv(REL / "results/m7_scene_split.csv")
    A8 = pd.read_csv(REL / "results/m8/A_kitti_distance_drive.csv"); A8 = A8[(A8.protocol == "kitti_ignore") & (A8.hb_unit == "frame")]
    B8 = pd.read_csv(REL / "results/m8/B_dataset_drive.csv"); B8 = B8[(B8.protocol == "kitti_ignore") & (B8.hb_unit == "frame")]
    dsn = {"kitti": "KITTI", "nuscenes": "nuScenes"}
    B6 = B6.assign(established=B6.source.map(dsn), applied=B6.target.map(dsn))
    B8 = B8.assign(established=B8.source.map(dsn), applied=B8.target.map(dsn))
    return {("frame/frame", "KITTI distance"): A6,
            ("frame/frame", "nuScenes distance"): M7[(M7.setting == "distance") & (M7.variant == "frame")],
            ("frame/frame", "nuScenes weather"): M7[(M7.setting == "rain") & (M7.variant == "frame")],
            ("frame/frame", "change of dataset and detector"): B6,
            ("seq/frame", "KITTI distance"): A8,
            ("seq/frame", "nuScenes distance"): M7[(M7.setting == "distance") & (M7.variant == "scene_frame_unit")],
            ("seq/frame", "nuScenes weather"): M7[(M7.setting == "rain") & (M7.variant == "scene_frame_unit")],
            ("seq/frame", "change of dataset and detector"): B8}


def close(a, b, tol):
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return b is None or (isinstance(b, float) and math.isnan(b))
    return b is not None and not (isinstance(b, float) and math.isnan(b)) and abs(float(a) - float(b)) <= tol


def gate(data, modes=("frame/frame", "seq/frame"), seeds=SEEDS):
    """Compare recomputed rows with the recorded rows: outcome and tau exactly (1e-12), values to 1e-9."""
    rec = recorded(); bad, n = [], 0
    for mode in modes:
        for pair in PAIRS:
            R = rec[(mode, pair)]
            for ind in IND:
                for seed in seeds:
                    rows, _, _ = run(pair, data, ind, seed, mode)
                    for r in rows:
                        q = R[(R.indicator == ind) & (R.seed == seed) & (R.alpha == r["alpha"]) &
                              (R.established == r["established"]) & (R.applied == r["applied"])]
                        n += 1
                        if len(q) != 1:
                            bad.append(f"{mode} {pair} {ind} split {seed} alpha {r['alpha']} {r['direction']}: {len(q)} recorded rows"); continue
                        q = q.iloc[0]
                        ok = OUT_NAMES[q.outcome] == r["outcome"]
                        if "tau" in q.index:
                            ok &= close(r["tau_c"], None if q.tau != q.tau else float(q.tau), 1e-12)
                        if r["tau_c"] is not None:
                            ok &= all(close(r[k], float(q[kr]), 1e-9) for k, kr in
                                      (("mean_Y", "A_hat"), ("L_Y", "hb_L"), ("U_Y", "hb_U"), ("retention", "R_hat")))
                        if not ok:
                            bad.append(f"{mode} {pair} {ind} split {seed} alpha {r['alpha']} {r['direction']}")
    return n, bad


# ------------------------------------------------------------------ B2: AUROC with a sequence bootstrap
def auroc(u, y, w=None):
    gid, ng = m1.auroc_groups(-u, y)
    return m1.auroc_weighted(gid, ng, y, np.ones(len(u)) if w is None else w)


def auroc_bootstrap(data):
    """Three pairs of Fig. 5, evaluation part of split 0 (frame division as in the paper). Sequences are resampled
    with replacement: jointly for near/far (shared sequences), within each condition for clear/rain (disjoint
    scenes) and for the two datasets (independent recordings)."""
    K, N = data["K"], data["N"]; rows = []
    rng = np.random.default_rng(SEED_BOOT)

    def boot(groups, joint):
        """groups: list of (u, y, seq) per condition; returns point values and replicate matrix (N_BOOT x 2)."""
        pts = [auroc(u, y) for u, y, _ in groups]
        reps = np.zeros((N_BOOT, len(groups)))
        if joint:
            seqs = np.unique(np.concatenate([s for _, _, s in groups])); pos = {v: i for i, v in enumerate(seqs)}
            idx = [np.array([pos[v] for v in s]) for _, _, s in groups]
            for b in range(N_BOOT):
                cnt = rng.multinomial(len(seqs), np.full(len(seqs), 1 / len(seqs))).astype(float)
                reps[b] = [auroc(u, y, cnt[ix]) for (u, y, _), ix in zip(groups, idx)]
        else:
            loc = [np.unique(s, return_inverse=True) for _, _, s in groups]
            for b in range(N_BOOT):
                for k, ((u, y, _), (sq, ix)) in enumerate(zip(groups, loc)):
                    cnt = rng.multinomial(len(sq), np.full(len(sq), 1 / len(sq))).astype(float)
                    reps[b, k] = auroc(u, y, cnt[ix])
        return pts, reps

    def emit(pair, ind, names, groups, joint, nseq):
        pts, reps = boot(groups, joint)
        for k, c in enumerate(names):
            lo, hi = np.nanpercentile(reps[:, k], [2.5, 97.5])
            rows.append({"pair": pair, "indicator": ind, "quantity": f"AUROC {c}", "point": pts[k], "lo95": lo, "hi95": hi,
                         "detections": len(groups[k][0]), "sequences": nseq[k], "resampling": "joint" if joint else "per condition",
                         "replicates": N_BOOT, "seed": SEED_BOOT})
        d = reps[:, 1] - reps[:, 0]; lo, hi = np.nanpercentile(d, [2.5, 97.5])
        rows.append({"pair": pair, "indicator": ind, "quantity": f"AUROC {names[1]} - AUROC {names[0]}", "point": pts[1] - pts[0],
                     "lo95": lo, "hi95": hi, "detections": len(groups[0][0]) + len(groups[1][0]), "sequences": "",
                     "resampling": "joint" if joint else "per condition", "replicates": N_BOOT, "seed": SEED_BOOT})

    # KITTI near -> far, u_s
    T = K["tab"]; dcode = m1.split_frames(T["n_frames"], 0, m1.CFG)[T["fpos"]]; car = T["cls"] == "Car"
    cut = float(np.quantile(T["rng"][car & (dcode == 0)], 0.5)); far = T["rng"] > cut
    g = [(T["u_s"][m], T["y_A_iou0.5"][m], K["seq"][T["fpos"][m]]) for m in (car & (dcode == 2) & ~far, car & (dcode == 2) & far)]
    emit("KITTI distance", "u_s", ("near", "far"), g, True, [len(np.unique(x[2])) for x in g])
    # nuScenes clear -> rain, u_e
    T = N["tab"]; dcode = m1.split_frames(T["n_frames"], 0, m1.CFG)[T["fpos"]]; car = T["cls"] == "car"; dc = N["det_class"]
    g = [(T["u_e"][m], T["y_A_iou0.5"][m], N["seq"][T["fpos"][m]]) for m in (car & (dcode == 2) & (dc == 0), car & (dcode == 2) & (dc == 1))]
    assert not set(g[0][2]) & set(g[1][2]), "clear and rain share a scene"
    emit("nuScenes weather", "u_e", ("clear", "rain"), g, False, [len(np.unique(x[2])) for x in g])
    # nuScenes -> KITTI, u_s (m4 halves, split 0)
    g = []
    for D in (N, K):
        T = D["tab"]; m = (T["cls"] == D["car"]) & (halves(np.arange(T["n_frames"]), 0)[T["fpos"]] == 0)
        g.append((T["u_s"][m], T["y_A_iou0.5"][m], D["seq"][T["fpos"][m]]))
    emit("change of dataset and detector", "u_s", ("nuScenes", "KITTI"), g, False, [len(np.unique(x[2])) for x in g])
    return rows


# ------------------------------------------------------------------ main
def load(devkit, meta):
    C = pickle.load(open(REL / "cache/tables.pkl", "rb"))
    ktab, why, ntab = C["ktab"], C["why"], C["ntab"]
    kign = m6.subset(ktab, why == "")
    didx, drives = drive_index(devkit, ktab["fids"])
    sidx, scenes = m3.scene_index(meta, ntab["fids"])
    wcls, wcounts = m6.nusc_weather_classes(meta, ntab["fids"])
    return {"K": {"tab": kign, "car": "Car", "seq": didx, "seq_names": drives},
            "N": {"tab": ntab, "car": "car", "seq": sidx, "seq_names": scenes, "det_class": wcls[ntab["fpos"]]},
            "prov": {"export_version": C["prov"].get("export_version"), "weather_frames": wcounts,
                     "kitti_drives": len(drives), "nuscenes_scenes": len(scenes)}}


def write_csv(path, rows):
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REL / "results/seq_ratio"))
    ap.add_argument("--devkit", default=str(REL / "ext/kitti_devkit"))
    ap.add_argument("--nusc-meta", default="/data/nuscenes/v1.0-trainval")
    a = ap.parse_args()
    t0 = time.time(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    meta, devkit = Path(a.nusc_meta), Path(a.devkit)
    stat_keys = ("delta", "alphas_frozen", "alphas_exploratory", "frac_grid", "frac_select", "grid_levels", "cut_quantiles", "seeds")
    assert all(m3.m1.CFG[k] == m1.CFG[k] for k in stat_keys), "m3 and m6 use different statistics settings"
    data = load(devkit, meta)
    prov = {"script_version": SCRIPT_VERSION, "post_hoc": True, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "python": platform.python_version(), "numpy": np.__version__, "statistics_from": str(CODE),
            "m1_cfg": m1.CFG, "alphas": ALPHAS, "delta": DELTA, "splits": SEEDS, "seed_bootstrap": SEED_BOOT,
            "seed_betting_order": f"{SEED_BET} + split", "betting_breaks": BREAKS, "n_boot": N_BOOT, **data["prov"],
            "inputs_sha256": {str(f): m1.sha256(f) for f in [REL / "cache/tables.pkl", meta / "sample.json", meta / "scene.json",
                                                              devkit / "mapping/train_rand.txt", devkit / "mapping/train_mapping.txt",
                                                              W / "m6/results/A_kitti_range_protocol.csv", W / "m6/results/B_shift_seeds_protocol.csv",
                                                              REL / "results/m7_scene_split.csv", REL / "results/m8/A_kitti_distance_drive.csv",
                                                              REL / "results/m8/B_dataset_drive.csv"]}}
    print(f"{SCRIPT_VERSION}: KITTI frames {data['K']['tab']['n_frames']} in {data['prov']['kitti_drives']} drives, "
          f"nuScenes frames {data['N']['tab']['n_frames']} in {data['prov']['nuscenes_scenes']} scenes", flush=True)

    n, bad = gate(data)
    msg = (f"GATE {'PASSED' if not bad else 'FAILED'}: {n} recomputed rows compared with the recorded rows "
           f"(frame division with N_s = 1 against m6 A/B and m7 frame rows; sequence division with frame units against "
           f"m7 scene_frame_unit and m8 frame-unit rows); {len(bad)} differ")
    print(msg, flush=True); prov["gate"] = msg
    if bad:
        (out / "GATE_FAILED.txt").write_text(msg + "\n" + "\n".join(bad) + "\n"); sys.exit("stopping: gate failed")
    (out / "GATE_PASSED.txt").write_text(msg + "\n")

    rows, ns_rows = [], []
    for pair in PAIRS:
        for ind in IND:
            for seed in SEEDS:
                rr, cells, info = run(pair, data, ind, seed, "seq/seq")
                for r in rr:
                    rows.append(dict(r, method="A"))
                    if r["tau_c"] is not None:
                        Y = cells[("eval", r["applied"])].Y(r["tau_c"], r["alpha"])
                        L, U = betting_bounds(Y, SEED_BET + seed)
                        rows.append(dict(r, method="B", L_Y=L, U_Y=U, outcome=decide(L, U, r["alpha"])))
                    else:
                        rows.append(dict(r, method="B"))
                if ind == IND[0]:
                    for c, v in info["ns"].items():
                        v = v[v > 0]
                        ns_rows.append({"pair": pair, "condition": c, "split": seed, "sequences": len(v), "N_s_min": int(v.min()),
                                        "N_s_median": float(np.median(v)), "N_s_max": int(v.max()), "frames": int(v.sum()),
                                        "cut_m": info["cut_m"]})
            print(f"  {pair} {ind} done ({time.time() - t0:.0f} s)", flush=True)
    cols = ["pair", "direction", "established", "applied", "indicator", "alpha", "limit", "split", "method", "own_condition",
            "tau_c", "n_select_seq", "n_eval_seq", "N_max_select", "N_max_eval", "n_eval_frames", "mean_Y", "L_Y", "U_Y",
            "ratio", "outcome", "retention", "cut_m"]
    rows = [{k: r.get(k) for k in cols} for r in rows]
    write_csv(out / "outcomes.csv", rows)
    write_csv(out / "ns_per_condition.csv", ns_rows)
    df = pd.DataFrame(rows)
    order = ["applicable", "not applicable", "not determined", "no threshold selected"]
    s = (df.groupby(["method", "pair", "direction", "own_condition", "indicator", "alpha", "limit"]).outcome
         .value_counts().unstack(fill_value=0).reindex(columns=order, fill_value=0).reset_index())
    s.to_csv(out / "summary.csv", index=False)
    print(f"Method A and B done ({time.time() - t0:.0f} s); B2 bootstrap ...", flush=True)
    write_csv(out / "auroc_bootstrap.csv", auroc_bootstrap(data))
    prov["finished"] = time.strftime("%Y-%m-%d %H:%M:%S"); prov["script_sha256"] = m1.sha256(__file__)
    (out / "provenance.json").write_text(json.dumps(prov, indent=2, default=str))
    print(f"finished in {time.time() - t0:.0f} s; files in {out}")


if __name__ == "__main__":
    main()

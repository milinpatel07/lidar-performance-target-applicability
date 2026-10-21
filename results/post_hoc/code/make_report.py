#!/usr/bin/env python3
"""make_report.py (seq-0.1) - REPORT.md of the post-hoc sequence-level test, built only from the files of
release/results/seq_ratio and the recorded frame-unit and sequence-unit rows. No value is typed in."""
import argparse, re
from pathlib import Path
import pandas as pd

W = Path("/work"); REL = W / "release"
DSN = {"kitti": "KITTI", "nuscenes": "nuScenes"}
NAMES = {"applies": "applicable", "does not apply": "not applicable", "not determined": "not determined",
         "no threshold established": "no threshold selected"}


def recorded(variant):
    """Rows of the paper: variant 'frame' (Fig. 4, frame division, frame unit) or 'sequence' (sequence division and unit)."""
    M7 = pd.read_csv(REL / "results/m7_scene_split.csv")
    if variant == "frame":
        A = pd.read_csv(W / "m6/results/A_kitti_range_protocol.csv"); A = A[A.protocol == "kitti_ignore"]
        B = pd.read_csv(W / "m6/results/B_shift_seeds_protocol.csv"); B = B[B.protocol == "kitti_ignore"]
        m7v = "frame"
    else:
        A = pd.read_csv(REL / "results/m8/A_kitti_distance_drive.csv"); A = A[(A.protocol == "kitti_ignore") & (A.hb_unit == "drive")]
        B = pd.read_csv(REL / "results/m8/B_dataset_drive.csv"); B = B[(B.protocol == "kitti_ignore") & (B.hb_unit == "drive")]
        m7v = "scene_scene_unit"
    B = B.assign(established=B.source.map(DSN), applied=B.target.map(DSN))
    parts = [A.assign(pair="KITTI distance"),
             M7[(M7.setting == "distance") & (M7.variant == m7v)].assign(pair="nuScenes distance"),
             M7[(M7.setting == "rain") & (M7.variant == m7v)].assign(pair="nuScenes weather"),
             B.assign(pair="change of dataset and detector")]
    R = pd.concat(parts, ignore_index=True)[["pair", "indicator", "seed", "alpha", "established", "applied", "outcome"]]
    R["outcome"] = R.outcome.map(NAMES); R["direction"] = R.established + "->" + R.applied
    return R


def lim(a):
    return {0.01: "1e-2", 0.001: "1e-3", 0.0001: "1e-4", 0.05: "0.05†", 0.1: "0.1†"}[a]


def table(df):
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(REL / "results/seq_ratio")); a = ap.parse_args()
    out = Path(a.out)
    O = pd.read_csv(out / "outcomes.csv"); NS = pd.read_csv(out / "ns_per_condition.csv"); AU = pd.read_csv(out / "auroc_bootstrap.csv")
    gate = (out / "GATE_PASSED.txt").read_text().strip()
    tests = (out / "tests.log").read_text().strip().splitlines()[-1] if (out / "tests.log").exists() else "tests.log missing"
    key = ["pair", "direction", "indicator", "alpha"]
    A, B = O[O.method == "A"], O[O.method == "B"]
    tr = lambda d: d[d.established != d.applied]
    L = ["# Sequence-level test of the per-frame target (post-hoc analysis)", "",
         "**Post-hoc.** This analysis was added after the outcomes of the paper were known. It is not part of the predictions "
         "fixed in advance. † marks the exploratory limits 0.05 and 0.1, which are not safety targets.", "",
         f"Method A: recorded sequence (KITTI drive, nuScenes scene) as the independent unit, per-frame target kept through "
         f"Y_s = (S_s − αN_s + αN_max)/N_max; selection and evaluation as in the paper (HB, δ = 0.05, bounds at δ/2). "
         f"Method B: evaluation bounds from the betting interval (Waudby-Smith and Ramdas, `confseq` 0.0.11, hedged capital "
         f"process, θ = 1/2), selection from Method A. Division by recorded sequence as in the paper (m7 scenes, m8 drives; "
         f"for the change of dataset and detector, the existing m8 division into halves of KITTI drives and nuScenes scenes, "
         f"so no new division was built). Splits 0 to 4; candidate thresholds as in the paper.", "",
         f"Checks: {gate}. Sanity tests (`tests/test_seq_ratio.py`): {tests}.", ""]

    # 1. Fig. 4 not applicable outcomes
    F = tr(recorded("frame"))
    fna = F[F.outcome == "not applicable"].groupby(key).size().rename("frame unit").reset_index()
    def count(D, what):
        return D[D.outcome == what].groupby(key).size()
    rows = []
    for r in fna.itertuples(index=False):
        k = (r.pair, r.direction, r.indicator, r.alpha)
        a = A.set_index(key).loc[[k]] if k in A.set_index(key).index else A.iloc[0:0]
        rows.append({"pair": r.pair, "transfer": r.direction, "indicator": r.indicator, "α": lim(r.alpha),
                     "frame unit: not appl.": f"{getattr(r, '_4')}/5",
                     "A: not appl.": f"{int((a.outcome == 'not applicable').sum())}/5",
                     "A: not det.": int((a.outcome == "not determined").sum()),
                     "A: appl.": int((a.outcome == "applicable").sum()),
                     "A: none sel.": int((a.outcome == "no threshold selected").sum()),
                     "B: not appl.": f"{int(count(B, 'not applicable').get(k, 0))}/5"})
    T1 = pd.DataFrame(rows)
    nA = int((T1["A: not appl."] != "0/5").sum()) if len(T1) else 0
    L += ["## 1. Not applicable outcomes of Fig. 4 under Method A", "",
          f"Fig. 4 (frame division, frame unit) holds {len(T1)} transfer cells (pair, direction, indicator, limit) with a not "
          f"applicable outcome on at least one split. Method A gives not applicable in {nA} of them.", "", table(T1), ""]

    # 2. applicable / not applicable outcomes of Method A on transfers, against the paper's sequence-unit rows
    S = tr(recorded("sequence"))
    dec = tr(A[A.outcome.isin(["applicable", "not applicable"])])
    g = dec.groupby(key + ["outcome"]).size().rename("A splits").reset_index()
    def paper_seq(r):
        q = S[(S.pair == r.pair) & (S.direction == r.direction) & (S.indicator == r.indicator) & (S.alpha == r.alpha)]
        return f"{int((q.outcome == r.outcome).sum())}/5"
    if len(g):
        g["paper sequence unit, same outcome"] = [paper_seq(r) for r in g.itertuples(index=False)]
        g["α"] = g.alpha.map(lim); g["A splits"] = g["A splits"].astype(str) + "/5"
        g = g[["pair", "direction", "indicator", "α", "outcome", "A splits", "paper sequence unit, same outcome"]]
    na_any = int((tr(A).outcome == "not applicable").sum()); ap_any = int((tr(A).outcome == "applicable").sum())
    L += ["## 2. Decided transfers under Method A", "",
          f"Over all transfers (4 pairs × 2 directions × 2 indicators × 5 limits × 5 splits = {len(tr(A))} outcomes), Method A gave "
          f"{ap_any} applicable and {na_any} not applicable outcomes. The last column counts the splits on which the paper's "
          f"sequence-unit analysis (loss = mean of a_f over the frames of a sequence, m7/m8) gave the same outcome."]
    if not len(g):
        L += ["", "**Method A decided no transfer:** every transfer outcome is not determined or no threshold selected."]
    L += ["", table(g) if len(g) else "", ""]
    sel = A.drop_duplicates(["pair", "established", "indicator", "alpha", "split"])
    s2 = sel.assign(selected=sel.tau_c.notna()).groupby(["pair", "established", "indicator", "alpha"]).selected.sum().reset_index()
    s2 = s2[s2.selected > 0].assign(α=lambda d: d.alpha.map(lim), splits=lambda d: d.selected.astype(int).astype(str) + "/5")
    L += ["Splits on which Method A selected a threshold (all other condition, indicator and limit combinations: none):", "",
          table(s2[["pair", "established", "indicator", "α", "splits"]]) if len(s2) else "none", ""]

    # 3. self-check
    own = O[O.own_condition]
    sc = own.groupby(["method", "outcome"]).size().unstack(fill_value=0)
    with_tau = own[own.tau_c.notna()].groupby("method").size()
    L += ["## 3. Self-check (threshold used in its own condition of selection)", "",
          "Counts over 4 pairs × 2 conditions × 2 indicators × 5 limits × 5 splits per method. With independent sequences, "
          "the frequency of not applicable among selected thresholds is bounded by δ + δ/2 = 0.075.", "",
          table(sc.reset_index()), ""]
    for m in sc.index:
        n = int(with_tau.get(m, 0)); k = int(sc.loc[m].get("not applicable", 0))
        L.append(f"- Method {m}: not applicable in {k} of {n} self-checks with a selected threshold"
                 + (f" ({k / n:.3f})." if n else "."))
    L.append("")

    # 4. AUROC
    au = AU.assign(**{"95 % interval": [f"[{a:.3f}, {b:.3f}]" for a, b in zip(AU.lo95, AU.hi95)]})
    au["point"] = au.point.map(lambda v: f"{v:.3f}")
    au["sequences"] = au.sequences.map(lambda v: "" if v != v or v == "" else str(int(float(v))))
    L += ["## 4. AUROC of Fig. 5 with a sequence bootstrap", "",
          f"Evaluation part of split 0 (frame division, as in Fig. 5), {int(AU.replicates.iloc[0])} replicates, seed {int(AU.seed.iloc[0])}, "
          "percentile interval. Near/far: drives resampled once for both conditions; clear/rain and the two datasets: "
          "sequences resampled within each condition.", "",
          table(au[["pair", "indicator", "quantity", "point", "95 % interval", "sequences", "resampling"]]), ""]

    # 5. epochs
    ep = (out / "epoch_check.txt").read_text().splitlines()
    cfg = sorted(set(re.findall(r"NUM_EPOCHS:\s*(\d+)", "\n".join(ep))))
    stored = [l for l in ep if l.startswith("seed ") and "epoch=" in l]
    last = [l.strip() for l in ep if re.search(r"Train: *\d+/\d+", l)]
    ck = [l.split()[-1] for l in ep if l.rstrip().endswith(".pth") and "/" not in l.split()[-1]]
    inf = sorted({l.strip() for l in ep if l.strip().endswith("latest_model.pth") and l.strip().startswith("/")})
    L += ["## 5. Training epochs of the nuScenes members (item C, nothing changed)", "",
          f"- Configurations `runtime-monitoring/configs/cbgs_pp_multihead_nuscenes_seed{{1..5}}.yaml`: NUM_EPOCHS = {', '.join(cfg)}.",
          f"- Training logs `runtime-monitoring/training_seed{{1..4}}_nuscenes.log`, last epoch markers: {'; '.join(last)}.",
          f"- Checkpoint files per member (`third_party/OpenPCDet/output/workspace/configs/cbgs_pp_multihead_nuscenes_seed<s>/seed_<s>/ckpt/`): "
          f"{', '.join(sorted(set(ck)))}.",
          f"- Inference logs `runtime-monitoring/logs/nuscenes_inference_seed<s>.log` load: {'; '.join(inf)}.",
          f"- Epoch stored in the checkpoints: {'; '.join(stored)}.", ""]
    its = {l.split()[1]: (l.split()[2], int(re.search(r"it=(\d+)", l).group(1)), int(re.search(r"epoch=(\d+)", l).group(1))) for l in stored}
    ends = [int(re.search(r"it=(\d+)", l).group(1)) for l in stored if "checkpoint_epoch_10" in l]
    if ends and len(set(ends)) == 1:
        per = ends[0] / 10
        lat = [int(re.search(r"it=(\d+)", l).group(1)) for l in stored if "latest_model" in l]
        L += [f"Reading: checkpoint_epoch_10 holds iteration {ends[0]} = 10 epochs of {per:.0f} iterations; the latest_model.pth files "
              f"that inference loaded hold iterations {min(lat)} to {max(lat)}, i.e. {min(lat) / per:.4f} to {max(lat) / per:.4f} epochs, "
              f"{ends[0] - max(lat)} to {ends[0] - min(lat)} iterations before the end of epoch 10. Training was configured for 20 epochs "
              f"and the logs end at the start of epoch 11, so the members were trained for (just under) 10 epochs, not 20.", ""]
    L += [
          "Full listing: `epoch_check.txt`.", ""]

    # 6. N_s
    n0 = NS[NS.split == 0][["pair", "condition", "sequences", "N_s_min", "N_s_median", "N_s_max"]]
    rng = NS.groupby(["pair", "condition"]).N_s_max.agg(["min", "max"]).reset_index()
    n0 = n0.merge(rng, on=["pair", "condition"]).rename(columns={"min": "N_max over splits, min", "max": "N_max over splits, max"})
    L += ["## 6. Frames per sequence N_s (sequences with N_s ≥ 1, all parts, split 0)", "",
          "N_max(c) is the largest N_s over all validation sequences of c; for distance it depends on the boundary of each split.", "",
          table(n0), ""]
    (out / "REPORT.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

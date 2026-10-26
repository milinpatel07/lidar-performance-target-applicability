#!/usr/bin/env python3
"""m7_scene_split_report.py (m7-1.0) - split by recorded nuScenes scene: reproduction gate and comparison table.

The scene split reruns m3 (nuScenes distance) and m6 part C (rain) with the parts drawn by recorded scene
(`--split scene`). Before that, the same scripts are run with `--split frame` into <run>/m3_frame and
<run>/m6_frame, and must reproduce the recorded results.

  gate     <run>/m3_frame and <run>/m6_frame must equal results/m3_range_nuscenes and
           results/m6_protocol_seeds_weather in every row and column, with equal input hashes;
           writes <run>/REPRO_PASSED.txt, or <run>/REPRO_FAILED.txt and exits 1
  collect  after the scene runs (<run>/m3_scene, <run>/m6_scene): writes <run>/m7_scene_split.csv (one row per
           cell, split and variant) and <run>/m7_scene_split_summary.txt (outcome codes per cell over the splits)

Variants: frame = the recorded frame split; scene_frame_unit = (i) scenes permuted with the original split function
and fractions, every frame takes its scene's part, the frame stays the unit of the selection test and of the HB
interval; scene_scene_unit = (ii) the same partition with the scene as the unit, the loss of a scene being the mean
of the per-frame false acceptance proportions a_f (Eq. 1) over its frames in the condition, 0 if nothing is accepted.
Distance = m3 primary variant (IoU 0.5, car, median cut).

Usage: python3 m7_scene_split_report.py gate|collect --run <folder> [--recorded <results folder>]
"""
import argparse, csv, json, sys
from collections import Counter, defaultdict
from pathlib import Path

VERSION = "m7-1.0 (2026-10-19)"
CODE = {"applies": "A", "does not apply": "N", "not determined": "?", "no threshold established": "-"}
SEEDS = range(5)


def fmt_r(v):
    return "  -" if v in ("", "None") else f"{float(v):.2f}"


def rows(p):
    return list(csv.DictReader(open(p)))


def same_rows(new, ref, name):
    """Every recorded column of every recorded row equal (as written), rows in the same order."""
    if len(new) != len(ref):
        return [f"{name}: {len(new)} rows, recorded {len(ref)}"]
    bad = [f"{name} row {i}: {[(k, n.get(k), v) for k, v in r.items() if n.get(k) != v][:3]}"
           for i, (n, r) in enumerate(zip(new, ref)) if any(n.get(k) != v for k, v in r.items())]
    return bad[:10] + ([f"{name}: {len(bad)} rows differ"] if bad else [])


def gate(run, rec):
    out = same_rows(rows(run / "m3_frame/matrix_all_variants.csv"), rows(rec / "m3_range_nuscenes/matrix_all_variants.csv"), "m3")
    for f in ("A_kitti_range_protocol.csv", "B_shift_seeds_protocol.csv", "C_weather_nuscenes.csv"):
        out += same_rows(rows(run / "m6_frame" / f), rows(rec / "m6_protocol_seeds_weather" / f), "m6 " + f)
    for new, ref in ((run / "m3_frame/provenance.json", rec / "m3_range_nuscenes/provenance.json"),
                     (run / "m6_frame/provenance.json", rec / "m6_protocol_seeds_weather/provenance.json")):
        if json.load(open(new))["inputs_sha256"] != json.load(open(ref))["inputs_sha256"]:
            out.append(f"input hashes differ: {new.parent.name}")
    n = {k: len(rows(p)) for k, p in (("m3", run / "m3_frame/matrix_all_variants.csv"), ("m6 C", run / "m6_frame/C_weather_nuscenes.csv"))}
    msg = f"REPRODUCTION frame split: m3 {n['m3']} rows, m6 A/B/C all rows, input hashes: " + ("EQUAL" if not out else "DIFFER")
    print(msg)
    if out:
        (run / "REPRO_FAILED.txt").write_text(msg + "\n" + "\n".join(out) + "\n"); print("\n".join(out)); sys.exit(1)
    (run / "REPRO_PASSED.txt").write_text(msg + "\n")


def table(run):
    """Rows of m7_scene_split.csv: distance = m3 primary variant (A_iou0.5, car, median cut); rain = m6 part C."""
    out = []
    prim = lambda r: r["iou"] == "A_iou0.5" and r["objects"] == "car" and r["cut_q"] == "0.5"
    for src, variant_of in ((run / "m3_frame", lambda r: "frame"), (run / "m3_scene", lambda r: "scene_" + r["hb_unit"] + "_unit")):
        for r in rows(src / "matrix_all_variants.csv"):
            if prim(r):
                out.append({"setting": "distance", "variant": variant_of(r), "indicator": r["indicator"], "seed": r["seed"],
                            "alpha": r["alpha"], "established": r["established"], "applied": r["applied"], "outcome": r["outcome"],
                            "tau": r["tau"], "A_hat": r["A_hat"], "hb_L": r["hb_L"], "hb_U": r["hb_U"], "R_hat": r["R_hat"],
                            "n_select_units": r.get("n_select_units", ""), "n_eval_units": r["n_eval_frames"], "cut_m": r["cut_m"]})
    for src, variant_of in ((run / "m6_frame", lambda r: "frame"), (run / "m6_scene", lambda r: "scene_" + r["hb_unit"] + "_unit")):
        for r in rows(src / "C_weather_nuscenes.csv"):
            out.append({"setting": "rain", "variant": variant_of(r), "indicator": r["indicator"], "seed": r["seed"],
                        "alpha": r["alpha"], "established": r["established"], "applied": r["applied"], "outcome": r["outcome"],
                        "tau": r.get("tau", ""), "A_hat": r.get("A_hat", ""), "hb_L": r.get("hb_L", ""), "hb_U": r.get("hb_U", ""),
                        "R_hat": r.get("R_hat", ""), "n_select_units": r["frames_select"], "n_eval_units": r["frames_eval"], "cut_m": ""})
    return out


def collect(run):
    allr = table(run)
    with open(run / "m7_scene_split.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allr[0])); w.writeheader(); w.writerows(allr)
    d = defaultdict(dict)
    for r in allr:
        d[(r["setting"], r["indicator"], float(r["alpha"]), r["established"], r["applied"])].setdefault(r["variant"], {})[int(r["seed"])] = r
    V = (("frame", "frame"), ("scene_frame_unit", "(i)"), ("scene_scene_unit", "(ii)"))
    order = {"distance": 0, "rain": 1}
    L = [f"Split by recorded scene ({VERSION})", (run / "REPRO_PASSED.txt").read_text().strip(), "",
         "Codes per split 0-4: A applicable, N not applicable, ? not determined, - no threshold; counts in brackets.",
         "R(ii): retention per split under variant (ii), on the evaluation part of the applied condition.", ""]
    for k in sorted(d, key=lambda k: (order[k[0]], k[1], -k[2], k[3], k[4])):
        parts = []
        for v, lab in V:
            codes = "".join(CODE[d[k][v][s]["outcome"]] for s in SEEDS)
            cnt = Counter(codes)
            parts.append(f"{lab} {codes} [" + " ".join(f"{c}{cnt[c]}" for c in "AN?-" if cnt[c]) + "]")
        rr = " ".join(fmt_r(d[k]["scene_scene_unit"][s]["R_hat"]) for s in SEEDS)
        L.append(f"{k[0]:8s} {k[1]} {k[2]:<6g} {k[3]:>5s}->{k[4]:5s}  " + "  ".join(parts) + f"  R(ii) {rr}")
    tot = {v: Counter(d[k][v][s]["outcome"] for k in d for s in SEEDS) for v, _ in V}
    L += ["", "Totals over " + str(len(d) * 5) + " split-cells: " + "; ".join(
        f"{lab}: " + ", ".join(f"{o} {n}" for o, n in sorted(tot[v].items())) for v, lab in V) + "."]
    p3 = json.load(open(run / "m3_scene/provenance.json"))["scene_counts_primary"]
    p6 = json.load(open(run / "m6_scene/provenance.json"))["C"]["parts"]
    L += ["", "Scenes (frames with a car detection) per condition and part. Distance: a scene counts for near or far if it holds",
          "a car detection in that condition (most scenes count for both).", "",
          "split | grid / sel / eval scenes | cut | near sel / eval | far sel / eval | clear sel / eval | rain sel / eval"]
    for s in SEEDS:
        a, b = p3[f"seed{s}"], p6[f"seed{s}"]
        f6 = lambda c, p: f"{b[p][c]['scenes']} ({b[p][c]['frames_with_car']})"
        L.append(f"{s} | {a['grid']['scenes']} / {a['select']['scenes']} / {a['eval']['scenes']} | {a['cut_m']:.3f} m | "
                 f"{a['select']['near']} / {a['eval']['near']} | {a['select']['far']} / {a['eval']['far']} | "
                 f"{f6('clear', 'select')} / {f6('clear', 'eval')} | {f6('rain', 'select')} / {f6('rain', 'eval')}")
    (run / "m7_scene_split_summary.txt").write_bytes(("\n".join(L) + "\n").encode())
    print("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=VERSION)
    ap.add_argument("cmd", choices=["gate", "collect"])
    ap.add_argument("--run", required=True, help="folder holding m3_frame, m6_frame, m3_scene, m6_scene")
    ap.add_argument("--recorded", default=str(Path(__file__).resolve().parents[1] / "results"))
    a = ap.parse_args()
    gate(Path(a.run), Path(a.recorded)) if a.cmd == "gate" else collect(Path(a.run))

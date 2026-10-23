#!/usr/bin/env python3
"""Check interactive/stats.js against analysis/m1_range_kitti.py and against the recorded sequence-unit rows.

    python3 tools/test_stats_js.py            # from the repository root; exit 0 on success, 1 on a difference
    pytest tools/test_stats_js.py             # the same as a pytest test

1. 300 seeded random cases (S, n, alpha, delta): hb_pvalue, hb_upper, hb_lower agree to 1e-9; n_required agrees
   exactly on the cases with alpha >= 1e-3.
2. Every recorded row of the sequence-level evaluation with an interval, in results/m7_scene_split/m7_scene_split.csv
   (variant scene_scene_unit) and results/m8_kitti_drive_split/*.csv (hb_unit == 'drive'): hb_L and hb_U are
   recomputed by stats.js from A_hat * n_eval_units and n_eval_units at delta/2 = 0.025 and agree to 1e-6, and the
   outcome rule gives the recorded outcome.

Needs node; without it the check is skipped with a message (exit 0). No network access.
"""
import argparse
import csv
import importlib.util
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOL_PY, TOL_REC = 1e-9, 1e-6
DELTA = 0.05
OUTCOME = {"applies": "applicable", "does not apply": "not applicable", "not determined": "not determined",
           "applicable": "applicable", "not applicable": "not applicable"}

NODE_SCRIPT = r"""
const HB = require(process.argv[2]);
const inp = JSON.parse(require("fs").readFileSync(process.argv[3], "utf8"));
const out = {
  cases: inp.cases.map(c => ({
    p: HB.hbPvalue(c.S, c.n, c.alpha), U: HB.hbUpper(c.S, c.n, c.delta), L: HB.hbLower(c.S, c.n, c.delta),
    nreq: c.nreq ? HB.nRequired(c.alpha, c.delta) : null })),
  rows: inp.rows.map(r => { const S = r.A_hat * r.n, U = HB.hbUpper(S, r.n, r.d), L = HB.hbLower(S, r.n, r.d);
    return { L, U, outcome: HB.outcome(L, U, r.alpha) }; })
};
process.stdout.write(JSON.stringify(out));
"""


def load_m1(root):
    spec = importlib.util.spec_from_file_location("m1_range_kitti", root / "analysis" / "m1_range_kitti.py")
    m1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m1)
    return m1


def random_cases(seed=20261023, count=300):
    rng = random.Random(seed)
    cases = []
    for i in range(count):
        n = int(round(10 ** rng.uniform(0, math.log10(2000))))
        kind = i % 3
        if kind == 0:
            S = 0.0
        elif kind == 1:
            S = float(rng.randint(0, n))
        else:
            S = rng.uniform(0, n) * rng.choice([1.0, 0.1, 0.01])
        alpha = 10 ** rng.uniform(-4, math.log10(0.5))
        delta = rng.uniform(0.005, 0.2)
        cases.append({"S": S, "n": n, "alpha": alpha, "delta": delta, "nreq": alpha >= 1e-3})
    return cases


def recorded_rows(root):
    rows = []
    sources = [(root / "results/m7_scene_split/m7_scene_split.csv", lambda r: r["variant"] == "scene_scene_unit")]
    sources += [(p, lambda r: r["hb_unit"] == "drive") for p in sorted((root / "results/m8_kitti_drive_split").glob("*.csv"))]
    for path, keep in sources:
        with open(path, newline="", encoding="utf-8") as fh:
            for line, r in enumerate(csv.DictReader(fh), start=2):
                if not keep(r) or "" in (r["A_hat"], r["n_eval_units"], r["hb_L"], r["hb_U"]):
                    continue
                rows.append({"file": path.relative_to(root).as_posix(), "line": line, "A_hat": float(r["A_hat"]),
                             "n": int(float(r["n_eval_units"])), "d": DELTA / 2, "alpha": float(r["alpha"]),
                             "L_rec": float(r["hb_L"]), "U_rec": float(r["hb_U"]), "outcome_rec": OUTCOME[r["outcome"]]})
    return rows


def run(root, stats_js):
    node = shutil.which("node")
    if node is None:
        print("SKIPPED: node is not installed; stats.js was not checked.")
        return 0
    m1 = load_m1(root)
    cases, rows = random_cases(), recorded_rows(root)
    with tempfile.TemporaryDirectory() as tmp:
        js, data = Path(tmp) / "run.js", Path(tmp) / "in.json"
        js.write_text(NODE_SCRIPT, encoding="utf-8")
        data.write_text(json.dumps({"cases": cases, "rows": rows}), encoding="utf-8")
        res = subprocess.run([node, str(js), str(stats_js.resolve()), str(data)], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)
    bad = 0
    worst = 0.0
    for c, o in zip(cases, out["cases"]):
        ref = {"p": m1.hb_pvalue(c["S"], c["n"], c["alpha"]), "U": m1.hb_upper(c["S"], c["n"], c["delta"]),
               "L": m1.hb_lower(c["S"], c["n"], c["delta"])}
        for k, v in ref.items():
            d = abs(v - o[k])
            worst = max(worst, d)
            if d > TOL_PY:
                bad += 1
                print(f"DIFF {k}: S={c['S']} n={c['n']} alpha={c['alpha']} delta={c['delta']}: python {v} js {o[k]}")
        if c["nreq"] and m1.n_required(c["alpha"], c["delta"]) != o["nreq"]:
            bad += 1
            print(f"DIFF n_required: alpha={c['alpha']} delta={c['delta']}: python "
                  f"{m1.n_required(c['alpha'], c['delta'])} js {o['nreq']}")
    print(f"random cases: {len(cases)}, largest absolute difference {worst:.3g} (tolerance {TOL_PY:g}), "
          f"n_required compared on {sum(c['nreq'] for c in cases)}")
    worst = 0.0
    for r, o in zip(rows, out["rows"]):
        d = max(abs(o["L"] - r["L_rec"]), abs(o["U"] - r["U_rec"]))
        worst = max(worst, d)
        if d > TOL_REC or o["outcome"] != r["outcome_rec"]:
            bad += 1
            print(f"DIFF {r['file']} line {r['line']}: recorded L={r['L_rec']} U={r['U_rec']} {r['outcome_rec']}; "
                  f"stats.js L={o['L']} U={o['U']} {o['outcome']}")
    files = sorted({r["file"] for r in rows})
    print(f"recorded sequence-unit rows: {len(rows)} from {', '.join(files)}, largest absolute difference "
          f"{worst:.3g} (tolerance {TOL_REC:g})")
    if not rows:
        print("DIFF: no recorded rows found")
        bad += 1
    print("FAILED" if bad else "PASSED")
    return 1 if bad else 0


def test_stats_js():
    assert run(ROOT, ROOT / "interactive" / "stats.js") == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root with analysis/ and results/")
    ap.add_argument("--stats-js", type=Path, default=None, help="default: <root>/interactive/stats.js")
    a = ap.parse_args()
    sys.exit(run(a.root.resolve(), a.stats_js or a.root / "interactive" / "stats.js"))

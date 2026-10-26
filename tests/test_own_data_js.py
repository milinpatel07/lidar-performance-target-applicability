#!/usr/bin/env python3
"""Check site/interactive/apptest.js (the computation of site/interactive/own-data.html) against Python.

    python3 tests/test_own_data_js.py         # from the repository root; exit 0 on success, 1 on a difference
    pytest tests/test_own_data_js.py

Two tables of detections are used: the synthetic example of apptest.js (seed 1, divided by frame, selection share
0.5, seed 7) and a table generated here with numpy (ties in u, division by sequence). For every ordered pair of
conditions, both units (frame, recorded sequence) and alpha in {0.1, 0.05, 0.01} at delta = 0.05, the JS results
(candidates, per-candidate p-values, selected threshold, A_hat, L, U, retention, n, outcome, own-condition check)
are compared with
  1. an independent Python implementation written here from Sect. 3 of the paper, using hb_pvalue, hb_upper and
     hb_lower of case_study/experiments/m1_range_kitti.py (and, for the frame unit, its class Cell and chain_index);
  2. the package in package/src/applicability_test (applicability_test), if it is present.
Needs node; without it the check is skipped with a message (exit 0). No network access.
"""
import argparse
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ALPHAS, DELTA, UNITS = (0.1, 0.05, 0.01), 0.05, ("frame", "sequence")
TOL = 1e-9
LEVELS = [round(0.01 * i, 2) for i in range(1, 101)]

NODE_SCRIPT = r"""
const A = require(process.argv[2]);
const fs = require("fs");
const job = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const out = {};
if (job.writeSynthetic) {
  const rows = A.divide(A.synthetic(1), "frame", 0.5, 7);
  fs.writeFileSync(job.writeSynthetic, A.toCSV(rows, true));
}
for (const t of job.tables) {
  const parsed = A.parseCSV(fs.readFileSync(t.path, "utf8"));
  if (parsed.errors.length) throw new Error(parsed.errors.join("; "));
  const res = [];
  for (const unit of job.units) for (const alpha of job.alphas) {
    const r = A.runAll(parsed.rows, { unit, alpha, delta: job.delta });
    for (const p of r.pairs) res.push({ c: p.c, c2: p.c2, unit, alpha, candidates: p.selection.candidates,
      p: p.selection.pValues, tau: p.tau, outcome: p.outcome, nSel: p.nSelection, nTest: p.nTest,
      test: p.test, own: p.ownCheck });
  }
  out[t.name] = res;
}
process.stdout.write(JSON.stringify(out, (k, v) => (typeof v === "number" && !Number.isFinite(v)) ? null : v));
"""


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def numpy_table(path, seed=20261023):
    """A table with three conditions, ties in u (two decimals) and a division by sequence."""
    rng = np.random.default_rng(seed)
    rows = []
    seqs = [f"q{s:02d}" for s in range(36)]
    sel = set(rng.choice(seqs, size=18, replace=False))
    for s_i, s in enumerate(seqs):
        cond = ("a", "b", "c")[s_i % 3]
        for f in range(int(rng.integers(5, 30))):
            for _ in range(int(rng.integers(1, 9))):
                wrong = rng.random() < (0.25, 0.4, 0.25)[s_i % 3]
                u = (0.5 if wrong else 0.3) + (0.05 if cond == "c" else 0.0) + 0.12 * rng.standard_normal()
                rows.append((f"{s}-{f}", s, cond, "selection" if s in sel else "test", round(float(u), 2),
                             0 if wrong else 1))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "sequence", "condition", "part", "u", "correct"])
        w.writerows(rows)


def read_table(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["u"], r["correct"] = float(r["u"]), int(r["correct"])
    return rows


class Reference:
    """Independent implementation of the test (Sect. 3 of the paper) on plain Python lists."""

    def __init__(self, m1):
        self.m1 = m1

    @staticmethod
    def unit_values(dets, unit, tau):
        frames = {}
        for d in dets:
            key = (d["sequence"], d["frame"]) if unit == "sequence" else d["frame"]
            na, nw = frames.get(key, (0, 0))
            if d["u"] <= tau:
                na += 1
                nw += 1 - d["correct"]
            frames[key] = (na, nw)
        a = {k: (nw / na if na else 0.0) for k, (na, nw) in frames.items()}
        if unit == "frame":
            return [a[k] for k in sorted(a)]
        per = {}
        for (s, _), v in a.items():
            per.setdefault(s, []).append(v)
        return [sum(v) / len(v) for _, v in sorted(per.items())]

    def run(self, rows, c, c2, unit, alpha, delta):
        m1 = self.m1
        both = {c, c2}
        pool = [r["u"] for r in rows if r["condition"] in both and r["part"] == "grid"] or \
               [r["u"] for r in rows if r["condition"] in both and r["part"] == "selection"]
        cand = [float(v) for v in np.unique(np.quantile(np.asarray(pool), LEVELS))]
        sel = [r for r in rows if r["condition"] == c and r["part"] == "selection"]
        use = [r for r in rows if r["condition"] == c2 and r["part"] == "test"]
        own = [r for r in rows if r["condition"] == c and r["part"] == "test"]
        p = []
        for t in cand:
            v = self.unit_values(sel, unit, t)
            p.append(m1.hb_pvalue(sum(v), len(v), alpha))
        j = m1.chain_index([p], delta)
        out = {"candidates": cand, "p": p, "tau": cand[j] if j >= 0 else None,
               "nSel": len(self.unit_values(sel, unit, 0.0)), "nTest": len(self.unit_values(use, unit, 0.0))}
        if unit == "frame" and sel:   # the same selection with the class Cell of m1
            cell = m1.Cell(np.array([r["frame"] for r in sel]), np.array([r["u"] for r in sel]),
                           np.array([r["correct"] for r in sel]))
            p_cell = [m1.hb_pvalue(cell.a_f(t).sum(), cell.m, alpha) for t in cand]
            j_cell = m1.chain_index([p_cell], delta)
            out["tau_cell"] = cand[j_cell] if j_cell >= 0 else None

        def test(dets):
            v = self.unit_values(dets, unit, out["tau"])
            S, n = sum(v), len(v)
            L, U = m1.hb_lower(S, n, delta / 2), m1.hb_upper(S, n, delta / 2)
            corr = [d for d in dets if d["correct"] == 1]
            ret = sum(1 for d in corr if d["u"] <= out["tau"]) / len(corr) if corr else None
            oc = "applicable" if U <= alpha else ("not applicable" if L > alpha else "not determined")
            return {"A_hat": S / n if n else None, "L": L, "U": U, "n": n, "retention": ret, "outcome": oc}

        if out["tau"] is None:
            out["outcome"], out["test"], out["own"] = "no threshold selected", None, None
        else:
            out["test"] = test(use)
            out["own"] = test(own)
            out["outcome"] = out["test"]["outcome"]
        return out


def close(a, b, tol=TOL):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


def compare(js, ref, pkg, label):
    errs = []
    if js["candidates"] != ref["candidates"]:
        if len(js["candidates"]) != len(ref["candidates"]) or \
                max(abs(x - y) for x, y in zip(js["candidates"], ref["candidates"])) > 1e-12:
            errs.append("candidates differ")
    if len(js["p"]) != len(ref["p"]) or any(abs(x - y) > TOL for x, y in zip(js["p"], ref["p"])):
        errs.append("p-values differ")
    for k in ("tau", "nSel", "nTest", "outcome"):
        if js[k] != ref[k] and not (isinstance(js[k], float) and close(js[k], ref[k], 1e-12)):
            errs.append(f"{k}: js {js[k]} python {ref[k]}")
    if "tau_cell" in ref and not close(ref["tau_cell"], ref["tau"], 0):
        errs.append(f"m1.Cell gives tau {ref['tau_cell']}, list reference {ref['tau']}")
    for part in ("test", "own"):
        a, b = js[part], ref[part]
        if ref["tau"] is None:   # no threshold selected: nothing is tested in either condition
            if a is not None and a.get("outcome") != "no threshold selected":
                errs.append(f"{part}: js reports {a.get('outcome')} without a selected threshold")
            continue
        if (a is None) != (b is None):
            if not (part == "own" and js["c"] == js["c2"]):
                errs.append(f"{part}: presence differs")
            continue
        if a is None:
            continue
        for k in ("A_hat", "L", "U", "retention"):
            if not close(a[k], b[k]):
                errs.append(f"{part}.{k}: js {a[k]} python {b[k]}")
        if a["n"] != b["n"] or a["outcome"] != b["outcome"]:
            errs.append(f"{part}: n or outcome differ (js {a['n']} {a['outcome']}, python {b['n']} {b['outcome']})")
    if pkg is not None:
        if not close(pkg.tau, js["tau"], 1e-12) or pkg.outcome != js["outcome"] or pkg.n_selection != js["nSel"] \
                or pkg.n_test != js["nTest"]:
            errs.append(f"package: tau {pkg.tau} outcome {pkg.outcome} n {pkg.n_selection}/{pkg.n_test}")
        elif js["test"] is not None:
            for k, v in (("L", pkg.L), ("U", pkg.U), ("A_hat", pkg.A_hat), ("retention", pkg.retention)):
                if not close(v, js["test"][k]):
                    errs.append(f"package {k}: {v} js {js['test'][k]}")
    return [f"{label}: {e}" for e in errs]


def run(root, apptest_js):
    node = shutil.which("node")
    if node is None:
        print("SKIPPED: node is not installed; apptest.js was not checked.")
        return 0
    m1 = load(root / "case_study" / "experiments" / "m1_range_kitti.py", "m1_range_kitti")
    pkg_src = root / "package" / "src"
    package = None
    if (pkg_src / "applicability_test" / "core.py").exists():
        sys.path.insert(0, str(pkg_src))
        import applicability_test as package
    else:
        print("package/src/applicability_test not found: comparing with the Python reference only")
    ref = Reference(m1)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        synth, own = tmp / "synthetic.csv", tmp / "numpy_table.csv"
        numpy_table(own)
        job = {"writeSynthetic": str(synth), "units": list(UNITS), "alphas": list(ALPHAS), "delta": DELTA,
               "tables": [{"name": "synthetic", "path": str(synth)}, {"name": "numpy", "path": str(own)}]}
        (tmp / "job.json").write_text(json.dumps(job), encoding="utf-8")
        (tmp / "run.js").write_text(NODE_SCRIPT, encoding="utf-8")
        # the synthetic table is written by the first node call, so run node once and read both tables afterwards
        res = subprocess.run([node, str(tmp / "run.js"), str(apptest_js.resolve()), str(tmp / "job.json")],
                             capture_output=True, text=True)
        if res.returncode:
            print(res.stderr)
            return 1
        out = json.loads(res.stdout)
        tables = {"synthetic": read_table(synth), "numpy": read_table(own)}
    errs, counts, n = [], {}, 0
    for name, results in out.items():
        rows = tables[name]
        for js in results:
            label = f"{name} {js['unit']} alpha={js['alpha']} {js['c']}->{js['c2']}"
            r = ref.run(rows, js["c"], js["c2"], js["unit"], js["alpha"], DELTA)
            pk = None
            if package is not None:
                cols = lambda part, cond: {k: [x[k] for x in rows if x["condition"] == cond and x["part"] == part]
                                           for k in ("frame", "sequence", "u", "correct")}
                pk = package.applicability_test(cols("selection", js["c"]), cols("test", js["c2"]), r["candidates"],
                                                js["alpha"], DELTA, unit=js["unit"])
            errs += compare(js, r, pk, label)
            counts[js["outcome"]] = counts.get(js["outcome"], 0) + 1
            n += 1
    for e in errs[:40]:
        print("DIFF", e)
    print(f"compared {n} results ({', '.join(f'{k}: {v}' for k, v in sorted(counts.items()))}) with the Python "
          f"reference{' and the package' if package is not None else ''}")
    print("FAILED" if errs else "PASSED")
    return 1 if errs else 0


def test_own_data_js():
    assert run(ROOT, ROOT / "site" / "interactive" / "apptest.js") == 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root with case_study/experiments/ (and package/)")
    ap.add_argument("--apptest-js", type=Path, default=None, help="default: <root>/interactive/apptest.js")
    a = ap.parse_args()
    sys.exit(run(a.root.resolve(), a.apptest_js or a.root / "site" / "interactive" / "apptest.js"))

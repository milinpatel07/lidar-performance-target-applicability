"""Command line: python -m applicability_test detections.csv --selection-condition near --use-condition far --alpha 0.01"""
import argparse
import csv
import json
import math
import sys
from dataclasses import asdict

import numpy as np

from .core import applicability_test, quantile_candidates

DESCRIPTION = """Applicability test of the performance target FAP <= alpha.

The CSV holds one row per detection with the columns
  frame       frame id
  sequence    recorded sequence id (needed only for --unit sequence)
  condition   condition of the detection, for example near or far
  part        grid, selection or test (grid is needed only for --candidates quantiles)
  u           indicator value; a detection is accepted if u <= tau
  correct     1 for a correct, 0 for a wrong detection
The threshold is selected on the selection rows of the condition of selection and
tested on the test rows of the condition of use."""


def _values(text):
    """'0.1,0.2,0.3' or 'start:stop:step' (stop included)."""
    if ":" in text:
        a, b, s = (float(x) for x in text.split(":"))
        k = int(math.floor((b - a) / s + 1e-9))
        return [round(a + i * s, 12) for i in range(k + 1)]
    return [float(x) for x in text.split(",") if x.strip()]


def _read(path):
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except OSError as e:
        raise SystemExit(f"cannot read {path}: {e.strerror}")
    except UnicodeDecodeError:
        raise SystemExit(f"cannot read {path}: not a UTF-8 text file")
    if not rows:
        raise SystemExit(f"{path} holds no detections")
    need = {"frame", "condition", "part", "u", "correct"}
    missing = need - set(rows[0])
    if missing:
        raise SystemExit(f"missing columns: {', '.join(sorted(missing))}")
    return rows


def _number(row, column, kind=float):
    try:
        return kind(row[column])
    except (TypeError, ValueError):
        raise SystemExit(f"column {column}: {row[column]!r} is not a number (frame {row.get('frame')!r})")


def _select(rows, condition, part):
    r = [x for x in rows if x["condition"] == condition and x["part"] == part]
    if not r:   # a misspelt condition would otherwise give an empty part and a misleading outcome
        conditions = sorted({x["condition"] for x in rows})
        raise SystemExit(f"no rows with condition '{condition}' and part '{part}'; "
                         f"conditions in the file: {', '.join(conditions)}")
    data = {"frame": np.array([x["frame"] for x in r]),
            "u": np.array([_number(x, "u") for x in r]),
            "correct": np.array([_number(x, "correct", int) for x in r])}
    if r and "sequence" in r[0]:
        data["sequence"] = np.array([x["sequence"] for x in r])
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m applicability_test", description=DESCRIPTION,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="detections, one row per detection")
    ap.add_argument("--selection-condition", required=True, help="condition of selection c")
    ap.add_argument("--use-condition", required=True, help="condition of use c'")
    ap.add_argument("--alpha", type=float, required=True, help="limit of the FAP")
    ap.add_argument("--delta", type=float, default=0.05, help="error probability (default 0.05)")
    ap.add_argument("--candidates", choices=["quantiles", "values"], default="quantiles",
                    help="quantiles: quantiles of u at levels 0.01..1.00 over the grid rows of both conditions; "
                         "values: the list given by --values")
    ap.add_argument("--values", default="0.01:1.00:0.01",
                    help="candidate thresholds for --candidates values, as '0.1,0.2' or 'start:stop:step' "
                         "(default 0.01:1.00:0.01)")
    ap.add_argument("--unit", choices=["frame", "sequence"], default="frame",
                    help="frame-level or sequence-level evaluation (default frame)")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    args = ap.parse_args(argv)

    rows = _read(args.csv)
    if args.unit == "sequence" and "sequence" not in rows[0]:
        raise SystemExit("--unit sequence needs a 'sequence' column")
    if args.candidates == "quantiles":
        g = [_number(x, "u") for x in rows
             if x["part"] == "grid" and x["condition"] in (args.selection_condition, args.use_condition)]
        if not g:
            raise SystemExit("--candidates quantiles needs rows with part 'grid' in the two conditions")
        candidates = quantile_candidates(g)
    else:
        try:
            candidates = _values(args.values)
        except ValueError:
            raise SystemExit(f"--values: {args.values!r} is not a list of numbers or start:stop:step")

    try:
        res = applicability_test(_select(rows, args.selection_condition, "selection"),
                                 _select(rows, args.use_condition, "test"),
                                 candidates, args.alpha, args.delta, args.unit)
    except ValueError as e:
        raise SystemExit(str(e))
    if args.json:
        out = asdict(res)
        out["condition_of_selection"], out["condition_of_use"] = args.selection_condition, args.use_condition
        json.dump(out, sys.stdout, indent=1, default=float)
        print()
        return 0

    def f(x):
        return "-" if x is None else f"{x:.6g}"

    print(f"condition of selection: {args.selection_condition}   condition of use: {args.use_condition}")
    print(f"limit alpha: {args.alpha:g}   error probability delta: {args.delta:g}   "
          f"evaluation: {args.unit}-level   candidates: {len(res.selection.candidates)}")
    print(f"units: {res.n_selection} in the selection part, {res.n_test} in the test part")
    print(f"selected threshold tau: {f(res.tau)}")
    print(f"FAP estimate: {f(res.A_hat)}   interval [L, U]: [{f(res.L)}, {f(res.U)}]   retention: {f(res.retention)}")
    print(f"outcome: {res.outcome}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

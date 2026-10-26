#!/usr/bin/env python3
"""Check every number of the paper and rebuild its figures from the recorded results; no dataset is needed.

Run from case_study/ (Python 3.10 with environment/requirements.txt):

    python reproduce_paper.py              # checks, then Fig. 2 to 6 into work/figures/
    python reproduce_paper.py --no-latex   # the same without compiling the TikZ figures (no pdflatex needed)

1. Checks: every number of the paper against the recorded files (checks/check_paper_numbers.py --check-fresh, which
   also requires docs/paper_map.md to be up to date), every recorded result file at its path
   (checks/check_recorded_results.py) and every number of the supplementary material
   (tools/supplementary/make_supplementary.py --check).
2. Figures: Fig. 4 (outcomes and retention) and Fig. 5 (separation and FAP) are drawn from the recorded results; the
   schematics Fig. 2 and 3 and the curve of Fig. 6 are TikZ sources. Each is written to work/figures/ and, with
   pdflatex, compiled to PDF. Fig. 1 shows dataset images and needs the datasets (tools/figures/paper/README.md).

The tables of the paper are covered by the first check: docs/paper_map.md lists each of their numbers with its source.
Exit status 1 if a check or a figure fails.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_FIGS = HERE / "tools" / "figures" / "paper"
OUT = HERE / "work" / "figures"


def run(label, cmd, cwd=HERE):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1"))
    text = r.stdout if r.returncode == 0 else r.stdout + r.stderr   # pdflatex distributions also write notices to stderr
    last = ([x for x in text.splitlines() if x.strip()] or ["done"])[-1]
    print(f"{'ok  ' if r.returncode == 0 else 'FAIL'} {label}: {last[:150]}")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-latex", action="store_true", help="write the TikZ sources without compiling them")
    a = ap.parse_args()
    py = sys.executable
    ok = [run("numbers of the paper", [py, "checks/check_paper_numbers.py", "--check-fresh"]),
          run("recorded result files", [py, "checks/check_recorded_results.py"]),
          run("numbers of the supplementary material", [py, "tools/supplementary/make_supplementary.py", "--check"])]

    OUT.mkdir(parents=True, exist_ok=True)
    ok.append(run("Fig. 4 source", [py, str(PAPER_FIGS / "make_fig_outcomes.py"),
                                    "results/supporting_analyses/retention_applicable_cells.csv",
                                    str(OUT / "fig_outcomes.tex")]))
    ok.append(run("Fig. 5", [py, str(PAPER_FIGS / "make_fig_separation.py"),
                             "results/supporting_analyses/fig_separation_curves.csv", str(OUT / "fig_separation.pdf")]))
    for name in ("preamble.tex", "fig_concept.tex", "fig_parts.tex", "fig_units.tex"):
        shutil.copyfile(PAPER_FIGS / name, OUT / name)
    if a.no_latex:
        print("TikZ figures written to work/figures/ without compiling (--no-latex)")
    elif not shutil.which("pdflatex"):
        print("pdflatex not found: TikZ figures written to work/figures/ without compiling")
    else:
        for fig, name in (("Fig. 2", "fig_concept"), ("Fig. 3", "fig_parts"), ("Fig. 4", "fig_outcomes"),
                          ("Fig. 6", "fig_units")):
            ok.append(run(f"{fig} PDF", ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"],
                          cwd=OUT))
        for p in OUT.glob("*"):
            if p.suffix in (".aux", ".log"):
                p.unlink()
    print(f"{sum(ok)} of {len(ok)} steps passed; figures in {OUT.relative_to(HERE).as_posix()}/")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Edge cases, input validation, the command line on the shipped example, and the HB p-value against an
implementation written from its definition (exact binomial sums with math.comb, no shared code)."""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import applicability_test as at
from applicability_test.cli import main as cli_main
from applicability_test.core import _outcome

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "detections_example.csv"


def hb_pvalue_by_definition(S, n, alpha):
    """min(1, exp(-n h(r, alpha)), e P[Bin(n, alpha) <= ceil(S)]) for r = S/n < alpha, else 1."""
    r = S / n
    if r >= alpha:
        return 1.0
    h = (r * math.log(r / alpha) if r > 0 else 0.0) + (1 - r) * math.log((1 - r) / (1 - alpha))
    k = math.ceil(S)
    cdf = sum(math.comb(n, i) * alpha ** i * (1 - alpha) ** (n - i) for i in range(min(k, n) + 1))
    return min(1.0, math.exp(-n * h), math.e * cdf)


@pytest.mark.parametrize("S, n, alpha", [(0, 299, 0.01), (0, 368, 0.01), (1, 500, 0.01), (2.5, 400, 0.02),
                                         (7, 1000, 0.01), (0.3, 50, 0.1), (12, 300, 0.05), (0, 2995, 0.001),
                                         (3, 3000, 0.002), (40, 600, 0.1)])
def test_hb_pvalue_matches_definition(S, n, alpha):
    assert at.hb_pvalue(S, n, alpha) == pytest.approx(hb_pvalue_by_definition(S, n, alpha), rel=1e-9, abs=1e-15)


def test_hb_bounds_and_monotonicity():
    rng = np.random.default_rng(7)
    for _ in range(200):
        n = int(rng.integers(1, 800))
        S = float(rng.uniform(0, n))
        lo, hi = at.hb_lower(S, n, 0.025), at.hb_upper(S, n, 0.025)
        assert 0.0 <= lo <= S / n + 1e-12 and S / n - 1e-12 <= hi <= 1.0
        ps = [at.hb_pvalue(S, n, a) for a in np.linspace(0.01, 0.99, 25)]
        assert all(p1 >= p2 - 1e-12 for p1, p2 in zip(ps, ps[1:]))   # a larger limit is easier to show


def test_outcome_at_the_boundaries():
    assert _outcome(0.0, 0.01, 0.01) == at.APPLICABLE            # U == alpha
    assert _outcome(0.01, 0.02, 0.01) == at.NOT_DETERMINED       # L == alpha
    assert _outcome(0.011, 0.02, 0.01) == at.NOT_APPLICABLE


def test_detection_at_the_threshold_is_accepted():
    ids, a = at.per_unit_shares([0, 0], [0.5, 0.7], [0, 1], tau=0.5)
    assert a[0] == 1.0   # the wrong detection with u == tau is accepted, the correct one with u > tau is not


@pytest.mark.parametrize("alpha, delta", [(0.0, 0.05), (1.0, 0.05), (1.5, 0.05), (0.01, 0.0), (0.01, 1.0),
                                          (-0.1, 0.05)])
def test_limits_outside_the_unit_interval_are_rejected(alpha, delta):
    d = {"frame": [0, 1], "u": [0.1, 0.2], "correct": [1, 0]}
    with pytest.raises(ValueError):
        at.applicability_test(d, d, [0.5], alpha, delta)
    with pytest.raises(ValueError):
        at.test_threshold([0], [0.1], [1], 0.5, alpha, delta)


def test_empty_candidates_are_rejected():
    with pytest.raises(ValueError):
        at.select_threshold([0], [0.1], [1], [], 0.1, 0.05)


def test_empty_parts():
    empty = {"frame": [], "u": [], "correct": []}
    full = {"frame": np.arange(400), "u": np.full(400, 0.1), "correct": np.ones(400, int)}
    r = at.applicability_test(empty, full, [0.5], 0.1, 0.05)
    assert r.outcome == at.NO_THRESHOLD and r.n_selection == 0
    t = at.test_threshold([], [], [], 0.5, 0.1, 0.05)
    assert t.outcome == at.NOT_DETERMINED and (t.L, t.U, t.n) == (0.0, 1.0, 0)


def test_cli_on_the_shipped_example(capsys):
    assert cli_main([str(EXAMPLE), "--selection-condition", "clear", "--use-condition", "rain", "--alpha", "0.05"]) == 0
    assert "outcome: not applicable" in capsys.readouterr().out
    assert cli_main([str(EXAMPLE), "--selection-condition", "clear", "--use-condition", "clear", "--alpha", "0.05"]) == 0
    assert "outcome: applicable" in capsys.readouterr().out


def test_cli_reports_input_errors(tmp_path):
    with pytest.raises(SystemExit, match="conditions in the file: clear, rain"):
        cli_main([str(EXAMPLE), "--selection-condition", "clera", "--use-condition", "rain", "--alpha", "0.05"])
    with pytest.raises(SystemExit, match="cannot read"):
        cli_main([str(tmp_path / "missing.csv"), "--selection-condition", "a", "--use-condition", "b", "--alpha", "0.05"])
    with pytest.raises(SystemExit, match="alpha and delta"):
        cli_main([str(EXAMPLE), "--selection-condition", "clear", "--use-condition", "rain", "--alpha", "1.5"])


def test_cli_reports_bad_values(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("frame,condition,part,u,correct\n0,a,grid,0.1,1\n1,a,selection,abc,1\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="column u"):
        cli_main([str(bad), "--selection-condition", "a", "--use-condition", "a", "--alpha", "0.05"])
    with pytest.raises(SystemExit, match="--values"):
        cli_main([str(EXAMPLE), "--selection-condition", "clear", "--use-condition", "rain", "--alpha", "0.05",
                  "--candidates", "values", "--values", "a:b:c"])
    empty = tmp_path / "empty.csv"
    empty.write_text("frame,condition,part,u,correct\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="holds no detections"):
        cli_main([str(empty), "--selection-condition", "a", "--use-condition", "a", "--alpha", "0.05"])


def test_shipped_example_is_reproducible(tmp_path):
    """The script writes the shipped sample again; values compared to their 5 printed decimals, so that a change in the
    last bit of a NumPy random generator between versions does not fail the test."""
    out = tmp_path / "d.csv"
    script = EXAMPLE.parent / "synthetic_example.py"
    subprocess.run([sys.executable, str(script), "--csv", str(out)], check=True, capture_output=True)
    new, old = (p.read_text(encoding="utf-8").splitlines() for p in (out, EXAMPLE))
    assert len(new) == len(old) and new[0] == old[0]
    for a, b in zip(new[1:], old[1:]):
        fa, fb = a.split(","), b.split(",")
        assert fa[:3] == fb[:3] and fa[4:] == fb[4:] and abs(float(fa[3]) - float(fb[3])) <= 1e-5

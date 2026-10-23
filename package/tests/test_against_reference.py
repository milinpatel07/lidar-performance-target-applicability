"""Checks of the package against the reference implementation analysis/m1_range_kitti.py.

The reference is loaded by file path from ../analysis/m1_range_kitti.py relative to the
package folder, or from the path in the environment variable APPLICABILITY_TEST_M1.
Tests that need it are skipped if it is absent.
"""
import importlib.util
import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

import applicability_test as at
from applicability_test.cli import main as cli_main

M1_PATH = Path(os.environ.get("APPLICABILITY_TEST_M1",
                              Path(__file__).resolve().parents[2] / "analysis" / "m1_range_kitti.py"))


@pytest.fixture(scope="module")
def m1():
    if not M1_PATH.is_file():
        pytest.skip(f"reference implementation not found at {M1_PATH}")
    spec = importlib.util.spec_from_file_location("m1_range_kitti", M1_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# (a) statistics functions equal the reference on 500 seeded random cases
def test_stats_equal_reference(m1):
    rng = np.random.default_rng(2026)
    for _ in range(500):
        n = int(rng.integers(1, 1500))
        S = float(rng.uniform(0, 1) ** 3 * n)   # mostly small sums, as for small limits
        alpha = float(10 ** rng.uniform(-4, -0.5))
        delta = float(rng.choice([0.05, 0.025, 0.05 / 6, 0.1]))
        assert at.hb_pvalue(S, n, alpha) == m1.hb_pvalue(S, n, alpha)
        assert at.hb_upper(S, n, delta) == m1.hb_upper(S, n, delta)
        assert at.hb_lower(S, n, delta) == m1.hb_lower(S, n, delta)
        assert at.n_required(alpha, delta) == m1.n_required(alpha, delta)


_OUTCOME = {"applies": at.APPLICABLE, "does not apply": at.NOT_APPLICABLE,
            "not determined": at.NOT_DETERMINED, "no threshold established": at.NO_THRESHOLD}


# (b) selection and test equal m1.analyse on its synthetic data
@pytest.mark.parametrize("seed,range_effect", [(0, 0.0), (1, 0.15), (2, 0.3), (3, 0.0), (4, 0.3)])
def test_analyse_equal_reference(m1, seed, range_effect):
    alphas = [1e-3, 1e-2, 5e-2, 1e-1]
    cfg = dict(m1.CFG)
    delta = cfg["delta"]
    tab, y = m1._synthetic_table(3000, np.random.default_rng(100 + seed), range_effect)
    _, results, _ = m1.analyse(tab, y, ["Car"], 0.5, seed, cfg, alphas)

    dcode = m1.split_frames(tab["n_frames"], seed, cfg)[tab["fpos"]]
    g = dcode == 0
    cut = float(np.quantile(tab["rng"][g], 0.5))
    grid = at.quantile_candidates(tab["u"][g])
    assert np.array_equal(grid, np.unique(np.quantile(tab["u"][g], cfg["grid_levels"])))
    cid = (tab["rng"] > cut).astype(int)

    def part(code, c):
        m = (dcode == code) & (cid == c)
        return {"frame": tab["fpos"][m], "u": tab["u"][m], "correct": y[m]}

    outcomes = set()
    for res in results:
        alpha = res["alpha"]
        for cell in res["cells"]:
            c, c2 = m1.CLASS_NAMES.index(cell["established"]), m1.CLASS_NAMES.index(cell["applied"])
            sel_data = part(1, c)
            # p-values of the candidates equal those from the reference Cell
            ref_cell = m1.Cell(sel_data["frame"], sel_data["u"], sel_data["correct"])
            sel = at.select_threshold(sel_data["frame"], sel_data["u"], sel_data["correct"], grid, alpha, delta)
            assert sel.p_values == [m1.hb_pvalue(ref_cell.a_f(t).sum(), ref_cell.m, alpha) for t in grid]

            r = at.applicability_test(sel_data, part(2, c2), grid, alpha, delta)
            assert r.outcome == _OUTCOME[cell["outcome"]]
            assert r.tau == res["tau"][cell["established"]]
            outcomes.add(r.outcome)
            if r.tau is None:
                continue
            assert (r.tau, r.A_hat, r.L, r.U, r.retention, r.n_test) == (
                cell["tau"], cell["A_hat"], cell["hb_L"], cell["hb_U"], cell["R_hat"], cell["n_eval_frames"])
    assert len(outcomes) >= 2  # more than one kind of outcome compared


# (c) sequence-level evaluation: one value per sequence, the mean of a_f over its frames
def test_sequence_level_mean_of_frame_shares():
    rng = np.random.default_rng(5)
    k = 4000
    seq = rng.integers(0, 40, size=k)
    frame = rng.integers(0, 15, size=k)          # frame ids repeat across sequences
    u = rng.uniform(size=k)
    y = (rng.uniform(size=k) < 0.8).astype(int)
    for tau in (0.05, 0.3, 0.9):
        ids, vals = at.per_unit_shares(frame, u, y, tau, unit_ids=seq)
        for s, v in zip(ids, vals):
            m = seq == s
            _, a = at.per_unit_shares(frame[m], u[m], y[m], tau)
            assert v == pytest.approx(a.mean(), abs=1e-15)
        assert at.fap(frame, u, y, tau, unit_ids=seq) == pytest.approx(vals.mean())


def test_sequence_level_counts_sequences():
    data = {"frame": np.array([0, 1, 0, 1, 2]), "sequence": np.array(["a", "a", "b", "b", "b"]),
            "u": np.array([0.1, 0.1, 0.1, 0.1, 0.1]), "correct": np.array([0, 1, 1, 1, 0])}
    ids, vals = at.per_unit_shares(data["frame"], data["u"], data["correct"], 0.5, unit_ids=data["sequence"])
    assert list(ids) == ["a", "b"] and np.allclose(vals, [0.5, 1 / 3])
    r = at.applicability_test(data, data, [0.5], 0.5, 0.05, unit="sequence")
    assert r.n_selection == 2 and r.n_test == 2


# (d) edge cases
def test_frame_without_accepted_detection_contributes_zero():
    ids, a = at.per_unit_shares([0, 0, 1, 1], [0.9, 0.8, 0.1, 0.2], [0, 0, 0, 1], 0.5)
    assert list(ids) == [0, 1] and list(a) == [0.0, 0.5]
    assert at.fap([0, 0, 1, 1], [0.9, 0.8, 0.1, 0.2], [0, 0, 0, 1], 0.5) == 0.25


def test_lowest_candidate_fails_no_threshold_selected():
    # every detection wrong: every candidate that accepts anything fails
    n = 500
    data = {"frame": np.arange(n), "u": np.full(n, 0.1), "correct": np.zeros(n, dtype=int)}
    sel = at.select_threshold(data["frame"], data["u"], data["correct"], [0.2, 0.05], 0.01, 0.05)
    assert sel.candidates == [0.05, 0.2]   # sorted, the lowest first
    assert sel.p_values[0] <= 0.05 and sel.p_values[1] == 1.0 and sel.tau == 0.05
    sel = at.select_threshold(data["frame"], data["u"], data["correct"], [0.2, 0.3], 0.01, 0.05)
    assert sel.tau is None and sel.index == -1
    r = at.applicability_test(data, data, [0.2, 0.3], 0.01, 0.05)
    assert r.outcome == at.NO_THRESHOLD and r.L is None and r.U is None and r.n_test == n


def test_selection_stops_at_first_failure():
    # frames 0..49: one wrong detection at u = 0.15 and 99 correct ones at u = 0.25;
    # frames 50..999: one correct detection at u = 0.05. The FAP is 0 at 0.1, 0.05 at 0.2
    # and 0.0005 at 0.3, so 0.2 fails and 0.3 passes again but is not selected.
    f = np.concatenate([np.repeat(np.arange(50), 100), np.arange(50, 1000)])
    u = np.concatenate([np.tile([0.15] + [0.25] * 99, 50), np.full(950, 0.05)])
    y = np.concatenate([np.tile([0] + [1] * 99, 50), np.ones(950, dtype=int)])
    sel = at.select_threshold(f, u, y, [0.1, 0.2, 0.3], 0.05, 0.05)
    assert sel.p_values[0] <= 0.05 and sel.p_values[1] == 1.0 and sel.p_values[2] <= 0.05
    assert sel.tau == 0.1 and sel.index == 0


def test_outcomes_from_interval():
    n = 2000
    zero = {"frame": np.arange(n), "u": np.zeros(n), "correct": np.ones(n, dtype=int)}
    half = {"frame": np.arange(n), "u": np.zeros(n), "correct": np.arange(n) % 2}
    assert at.applicability_test(zero, zero, [0.5], 0.01).outcome == at.APPLICABLE
    assert at.applicability_test(zero, half, [0.5], 0.01).outcome == at.NOT_APPLICABLE
    small = {"frame": np.arange(300), "u": np.zeros(300), "correct": np.ones(300, dtype=int)}
    r = at.applicability_test(zero, small, [0.5], 0.01)   # 300 < 368 units at delta/2
    assert r.outcome == at.NOT_DETERMINED and r.L <= 0.01 < r.U


def test_zero_failure_bound_values():
    assert at.zero_failure_bound(1e-2, 0.05) == 299
    assert at.zero_failure_bound(1e-2, 0.025) == 368
    assert at.zero_failure_bound(1e-3, 0.05) == 2995
    for alpha in (1e-2, 1e-3, 1e-4):
        for d in (0.05, 0.025, 0.05 / 6):
            assert at.zero_failure_bound(alpha, d) == at.n_required(alpha, d)
    assert at.lowest_limit(400, 0.025) == pytest.approx(at.hb_upper(0.0, 400, 0.025), abs=1e-9)


def test_input_validation():
    with pytest.raises(ValueError):
        at.per_unit_shares([0, 1], [0.1, float("nan")], [1, 0], 0.5)
    with pytest.raises(ValueError):
        at.per_unit_shares([0, 1], [0.1, 0.2], [1, 2], 0.5)
    with pytest.raises(ValueError):
        at.applicability_test({"frame": [0], "u": [0.1], "correct": [1]}, {"frame": [0], "u": [0.1], "correct": [1]},
                              [0.5], 0.1, unit="sequence")


def test_cli_json(tmp_path, capsys):
    rng = np.random.default_rng(3)
    lines = ["frame,sequence,condition,part,u,correct"]
    for f in range(1500):
        part = "grid" if f < 150 else ("selection" if f < 825 else "test")
        for cond, p_wrong in (("near", 0.0), ("far", 0.2)):
            ok = int(rng.uniform() >= p_wrong)
            lines.append(f"{f},{f // 10},{cond},{part},{rng.uniform(0.0, 0.3) if ok else rng.uniform(0.2, 1):.6f},{ok}")
    path = tmp_path / "d.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert cli_main([str(path), "--selection-condition", "near", "--use-condition", "far",
                     "--alpha", "0.01", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["outcome"] == at.NOT_APPLICABLE and out["n_selection"] == 675
    assert cli_main([str(path), "--selection-condition", "near", "--use-condition", "near", "--alpha", "0.01",
                     "--unit", "sequence", "--candidates", "values", "--values", "0.05:0.5:0.05"]) == 0
    text = capsys.readouterr().out
    assert "evaluation: sequence-level" in text and "units: 68 in the selection part" in text

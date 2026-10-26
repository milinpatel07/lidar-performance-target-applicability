"""Sanity tests of seq_ratio.py. Run from case_study/: python3 -m pytest results/post_hoc/code/tests

seq_ratio.py is published as it ran and loads the experiment scripts from the container folder
/data/work/code/experiments; outside that container the test loads the same files from case_study/experiments/.
The test of the betting interval needs confseq (requirements-posthoc.txt) and the reproduction of the paper needs the
cache and the recorded results; both are skipped without them."""
import importlib.util, math, sys
from pathlib import Path
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent.parent
EXPERIMENTS = HERE.parents[2] / "experiments"
_spec_from_file = importlib.util.spec_from_file_location


def _from_experiments(name, location, *args, **kwargs):
    p = Path(location)
    if not p.exists() and p.parent.as_posix() == "/data/work/code/experiments":
        location = str(EXPERIMENTS / p.name)
    return _spec_from_file(name, location, *args, **kwargs)


importlib.util.spec_from_file_location = _from_experiments
try:
    spec = importlib.util.spec_from_file_location("seq_ratio", str(HERE / "seq_ratio.py"))
    sr = importlib.util.module_from_spec(spec); sys.modules["seq_ratio"] = sr; spec.loader.exec_module(sr)
finally:
    importlib.util.spec_from_file_location = _spec_from_file
m1 = sr.m1


def synthetic_cell(rng, n_seq, nmax, p_wrong, alpha_unused=None):
    """Sequences with 1..nmax frames, 0..5 detections per frame; returns a SeqCell and its frame-level parts."""
    fpos, u, y, unit_f, f = [], [], [], [], 0
    for s in range(n_seq):
        for _ in range(rng.integers(1, nmax + 1)):
            k = rng.integers(1, 6)
            fpos += [f] * k; u += list(rng.uniform(size=k)); y += list((rng.uniform(size=k) > p_wrong).astype(np.uint8))
            unit_f.append(s); f += 1
    return sr.SeqCell(np.array(fpos), np.array(u), np.array(y, np.uint8), np.array(unit_f), nmax)


def test_transform_keeps_the_ratio_condition():
    """E[Y] <= alpha exactly when E[S]/E[N] <= alpha, on synthetic populations with known E[S]/E[N]."""
    rng = np.random.default_rng(1)
    agree = 0
    for _ in range(2000):
        nmax = int(rng.integers(1, 40)); m = int(rng.integers(1, 60))
        N = rng.integers(1, nmax + 1, size=m).astype(float)
        S = N * rng.uniform(0, 1, size=m) * rng.uniform(0, 0.3)
        alpha = float(rng.choice([1e-4, 1e-3, 1e-2, 0.05, 0.1]))
        Y = (S - alpha * N + alpha * nmax) / nmax
        assert (Y >= -1e-15).all() and (Y <= 1 + 1e-15).all()
        assert abs((Y.mean() - alpha) - (S.mean() - alpha * N.mean()) / nmax) < 1e-12
        agree += (Y.mean() <= alpha) == (S.sum() / N.sum() <= alpha)
    assert agree == 2000
    # exact boundary: E[S]/E[N] = alpha gives E[Y] = alpha
    N = np.array([1.0, 3.0, 4.0]); alpha = 0.25; S = alpha * N
    assert abs(((S - alpha * N + alpha * 4) / 4).mean() - alpha) < 1e-15


def test_zero_false_acceptances_give_the_implied_pvalue():
    """With no false acceptance, Y_s = alpha (N_max - N_s) / N_max and the HB p-value follows from it."""
    rng = np.random.default_rng(2)
    for nmax in (1, 7, 40):
        cell = synthetic_cell(rng, 120, nmax, p_wrong=0.0)
        for alpha in (1e-2, 0.05, 0.1):
            for tau in (0.2, 0.7, 1.0):
                Y = cell.Y(tau, alpha)
                implied = alpha * (nmax - cell.N) / nmax
                assert np.allclose(Y, implied, atol=1e-15)
                assert m1.hb_pvalue(Y.sum(), cell.m, alpha) == m1.hb_pvalue(implied.sum(), cell.m, alpha)


def test_single_frame_sequences_equal_frame_unit():
    """N_s = 1 for all s: Y_s equals a_f, so selection and evaluation equal the frame-unit procedure (synthetic)."""
    rng = np.random.default_rng(3)
    cell = synthetic_cell(rng, 800, 1, p_wrong=0.3)
    assert (cell.N == 1).all()
    grid = np.unique(np.quantile(cell.fc.u, m1.CFG["grid_levels"]))
    for alpha in (0.05, 0.1, 0.2):
        assert np.array_equal(cell.Y(0.5, alpha), cell.fc.a_f(0.5))
        S = np.array([cell.fc.a_f(t).sum() for t in grid])
        j = m1.chain_index([[m1.hb_pvalue(S[k], cell.fc.m, alpha) for k in range(len(grid))]], m1.CFG["delta"])
        assert sr.select(cell, grid, alpha) == (float(grid[j]) if j >= 0 else None)


@pytest.mark.skipif(not (sr.REL / "cache/tables.pkl").exists(), reason="needs the cache and recorded results")
def test_single_frame_sequences_reproduce_the_paper():
    """N_s = 1 (every frame its own sequence, frame division): every recorded frame-unit row of the paper, all splits."""
    data = sr.load(sr.REL / "ext/kitti_devkit", Path("/data/nuscenes/v1.0-trainval"))
    n, bad = sr.gate(data, modes=("frame/frame",))
    assert n == 4 * 2 * 5 * 5 * 4 and not bad, bad[:5]


def test_betting_interval_covers_bernoulli_means():
    """Method B: coverage of betting_ci (two-sided, delta) on simulated Bernoulli data."""
    pytest.importorskip("confseq")
    sr.BREAKS = 1000      # coarser grid for speed; confseq widens each bound by one grid step at any resolution
    rng = np.random.default_rng(4)
    for p, n in ((0.05, 60), (0.3, 150)):
        reps, cov = 300, 0
        for _ in range(reps):
            l, u = sr.betting_bounds((rng.uniform(size=n) < p).astype(float), int(rng.integers(1 << 30)))
            cov += l <= p <= u
        assert cov / reps >= 1 - sr.DELTA - 3 * math.sqrt(sr.DELTA * (1 - sr.DELTA) / reps)

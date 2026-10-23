"""Applicability test of a performance target across conditions (Sect. 3 of the paper).

Input data are detections of one condition in one part (selection part or test part):
one entry per detection with its frame id, optional sequence id, indicator value u
and a flag that is 1 for a correct and 0 for a wrong detection. A frame belongs to
the condition if it holds at least one of these detections. A detection is accepted
if u <= tau.
"""
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from .stats import hb_lower, hb_pvalue, hb_upper

__all__ = [
    "per_unit_shares", "fap", "retention", "quantile_candidates",
    "select_threshold", "test_threshold", "applicability_test",
    "SelectionResult", "TestResult", "ApplicabilityResult",
    "APPLICABLE", "NOT_APPLICABLE", "NOT_DETERMINED", "NO_THRESHOLD",
]

APPLICABLE = "applicable"
NOT_APPLICABLE = "not applicable"
NOT_DETERMINED = "not determined"
NO_THRESHOLD = "no threshold selected"


class _Units:
    """Detections of one condition in one part, grouped into frames and units.

    Frame-level evaluation: each frame is a unit. Sequence-level evaluation: each
    sequence is a unit, and its value is the mean of a_f over its frames in the
    condition. Units are ordered by sorted id.
    """

    def __init__(self, frame_ids, u, correct, unit_ids=None):
        frame_ids = np.asarray(frame_ids)
        u = np.asarray(u, dtype=float)
        correct = np.asarray(correct)
        if not (len(frame_ids) == len(u) == len(correct)):
            raise ValueError("frame ids, u and correct must have the same length")
        if np.isnan(u).any():
            raise ValueError("u contains NaN")
        if len(correct) and not np.isin(correct, (0, 1)).all():
            raise ValueError("correct must contain only 0 and 1")
        self.u, self.y = u, correct.astype(np.int8)
        if unit_ids is None:
            self.ids, self.lfr = np.unique(frame_ids, return_inverse=True)
            self.mf = self.m = len(self.ids)
            self.fs = None
        else:
            unit_ids = np.asarray(unit_ids)
            if len(unit_ids) != len(u):
                raise ValueError("unit ids must have the same length as u")
            self.ids, s_inv = np.unique(unit_ids, return_inverse=True)
            _, f_inv = np.unique(frame_ids, return_inverse=True)
            # a frame is keyed by (sequence, frame), so frame ids need to be unique only within a sequence
            nfr = int(f_inv.max()) + 1 if len(f_inv) else 1
            fkeys, self.lfr = np.unique(s_inv.astype(np.int64) * nfr + f_inv, return_inverse=True)
            self.mf, self.m = len(fkeys), len(self.ids)
            self.fs = fkeys // nfr  # frame -> unit
            self.nf = np.bincount(self.fs, minlength=self.m).astype(float)
        self.lfr = self.lfr.reshape(-1)

    def shares(self, tau):
        acc = self.u <= tau
        na = np.bincount(self.lfr[acc], minlength=self.mf)
        nw = np.bincount(self.lfr[acc & (self.y == 0)], minlength=self.mf)
        a = np.zeros(self.mf)
        nz = na > 0
        a[nz] = nw[nz] / na[nz]
        if self.fs is None:
            return a
        return np.bincount(self.fs, weights=a, minlength=self.m) / np.maximum(self.nf, 1)

    def retention(self, tau):
        c = int((self.y == 1).sum())
        return float(((self.u <= tau) & (self.y == 1)).sum() / c) if c > 0 else float("nan")


def per_unit_shares(frame_ids, u, correct, tau, unit_ids=None):
    """Per-unit values of the false acceptance share at threshold tau.

    Without ``unit_ids``: the per-frame share a_f (Eq. 2), the share of wrong
    detections among the accepted detections of the frame, and 0 for a frame
    without accepted detections. With ``unit_ids`` (sequence ids): one value per
    sequence, the mean of a_f over its frames. Returns ``(ids, values)`` with ids
    sorted.
    """
    units = _Units(frame_ids, u, correct, unit_ids)
    return units.ids, units.shares(tau)


def fap(frame_ids, u, correct, tau, unit_ids=None):
    """Estimate of the FAP: the mean of the per-unit values (nan if there are no units)."""
    _, a = per_unit_shares(frame_ids, u, correct, tau, unit_ids)
    return float(a.mean()) if len(a) else float("nan")


def retention(u, correct, tau):
    """Share of the correct detections that the threshold accepts (u <= tau); nan if there are none."""
    return _Units(np.zeros(len(u)), u, correct).retention(tau)


def quantile_candidates(u, levels=None):
    """Candidate thresholds: the distinct quantiles of u at levels 0.01, 0.02, ..., 1.00 (sorted).

    The paper takes them from a grid part of the frames, separate from the
    selection and test parts, over the detections of both conditions.
    """
    if levels is None:
        levels = [round(0.01 * i, 2) for i in range(1, 101)]
    return np.unique(np.quantile(np.asarray(u, dtype=float), levels))


@dataclass
class SelectionResult:
    """Result of the fixed-sequence selection in the condition of selection."""
    tau: Optional[float]          # selected threshold, None if no threshold is selected
    index: int                    # index of tau in candidates, -1 if none
    candidates: List[float]       # sorted candidates
    p_values: List[float]         # HB p-value of each candidate
    n: int                        # number of independent units in the selection part
    alpha: float
    delta: float


@dataclass
class TestResult:
    """Result of testing one threshold on the test part of the condition of use."""
    __test__ = False              # not a pytest test class
    tau: float
    L: float                      # lower confidence bound of the FAP (delta/2)
    U: float                      # upper confidence bound of the FAP (delta/2)
    A_hat: float                  # estimate of the FAP
    n: int                        # number of independent units in the test part
    retention: float              # retention on the test part
    outcome: str
    alpha: float
    delta: float


@dataclass
class ApplicabilityResult:
    """Outcome of the applicability test for one condition of selection and one condition of use."""
    outcome: str
    tau: Optional[float]
    L: Optional[float]
    U: Optional[float]
    A_hat: Optional[float]
    retention: Optional[float]    # retention in the condition of use (test part)
    n_selection: int
    n_test: int
    unit: str
    alpha: float
    delta: float
    selection: SelectionResult = field(repr=False)


def select_threshold(frame_ids, u, correct, candidates, alpha, delta, unit_ids=None):
    """Select a threshold on the selection part of the condition of selection.

    A candidate passes if its HB p-value for the null hypothesis FAP > alpha is at
    most delta. Candidates are taken from the lowest upwards; the selected
    threshold is the last candidate that passes before the first candidate that
    fails. If the lowest candidate fails, no threshold is selected (tau None).
    """
    units = _Units(frame_ids, u, correct, unit_ids)
    cand = np.unique(np.asarray(candidates, dtype=float))
    p = [hb_pvalue(units.shares(t).sum(), units.m, alpha) for t in cand]
    last = -1
    for j, pj in enumerate(p):
        if pj <= delta:
            last = j
        else:
            break
    return SelectionResult(tau=float(cand[last]) if last >= 0 else None, index=last,
                           candidates=[float(t) for t in cand], p_values=p,
                           n=units.m, alpha=alpha, delta=delta)


def _outcome(L, U, alpha):
    return APPLICABLE if U <= alpha else (NOT_APPLICABLE if L > alpha else NOT_DETERMINED)


def test_threshold(frame_ids, u, correct, tau, alpha, delta, unit_ids=None):
    """Test threshold tau on the test part of the condition of use.

    [L, U] is the HB interval of the FAP at confidence level 1 - delta (each bound
    at delta/2). Outcome: applicable if U <= alpha, not applicable if L > alpha,
    not determined otherwise.
    """
    units = _Units(frame_ids, u, correct, unit_ids)
    a = units.shares(tau)
    S, n = a.sum(), units.m
    U, L = hb_upper(S, n, delta / 2), hb_lower(S, n, delta / 2)
    return TestResult(tau=float(tau), L=L, U=U, A_hat=float(S / n) if n else float("nan"), n=n,
                      retention=units.retention(tau), outcome=_outcome(L, U, alpha),
                      alpha=alpha, delta=delta)


test_threshold.__test__ = False  # not a pytest test function


def _columns(data, unit):
    seq = None
    if unit == "sequence":
        if "sequence" not in data:
            raise ValueError("unit='sequence' needs a 'sequence' entry in the data")
        seq = data["sequence"]
    elif unit != "frame":
        raise ValueError("unit must be 'frame' or 'sequence'")
    return data["frame"], data["u"], data["correct"], seq


def applicability_test(selection, use, candidates, alpha, delta=0.05, unit="frame"):
    """Applicability test of the performance target FAP <= alpha.

    ``selection``: detections of the condition of selection c in the selection part.
    ``use``: detections of the condition of use c' in the test part.
    Each is a mapping (a dict of arrays or a pandas DataFrame) with entries
    ``frame``, ``u``, ``correct`` and, for ``unit='sequence'``, ``sequence``.
    ``unit='frame'`` is the frame-level evaluation, ``unit='sequence'`` the
    sequence-level evaluation.
    """
    f, u, y, s = _columns(selection, unit)
    sel = select_threshold(f, u, y, candidates, alpha, delta, s)
    f2, u2, y2, s2 = _columns(use, unit)
    if sel.tau is None:
        n_test = _Units(f2, u2, y2, s2).m
        return ApplicabilityResult(NO_THRESHOLD, None, None, None, None, None, sel.n, n_test,
                                   unit, alpha, delta, sel)
    t = test_threshold(f2, u2, y2, sel.tau, alpha, delta, s2)
    return ApplicabilityResult(t.outcome, sel.tau, t.L, t.U, t.A_hat, t.retention, sel.n, t.n,
                               unit, alpha, delta, sel)

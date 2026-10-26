"""Hoeffding-Bentkus (HB) p-value, confidence bounds and the zero-failure bound.

The functions ``hb_pvalue``, ``hb_upper``, ``hb_lower`` and ``n_required`` are the
statistics of ``case_study/experiments/m1_range_kitti.py`` with unchanged arithmetic, so that the
package gives the same numbers as the recorded runs. The losses are per-unit
values in [0, 1] (per-frame shares or per-sequence means), assumed independent and
identically distributed.
"""
import math

__all__ = ["hb_pvalue", "hb_upper", "hb_lower", "n_required", "zero_failure_bound", "lowest_limit"]


def _h1(a, b):
    out = 0.0
    if a > 0:
        out += a * math.log(a / b)
    if a < 1:
        out += (1 - a) * math.log((1 - a) / (1 - b))
    return out


def _log_binom_cdf(k, n, p):
    if k < 0:
        return -math.inf
    if k >= n:
        return 0.0
    lg = math.lgamma
    lp, lq = math.log(p), math.log1p(-p)
    terms = [lg(n + 1) - lg(i + 1) - lg(n - i + 1) + i * lp + (n - i) * lq for i in range(k + 1)]
    m = max(terms)
    return m + math.log(sum(math.exp(t - m) for t in terms))


def hb_pvalue(S, n, alpha):
    """HB p-value for the null hypothesis E[loss] > alpha.

    S is the sum of n independent losses in [0, 1]. Returns 1 if n <= 0 or if the
    mean S/n is at least alpha.
    """
    if n <= 0:
        return 1.0
    rhat = S / n
    if rhat >= alpha:
        return 1.0
    p1 = math.exp(-n * _h1(min(rhat, alpha), alpha))
    k = math.ceil(S - 1e-9)  # tolerance against a sum such as 2.9999999 from floating-point addition
    p2 = math.e * math.exp(_log_binom_cdf(k, n, alpha))
    return min(1.0, p1, p2)


def hb_upper(S, n, delta):
    """Upper confidence bound of E[loss]: the smallest alpha with hb_pvalue <= delta.

    Found by 50 bisection steps on [S/n, 1 - 1e-12]; returns 1 if n <= 0 or if no
    alpha below 1 is rejected.
    """
    if n <= 0:
        return 1.0
    lo, hi = S / n, 1.0 - 1e-12
    if hb_pvalue(S, n, hi) > delta:
        return 1.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        if hb_pvalue(S, n, mid) <= delta:
            hi = mid
        else:
            lo = mid
    return hi


def hb_lower(S, n, delta):
    """Lower confidence bound of E[loss]: one minus the upper bound of the values 1 - loss."""
    if n <= 0:
        return 0.0
    return 1.0 - hb_upper(n - S, n, delta)


def n_required(alpha, delta):
    """Smallest n at which n units without any false acceptance give hb_pvalue <= delta."""
    lo, hi = 1, 1
    while hb_pvalue(0.0, hi, alpha) > delta:
        hi *= 2
    while lo < hi:
        mid = (lo + hi) // 2
        if hb_pvalue(0.0, mid, alpha) <= delta:
            hi = mid
        else:
            lo = mid + 1
    return lo


def zero_failure_bound(alpha, delta):
    """Zero-failure bound (Eq. 5 of the paper): the smallest integer n with n >= ln(delta) / ln(1 - alpha).

    It is a necessary number of independent units per condition and part for showing
    that the limit alpha is met at error probability delta (delta for selecting,
    delta/2 for testing a threshold). Any unit with a false acceptance raises the
    number further.
    """
    if not (0 < alpha < 1 and 0 < delta < 1):
        raise ValueError("alpha and delta must lie in (0, 1)")
    return math.ceil(math.log(delta) / math.log1p(-alpha))


def lowest_limit(n, delta):
    """Lowest limit that n units without any false acceptance can show: 1 - delta**(1/n).

    This is Eq. 5 solved for alpha; it equals hb_upper(0, n, delta) up to the bisection tolerance.
    """
    if n <= 0:
        return 1.0
    return 1.0 - delta ** (1.0 / n)

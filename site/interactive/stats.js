// Hoeffding-Bentkus p-value, confidence bounds and zero-failure bound.
// Port of hb_pvalue, hb_upper, hb_lower and n_required in experiments/m1_range_kitti.py;
// the HB test depends on the per-unit values only through their sum S and count n.
(function (root) {
  "use strict";

  function h1(a, b) {
    let out = 0;
    if (a > 0) out += a * Math.log(a / b);
    if (a < 1) out += (1 - a) * Math.log((1 - a) / (1 - b));
    return out;
  }

  // log Gamma (Lanczos, g = 7, n = 9), accurate to about 1e-15 relative for x > 0
  const LG = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6,
    1.5056327351493116e-7];
  function lgamma(x) {
    if (x < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * x))) - lgamma(1 - x);
    x -= 1;
    let a = LG[0];
    const t = x + 7.5;
    for (let i = 1; i < 9; i++) a += LG[i] / (x + i);
    return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
  }

  function logBinomCdf(k, n, p) {
    if (k < 0) return -Infinity;
    if (k >= n) return 0;
    const lp = Math.log(p), lq = Math.log1p(-p);
    const terms = [];
    for (let i = 0; i <= k; i++)
      terms.push(lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1) + i * lp + (n - i) * lq);
    const m = Math.max(...terms);
    let s = 0;
    for (const t of terms) s += Math.exp(t - m);
    return m + Math.log(s);
  }

  // p-value for H: E[loss] > alpha from n independent losses in [0, 1] with sum S
  function hbPvalue(S, n, alpha) {
    if (n <= 0) return 1;
    const rhat = S / n;
    if (rhat >= alpha) return 1;
    const p1 = Math.exp(-n * h1(Math.min(rhat, alpha), alpha));
    const k = Math.ceil(S - 1e-9);
    const p2 = Math.E * Math.exp(logBinomCdf(k, n, alpha));
    return Math.min(1, p1, p2);
  }

  // smallest alpha at which H: E[loss] > alpha is rejected at level delta
  function hbUpper(S, n, delta) {
    if (n <= 0) return 1;
    let lo = S / n, hi = 1 - 1e-12;
    if (hbPvalue(S, n, hi) > delta) return 1;
    for (let i = 0; i < 50; i++) {
      const mid = 0.5 * (lo + hi);
      if (hbPvalue(S, n, mid) <= delta) hi = mid; else lo = mid;
    }
    return hi;
  }

  function hbLower(S, n, delta) {
    if (n <= 0) return 0;
    return 1 - hbUpper(n - S, n, delta);
  }

  // smallest n at which zero observed false acceptances reject H: risk > alpha
  function nRequired(alpha, delta) {
    let lo = 1, hi = 1;
    while (hbPvalue(0, hi, alpha) > delta) hi *= 2;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (hbPvalue(0, mid, alpha) <= delta) hi = mid; else lo = mid + 1;
    }
    return lo;
  }

  // Eq. (5) of the paper: n >= ln(delta') / ln(1 - alpha)
  function zeroFailureBound(alpha, deltaPrime) {
    return Math.log(deltaPrime) / Math.log(1 - alpha);
  }

  // lowest limit that n units without a false acceptance can show to be met (inverse of Eq. (5))
  function lowestLimit(n, deltaPrime) {
    return 1 - Math.pow(deltaPrime, 1 / n);
  }

  // outcome of the applicability test (Sect. 3.3): interval [L, U] at confidence 1 - delta
  function outcome(L, U, alpha) {
    if (U <= alpha) return "applicable";
    if (L > alpha) return "not applicable";
    return "not determined";
  }

  const api = { hbPvalue, hbUpper, hbLower, nRequired, zeroFailureBound, lowestLimit, outcome, lgamma };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.HB = api;
})(this);

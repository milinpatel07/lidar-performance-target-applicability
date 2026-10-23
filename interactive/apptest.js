// Applicability test on a table of detections: the computation behind own-data.html.
// Mirrors analyse() and the class Cell in analysis/m1_range_kitti.py and package/src/applicability_test/core.py:
// a detection is accepted if u <= tau; a frame belongs to a condition if it holds a detection of the condition;
// a_f is the share of wrong detections among the accepted detections of the condition in frame f, and 0 for a
// frame without accepted detections; in the sequence-level evaluation the value of a sequence is the mean of a_f
// over its frames in the condition (frames keyed by sequence and frame); candidates are taken from the lowest
// upwards and the selected threshold is the last candidate that passes before the first that fails; the test
// interval [L, U] uses delta/2 on each side. Needs stats.js (HB) in the browser, or require("./stats.js") in node.
(function (root) {
  "use strict";
  const HB = (typeof module !== "undefined" && module.exports) ? require("./stats.js") : root.HB;

  const APPLICABLE = "applicable", NOT_APPLICABLE = "not applicable", NOT_DETERMINED = "not determined",
    NO_THRESHOLD = "no threshold selected";

  // ---------- CSV ----------
  function splitLine(line, sep) {
    const out = []; let cur = "", q = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (q) {
        if (ch === '"') { if (line[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch;
      } else if (ch === '"') q = true;
      else if (ch === sep) { out.push(cur); cur = ""; } else cur += ch;
    }
    out.push(cur);
    return out.map(s => s.trim());
  }
  const PART = { selection: "selection", select: "selection", test: "test", eval: "test", grid: "grid" };
  const CORRECT = { "1": 1, "0": 0, "true": 1, "false": 0, "1.0": 1, "0.0": 0 };

  // returns {rows, hasSequence, hasPart, errors, warnings}; rows: {frame, sequence, condition, part, u, correct}
  function parseCSV(text, maxErrors) {
    maxErrors = maxErrors || 10;
    const lines = text.replace(/^﻿/, "").split(/\r?\n/).filter(l => l.trim() !== "");
    const errors = [], warnings = [];
    if (!lines.length) return { rows: [], errors: ["The file is empty."], warnings };
    const sep = [",", ";", "\t"].map(s => [s, lines[0].split(s).length]).sort((a, b) => b[1] - a[1])[0][0];
    const head = splitLine(lines[0], sep).map(h => h.toLowerCase());
    const col = name => head.indexOf(name);
    for (const need of ["frame", "condition", "u", "correct"])
      if (col(need) < 0) errors.push(`Column '${need}' is missing (header: ${head.join(", ")}).`);
    if (errors.length) return { rows: [], errors, warnings };
    const iF = col("frame"), iS = col("sequence"), iC = col("condition"), iP = col("part"), iU = col("u"), iY = col("correct");
    const rows = [];
    for (let k = 1; k < lines.length; k++) {
      const f = splitLine(lines[k], sep);
      const u = Number(f[iU]), y = CORRECT[String(f[iY]).toLowerCase()];
      let part = null;
      if (iP >= 0) part = PART[String(f[iP]).toLowerCase()];
      const bad = [];
      if (f[iF] === undefined || f[iF] === "") bad.push("frame is empty");
      if (f[iC] === undefined || f[iC] === "") bad.push("condition is empty");
      if (f[iU] === "" || !Number.isFinite(u)) bad.push(`u '${f[iU]}' is not a number`);
      if (y === undefined) bad.push(`correct '${f[iY]}' is not 1 or 0`);
      if (iP >= 0 && !part) bad.push(`part '${f[iP]}' is not selection, test or grid`);
      if (iS >= 0 && (f[iS] === undefined || f[iS] === "")) bad.push("sequence is empty");
      if (bad.length) { if (errors.length < maxErrors) errors.push(`line ${k + 1}: ${bad.join("; ")}`); continue; }
      rows.push({ frame: f[iF], sequence: iS >= 0 ? f[iS] : null, condition: f[iC], part, u, correct: y });
    }
    if (iS >= 0) {
      const seqOf = new Map(); let rep = 0;
      for (const r of rows) { const s = seqOf.get(r.frame); if (s === undefined) seqOf.set(r.frame, r.sequence); else if (s !== r.sequence) rep++; }
      if (rep) warnings.push("Some frame ids occur in more than one sequence. The frame-level evaluation treats rows with the same frame id as one frame; the sequence-level evaluation keys frames by sequence and frame.");
    }
    return { rows, hasSequence: iS >= 0, hasPart: iP >= 0, errors, warnings };
  }

  function toCSV(rows, hasSequence) {
    const q = v => /[",;\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
    const head = ["frame"].concat(hasSequence ? ["sequence"] : [], ["condition", "part", "u", "correct"]);
    const out = [head.join(",")];
    for (const r of rows) out.push([r.frame].concat(hasSequence ? [r.sequence] : [], [r.condition, r.part, r.u, r.correct]).map(q).join(","));
    return out.join("\n") + "\n";
  }

  // ---------- seeded random numbers and division into parts ----------
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  // assigns part to every row: 'selection' for round(share * N) randomly drawn frames (or sequences), 'test' otherwise
  function divide(rows, by, selShare, seed) {
    const key = r => by === "sequence" ? r.sequence : (r.sequence === null ? r.frame : r.sequence + "\u0001" + r.frame);
    const keys = [...new Set(rows.map(key))].sort();
    const rnd = mulberry32(seed);
    for (let i = keys.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); const t = keys[i]; keys[i] = keys[j]; keys[j] = t; }
    const nSel = Math.round(selShare * keys.length);
    const part = new Map(keys.map((k, i) => [k, i < nSel ? "selection" : "test"]));
    return rows.map(r => Object.assign({}, r, { part: part.get(key(r)) }));
  }

  // ---------- candidates: numpy.quantile (method 'linear') at levels 0.01..1.00, then unique ----------
  function defaultLevels() { const l = []; for (let i = 1; i <= 100; i++) l.push(i / 100); return l; }
  function quantile(sorted, q) {
    const n = sorted.length;
    const v = n * q + (1 + q * (1 - 1 - 1)) - 1;   // numpy _compute_virtual_index with alpha = beta = 1
    if (v >= n - 1) return sorted[n - 1];
    if (v < 0) return sorted[0];
    const i = Math.floor(v), t = v - i, a = sorted[i], b = sorted[i + 1], d = b - a;
    return t >= 0.5 ? b - d * (1 - t) : a + d * t;   // numpy _lerp
  }
  function quantileCandidates(values, levels) {
    if (!values.length) return [];
    const s = Float64Array.from(values).sort();
    return uniqueSorted((levels || defaultLevels()).map(q => quantile(s, q)));
  }
  function uniqueSorted(v) {
    const s = v.slice().sort((a, b) => a - b), out = [];
    for (const x of s) if (!out.length || x !== out[out.length - 1]) out.push(x);
    return out;
  }

  // ---------- units of one condition in one part ----------
  // dets: rows of one condition and one part; unit 'frame' or 'sequence'
  function Units(dets, unit) {
    const n = dets.length;
    this.u = new Float64Array(n); this.y = new Uint8Array(n); this.fr = new Int32Array(n);
    const fkey = unit === "sequence" ? (d => d.sequence + "\u0001" + d.frame) : (d => d.frame);
    const fIds = [...new Set(dets.map(fkey))].sort();
    const fIndex = new Map(fIds.map((k, i) => [k, i]));
    dets.forEach((d, i) => { this.u[i] = d.u; this.y[i] = d.correct; this.fr[i] = fIndex.get(fkey(d)); });
    this.mf = fIds.length;
    this.correctTotal = this.y.reduce((s, v) => s + v, 0);
    if (unit === "sequence") {
      const sIds = [...new Set(dets.map(d => d.sequence))].sort();
      const sIndex = new Map(sIds.map((k, i) => [k, i]));
      this.fs = new Int32Array(this.mf);
      dets.forEach(d => { this.fs[fIndex.get(fkey(d))] = sIndex.get(d.sequence); });
      this.m = sIds.length;
      this.nf = new Float64Array(this.m);
      for (let f = 0; f < this.mf; f++) this.nf[this.fs[f]] += 1;
    } else { this.fs = null; this.m = this.mf; }
  }
  Units.prototype.shares = function (tau) {
    const na = new Float64Array(this.mf), nw = new Float64Array(this.mf);
    for (let i = 0; i < this.u.length; i++) if (this.u[i] <= tau) { na[this.fr[i]] += 1; if (!this.y[i]) nw[this.fr[i]] += 1; }
    const a = new Float64Array(this.mf);
    for (let f = 0; f < this.mf; f++) if (na[f] > 0) a[f] = nw[f] / na[f];
    if (!this.fs) return a;
    const s = new Float64Array(this.m);
    for (let f = 0; f < this.mf; f++) s[this.fs[f]] += a[f];
    for (let k = 0; k < this.m; k++) s[k] /= Math.max(this.nf[k], 1);
    return s;
  };
  Units.prototype.sum = function (tau) { return this.shares(tau).reduce((s, v) => s + v, 0); };
  Units.prototype.retention = function (tau) {
    if (!this.correctTotal) return NaN;
    let c = 0;
    for (let i = 0; i < this.u.length; i++) if (this.y[i] && this.u[i] <= tau) c++;
    return c / this.correctTotal;
  };

  function outcomeOf(L, U, alpha) { return U <= alpha ? APPLICABLE : (L > alpha ? NOT_APPLICABLE : NOT_DETERMINED); }

  function selectThreshold(units, candidates, alpha, delta) {
    const cand = uniqueSorted(candidates);
    const p = cand.map(t => HB.hbPvalue(units.sum(t), units.m, alpha));
    let last = -1;
    for (let j = 0; j < p.length; j++) { if (p[j] <= delta) last = j; else break; }
    return { tau: last >= 0 ? cand[last] : null, index: last, candidates: cand, pValues: p, n: units.m, alpha, delta };
  }

  function testThreshold(units, tau, alpha, delta) {
    const S = units.sum(tau), n = units.m;
    const U = HB.hbUpper(S, n, delta / 2), L = HB.hbLower(S, n, delta / 2);
    return { tau, L, U, A_hat: n ? S / n : NaN, n, retention: units.retention(tau), outcome: outcomeOf(L, U, alpha), alpha, delta };
  }

  // ---------- one dataset: conditions, candidates, pairs ----------
  function conditions(rows) { return [...new Set(rows.map(r => r.condition))].sort(); }
  function subset(rows, cond, part) { return rows.filter(r => r.condition === cond && r.part === part); }

  // candidates from the grid part of the given conditions if it has rows, else from their selection part
  function candidatesFor(rows, conds, opts) {
    if (opts && opts.candidates) return { values: uniqueSorted(opts.candidates), source: "list" };
    const inC = r => conds.indexOf(r.condition) >= 0;
    let pool = rows.filter(r => inC(r) && r.part === "grid"), source = "grid part";
    if (!pool.length) { pool = rows.filter(r => inC(r) && r.part === "selection"); source = "selection part"; }
    return { values: quantileCandidates(pool.map(r => r.u)), source };
  }

  // applicability test of the target FAP <= alpha for the condition of selection c and the condition of use c2
  function applicabilityTest(rows, c, c2, opts) {
    const unit = opts.unit || "frame", alpha = opts.alpha, delta = opts.delta;
    const cand = candidatesFor(rows, uniqueSorted([c, c2]), opts);
    const sel = selectThreshold(new Units(subset(rows, c, "selection"), unit), cand.values, alpha, delta);
    const useUnits = new Units(subset(rows, c2, "test"), unit);
    const own = c === c2 ? null : new Units(subset(rows, c, "test"), unit);
    const res = { c, c2, unit, alpha, delta, candidateSource: cand.source, selection: sel,
      nSelection: sel.n, nTest: useUnits.m,
      eq5Selection: Math.ceil(HB.zeroFailureBound(alpha, delta) - 1e-9), eq5Test: Math.ceil(HB.zeroFailureBound(alpha, delta / 2) - 1e-9) };
    if (sel.tau === null) {
      Object.assign(res, { outcome: NO_THRESHOLD, tau: null, test: null, ownCheck: c === c2 ? null : { outcome: NO_THRESHOLD, n: own.m } });
      return res;
    }
    res.tau = sel.tau;
    res.test = testThreshold(useUnits, sel.tau, alpha, delta);
    res.outcome = res.test.outcome;
    res.ownCheck = c === c2 ? res.test : testThreshold(own, sel.tau, alpha, delta);
    return res;
  }

  // every ordered pair (c, c2), including c2 = c; candidates over both conditions of each pair
  function runAll(rows, opts) {
    const cs = conditions(rows), out = [];
    for (const c of cs) for (const c2 of cs) out.push(applicabilityTest(rows, c, c2, opts));
    return { conditions: cs, pairs: out };
  }

  // ---------- synthetic example (seeded; not data) ----------
  // conditions: 'base'; 'more_wrong' (larger share of wrong detections); 'shifted' (values of both kinds shifted
  // upwards); 'spread' (wrong detections concentrated in frames with few detections). Each sequence has one condition.
  function synthetic(seed, opts) {
    opts = opts || {};
    const rnd = mulberry32(seed === undefined ? 1 : seed);
    const nSeq = opts.sequences || 120, perSeq = opts.framesPerSequence || 25;
    const conds = ["base", "more_wrong", "shifted", "spread"];
    const P = { base: { w: 0.3, shift: 0, conc: 0 }, more_wrong: { w: 0.5, shift: 0, conc: 0 },
      shifted: { w: 0.3, shift: 0.08, conc: 0 }, spread: { w: 0.3, shift: 0, conc: 1 } };
    const normal = () => { const a = Math.max(rnd(), 1e-12), b = rnd(); return Math.sqrt(-2 * Math.log(a)) * Math.cos(2 * Math.PI * b); };
    // frames hold 1 to 8 detections with equal probability; in 'spread' the probability of a wrong detection in a
    // frame with k detections is proportional to 1/k, scaled so that the expected share of wrong detections would be w before the probability is capped at 1
    let num = 0, den = 0;
    for (let k = 1; k <= 8; k++) { num += k * Math.pow(k, -1); den += k; }
    const meanWeight = num / den;
    const rows = [];
    for (let s = 0; s < nSeq; s++) {
      const cond = conds[s % conds.length], p = P[cond];
      const seq = "s" + String(s).padStart(3, "0");
      for (let f = 0; f < perSeq; f++) {
        const k = 1 + Math.floor(rnd() * 8);
        const pf = Math.min(1, p.conc ? p.w * Math.pow(k, -1) / meanWeight : p.w);
        for (let i = 0; i < k; i++) {
          const wrong = rnd() < pf;
          const u = Math.min(1, Math.max(0, (wrong ? 0.5 : 0.3) + p.shift + 0.1 * normal()));
          rows.push({ frame: seq + "_f" + String(f).padStart(2, "0"), sequence: seq, condition: cond, part: null,
            u: Math.round(u * 1e4) / 1e4, correct: wrong ? 0 : 1 });
        }
      }
    }
    return rows;
  }

  const api = { parseCSV, toCSV, divide, mulberry32, quantile, quantileCandidates, uniqueSorted, Units,
    selectThreshold, testThreshold, applicabilityTest, runAll, candidatesFor, conditions, synthetic, outcomeOf,
    APPLICABLE, NOT_APPLICABLE, NOT_DETERMINED, NO_THRESHOLD };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.AppTest = api;
})(this);

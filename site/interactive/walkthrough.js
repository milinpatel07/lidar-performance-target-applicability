// Guided walk-through in seven steps. All detections and frames are schematic: drawn from a seeded generator
// (mulberry32), never measured. Statistics: stats.js (HB p-value and bounds). Recorded numbers appear only in
// step 6 and are read from data/units.json.
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { el, text, clear, lin, log, fmt, int, sup } = UI;
  const ALPHA = 0.05;                                   // schematic limit of steps 2 to 5
  const SD = 0.1, MU = 0.3, KMAX = 8;
  const BASE = { sep: 2.5, share: 0.3, shift: 0, conc: 0 }; // condition of selection c
  const DELTAS = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2];
  const CANDS = []; for (let t = 0.1; t <= 0.7001; t += 0.025) CANDS.push(+t.toFixed(3));
  const OUT = { "applicable": "A", "not applicable": "N", "not determined": "Q", "no threshold selected": "D" };

  // ---------- schematic model ----------
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function normal(r) { return Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r()); }
  // standard normal distribution function (Abramowitz and Stegun 7.1.26)
  function Phi(x) {
    const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x / 2);
    return x >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
  }
  // fixed random draws per detection, so that a change of a setting changes the frames smoothly
  function draws(seed, n) {
    const r = mulberry32(seed), F = [];
    for (let f = 0; f < n; f++) {
      const k = 1 + Math.floor(r() * KMAX), d = [];
      for (let i = 0; i < k; i++) d.push({ z: normal(r), v: r() });
      F.push(d);
    }
    return F;
  }
  // probability of a wrong detection in a frame with k detections; conc > 0 moves wrong detections into frames
  // with few detections, the scale is found by bisection so that the expected share per detection stays `share`
  function wrongProb(p) {
    const w = k => Math.pow(k, -1.5 * p.conc);
    const mean = s => { let a = 0; for (let k = 1; k <= KMAX; k++) a += k * Math.min(0.97, s * w(k)); return a / (KMAX * (KMAX + 1) / 2); };
    let lo = 0, hi = 100;
    for (let i = 0; i < 50; i++) { const m = (lo + hi) / 2; if (mean(m) < p.share) lo = m; else hi = m; }
    return k => Math.min(0.97, lo * w(k));
  }
  function label(D, p) {
    const pk = wrongProb(p);
    return D.map(d => { const q = pk(d.length); return d.map(x => {
      const wrong = x.v < q; return { wrong, u: MU + p.shift + SD * x.z + (wrong ? p.sep * SD : 0) }; }); });
  }
  // per-frame shares a_f, their sum S, FAP and retention at threshold tau
  function evalAt(F, tau, n) {
    n = Math.min(n || F.length, F.length);
    let S = 0, corr = 0, corrAcc = 0, empty = 0;
    for (let f = 0; f < n; f++) {
      let acc = 0, wr = 0;
      for (const d of F[f]) {
        if (!d.wrong) corr++;
        if (d.u <= tau) { acc++; if (d.wrong) wr++; else corrAcc++; }
      }
      if (acc) S += wr / acc; else empty++;
    }
    return { S, n, A: S / n, R: corr ? corrAcc / corr : 0, empty };
  }
  const auroc = p => Phi(p.sep / Math.SQRT2);

  // ---------- small drawing helpers ----------
  // correct: plain mark; wrong: the same mark with a cross, so that the two differ in shape as well as colour
  function mark(svg, x, y, w, h, cls, wrong, rx) {
    const g = el("g", {}, svg);
    el("rect", { x: x - w / 2, y: y - h / 2, width: w, height: h, rx: rx == null ? 2 : rx, class: "mk " + cls, "stroke-width": 1.4 }, g);
    if (wrong) {
      const s = Math.min(w, h) * 0.32, c = cls === "mk-acc-w" ? "#ffffff" : "var(--axis)";
      el("path", { d: `M${x - s},${y - s}L${x + s},${y + s}M${x + s},${y - s}L${x - s},${y + s}`, class: "glyph", stroke: c }, g);
    }
    return g;
  }
  function icon(cls, wrong) {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("width", 16); s.setAttribute("height", 16); s.setAttribute("viewBox", "0 0 16 16"); s.setAttribute("aria-hidden", "true");
    mark(s, 8, 8, 12, 12, cls, wrong);
    return s;
  }
  function tiles(box, items) {
    box.textContent = "";
    for (const it of items) {
      const d = document.createElement("div");
      if (it.icon) d.appendChild(icon(it.icon[0], it.icon[1]));
      const s = document.createElement("span"), b = document.createElement("b");
      b.textContent = it.value; s.appendChild(b); s.appendChild(document.createElement("br"));
      s.appendChild(document.createTextNode(it.label)); d.appendChild(s); box.appendChild(d);
    }
  }
  function legend(box, items) {
    box.textContent = "";
    for (const it of items) {
      const s = document.createElement("span");
      if (it.icon) s.appendChild(icon(it.icon[0], it.icon[1]));
      if (it.svg) s.insertAdjacentHTML("beforeend", it.svg);
      s.appendChild(document.createTextNode(it.label)); box.appendChild(s);
    }
  }
  const pct = v => (v * 100 < 0.1 && v > 0 ? "<0.1" : (+(v * 100).toFixed(1)).toString()) + " %";
  const badge = (node, o) => { node.className = "outcome " + OUT[o]; node.textContent = o; };
  // "τ" with subscript c, followed by `rest`
  function tauText(svg, x, y, rest, attrs) {
    const t = text(svg, x, y, "τ", attrs);
    el("tspan", { "baseline-shift": "sub", "font-size": "75%" }, t).textContent = "c";
    el("tspan", {}, t).textContent = rest;
    return t;
  }
  const line = (svg, x1, y1, x2, y2, cls, extra) => el("line", Object.assign({ x1, y1, x2, y2, class: cls }, extra || {}), svg);

  const state = { delta: 0.05, tauC: null, P: Object.assign({}, BASE) };

  // ---------- step 1: one frame ----------
  const ONE = (function () {
    const r = mulberry32(7), dets = [], wrongIdx = [2, 6, 9];
    const cols = [70, 150, 230, 310], rows = [40, 100, 160];
    let i = 0;
    for (let row = 0; row < 3; row++) for (let c = 0; c < 4; c++) {
      if (row === 2 && (c === 1 || c === 2)) continue;  // keep the area in front of the vehicle free
      const wrong = wrongIdx.indexOf(i) >= 0;
      const u = Math.min(0.97, Math.max(0.03, MU + SD * normal(r) + (wrong ? BASE.sep * SD : 0)));
      dets.push({ x: cols[c] + (r() - 0.5) * 30, y: rows[row] + (r() - 0.5) * 18, rot: (r() - 0.5) * 24, u: +u.toFixed(2), wrong });
      i++;
    }
    return dets;
  })();
  function step1() {
    const tau = +$("t1").value; $("o-t1").textContent = tau.toFixed(2);
    const svg = $("svg1"); [...svg.querySelectorAll(":scope > :not(desc)")].forEach(n => n.remove());
    el("rect", { x: 115, y: 0, width: 150, height: 222, class: "road" }, svg);
    line(svg, 165, 0, 165, 222, "lane"); line(svg, 215, 0, 215, 222, "lane");
    el("rect", { x: 182, y: 192, width: 16, height: 28, rx: 3, class: "ego" }, svg);
    text(svg, 190, 236, "vehicle", { "text-anchor": "middle", class: "muted small" });
    const n = { ac: 0, aw: 0, wc: 0, rw: 0 };
    for (const d of ONE) {
      const acc = d.u <= tau, cls = d.wrong ? (acc ? "mk-acc-w" : "mk-rj-w") : (acc ? "mk-acc-c" : "mk-wh-c");
      n[d.wrong ? (acc ? "aw" : "rw") : (acc ? "ac" : "wc")]++;
      const g = mark(svg, d.x, d.y, 14, 26, cls, d.wrong, 3);
      g.setAttribute("transform", `rotate(${d.rot.toFixed(1)} ${d.x.toFixed(1)} ${d.y.toFixed(1)})`);
      text(svg, d.x + 12, d.y + 4, d.u.toFixed(2), { class: acc ? "small" : "small muted" });
    }
    // axis of the uncertainty value
    const x = lin(0, 1, 24, 356), y = 285;
    el("rect", { x: x(0), y: y - 22, width: Math.max(0, x(tau) - x(0)), height: 32, class: "band" }, svg);
    line(svg, x(0), y + 10, x(1), y + 10, "axis");
    for (const t of [0, 0.25, 0.5, 0.75, 1]) text(svg, x(t), y + 24, String(t), { "text-anchor": "middle", class: "muted small" });
    text(svg, x(1), y + 38, "uncertainty u", { "text-anchor": "end", class: "muted small" });
    ONE.forEach((d, i) => {
      const acc = d.u <= tau, cls = d.wrong ? (acc ? "mk-acc-w" : "mk-rj-w") : (acc ? "mk-acc-c" : "mk-wh-c");
      mark(svg, x(d.u), y - 14 + (i % 3) * 8, 8, 8, cls, d.wrong, 4);
    });
    line(svg, x(tau), y - 26, x(tau), y + 12, "tau");
    text(svg, Math.min(x(tau) + 4, 300), y - 28, "τ: accept u ≤ τ", { class: "tauT small" });
    tiles($("c1"), [
      { icon: ["mk-acc-c", false], value: n.ac, label: "accepted correct" },
      { icon: ["mk-acc-w", true], value: n.aw, label: "false acceptances" },
      { icon: ["mk-wh-c", false], value: n.wc, label: "withheld correct" },
      { icon: ["mk-rj-w", true], value: n.rw, label: "rejected wrong" }]);
  }

  // ---------- step 2: per-frame shares and FAP ----------
  const F2 = label(draws(202, 20), BASE);
  function step2() {
    const tau = +$("t2").value; $("o-t2").textContent = tau.toFixed(2);
    const svg = $("svg2"); [...svg.querySelectorAll(":scope > :not(desc)")].forEach(n => n.remove());
    const X0 = 40, W = 330, cw = W / F2.length, y = lin(0, 1, 124, 30);
    for (const t of [0, 0.5, 1]) { line(svg, X0, y(t), X0 + W, y(t), "gridline"); text(svg, X0 - 5, y(t) + 4, String(t), { "text-anchor": "end", class: "muted small" }); }
    text(svg, X0 - 34, 12, "per-frame share aƒ", { class: "muted small" });
    const r = evalAt(F2, tau);
    F2.forEach((fr, i) => {
      let acc = 0, wr = 0;
      for (const d of fr) if (d.u <= tau) { acc++; if (d.wrong) wr++; }
      const a = acc ? wr / acc : 0, cx = X0 + cw * (i + 0.5);
      if (a > 0) el("rect", { x: cx - cw * 0.32, y: y(a), width: cw * 0.64, height: y(0) - y(a), class: "bar" }, svg);
      if (!acc) text(svg, cx, y(0) - 3, "0", { "text-anchor": "middle", class: "muted small" });
      fr.slice().sort((p, q) => p.u - q.u).forEach((d, j) => {
        const ac = d.u <= tau, cls = d.wrong ? (ac ? "mk-acc-w" : "mk-rj-w") : (ac ? "mk-acc-c" : "mk-wh-c");
        mark(svg, cx, 140 + j * 13, 10, 10, cls, d.wrong);
      });
    });
    line(svg, X0, y(ALPHA), X0 + W, y(ALPHA), "limit");
    line(svg, X0, y(r.A), X0 + W, y(r.A), "fapline");
    const lo = y(Math.max(r.A, ALPHA)), hi = y(Math.min(r.A, ALPHA));
    text(svg, X0 + W, (r.A >= ALPHA ? lo : hi) - 3, "FAP = " + r.A.toFixed(3), { "text-anchor": "end", class: "small halo" });
    text(svg, X0 + W, (r.A >= ALPHA ? hi : lo) + 11, "α = " + ALPHA, { "text-anchor": "end", class: "muted small halo" });
    text(svg, X0 - 34, 146, "frame", { class: "muted small" });
    const met = r.A <= ALPHA;
    tiles($("c2"), [
      { value: r.A.toFixed(3), label: met ? "FAP, limit met" : "FAP, limit exceeded" },
      { value: pct(r.R), label: "retention" },
      { value: r.empty + " of " + F2.length, label: "frames without accepted detections (aƒ = 0)" }]);
  }

  // ---------- step 3: Learn then Test ----------
  const F3 = label(draws(303, 400), BASE);
  const C3 = CANDS.map(t => Object.assign({ t }, evalAt(F3, t)));
  function step3() {
    const delta = DELTAS[+$("d3").value]; state.delta = delta; $("o-d3").textContent = delta;
    let firstFail = -1;
    C3.forEach((c, i) => { c.p = HB.hbPvalue(c.S, c.n, ALPHA); c.pass = c.p <= delta; if (!c.pass && firstFail < 0) firstFail = i; });
    const last = (firstFail < 0 ? C3.length : firstFail) - 1;
    state.tauC = last >= 0 ? C3[last].t : null;
    const svg = $("svg3"); [...svg.querySelectorAll(":scope > :not(desc)")].forEach(n => n.remove());
    const x = lin(0.1, 0.7, 52, 366), ya = lin(0, 0.15, 98, 26), yp = log(1e-8, 1, 222, 136);
    // upper panel: estimated FAP; lower panel: p-value
    for (const t of [0, 0.05, 0.1, 0.15]) { line(svg, x(0.1), ya(t), x(0.7), ya(t), "gridline"); text(svg, 46, ya(t) + 4, String(t), { "text-anchor": "end", class: "muted small" }); }
    for (const t of [1e-8, 1e-4, 1]) { line(svg, x(0.1), yp(t), x(0.7), yp(t), "gridline"); text(svg, 46, yp(t) + 4, t === 1 ? "1" : "10" + sup(Math.round(Math.log10(t))), { "text-anchor": "end", class: "muted small" }); }
    text(svg, 4, 12, "estimated FAP Â", { class: "muted small" });
    text(svg, 4, 124, "HB p-value", { class: "muted small" });
    line(svg, x(0.1), ya(ALPHA), x(0.7), ya(ALPHA), "limit"); text(svg, x(0.7), ya(ALPHA) - 3, "α", { "text-anchor": "end", class: "muted" });
    line(svg, x(0.1), yp(delta), x(0.7), yp(delta), "limit"); text(svg, x(0.7), yp(delta) - 3, "δ", { "text-anchor": "end", class: "muted" });
    for (const t of [0.1, 0.3, 0.5, 0.7]) text(svg, x(t), 240, String(t), { "text-anchor": "middle", class: "muted small" });
    text(svg, x(0.7), 250, "candidate τ", { "text-anchor": "end", class: "muted small" });
    if (state.tauC !== null) { line(svg, x(state.tauC), 10, x(state.tauC), 226, "tau"); tauText(svg, x(state.tauC) + 4, 112, " = " + state.tauC.toFixed(3), { class: "tauT small halo" }); }
    C3.forEach((c, i) => {
      const after = firstFail >= 0 && i > firstFail, cl = after ? "dimmed" : "";
      const g = el("g", { class: cl }, svg);
      el("circle", { cx: x(c.t), cy: ya(Math.min(c.A, 0.15)), r: 2.2, fill: "var(--fg)" }, g);
      const py = yp(Math.max(c.p, 1e-8));
      if (c.pass) el("circle", { cx: x(c.t), cy: py, r: 3.6, fill: after ? "none" : "var(--threshold)", stroke: "var(--threshold)", "stroke-width": 1.4 }, g);
      else { const s = i === firstFail ? 4.5 : 3.2; el("path", { d: `M${x(c.t) - s},${py - s}L${x(c.t) + s},${py + s}M${x(c.t) + s},${py - s}L${x(c.t) - s},${py + s}`, stroke: "var(--wrong)", "stroke-width": 2, fill: "none" }, g); }
    });
    legend($("l3"), [
      { svg: '<svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="4" fill="var(--threshold)"/></svg>', label: "passes (p ≤ δ)" },
      { svg: '<svg width="12" height="12" aria-hidden="true"><path d="M2,2L10,10M10,2L2,10" stroke="var(--wrong)" stroke-width="2"/></svg>', label: "fails" },
      { svg: '<svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="4" fill="none" stroke="var(--threshold)" opacity=".4"/></svg>', label: "after the first failure: not selected" }]);
    const s = last >= 0 ? C3[last] : null;
    tiles($("c3"), s ? [
      { value: s.t.toFixed(3), label: "selected threshold" },
      { value: s.A.toFixed(4), label: "Â on the selection frames" },
      { value: pct(s.R), label: "retention in c" }]
      : [{ value: "none", label: "no threshold selected: the lowest candidate fails" }]);
    step4();
  }

  // ---------- step 4: condition of use ----------
  const BIGC = draws(404, 20000), BIGU = draws(505, 20000);
  const LC = label(BIGC, BASE);
  const SL = { sep: ["s-sep", v => v.toFixed(2)], share: ["s-share", v => v.toFixed(2)], shift: ["s-shift", v => (v > 0 ? "+" : "") + v.toFixed(3)], conc: ["s-conc", v => v.toFixed(2)] };
  let LU = null;
  function syncSliders() {
    for (const k in SL) { $(SL[k][0]).value = state.P[k]; $("o-" + SL[k][0].slice(2)).textContent = SL[k][1](state.P[k]); }
    $("s5").value = state.P.share; $("o-s5").textContent = state.P.share.toFixed(2);
  }
  function density(svg, x, y, p, cls, solid) {
    const pts = { c: [], w: [] };
    for (let i = 0; i <= 120; i++) {
      const u = i / 120, g = m => Math.exp(-0.5 * ((u - m) / SD) ** 2) / (SD * Math.sqrt(2 * Math.PI));
      pts.c.push([x(u), y((1 - p.share) * g(MU + p.shift))]); pts.w.push([x(u), y(p.share * g(MU + p.shift + p.sep * SD))]);
    }
    for (const k of ["c", "w"]) {
      const d = "M" + pts[k].map(q => q[0].toFixed(1) + "," + q[1].toFixed(1)).join("L");
      const col = k === "c" ? "var(--correct)" : "var(--wrong)";
      if (solid) el("path", { d: d + `L${x(1)},${y(0)}L${x(0)},${y(0)}Z`, fill: col, opacity: 0.16 }, svg);
      el("path", { d, stroke: col, class: solid ? "curve-u" : "curve-c", fill: "none", "stroke-dasharray": solid ? (k === "w" ? "7 2" : null) : "2 3" }, svg);
    }
  }
  function step4() {
    syncSliders();
    LU = label(BIGU, state.P);
    const svg = $("svg4"); [...svg.querySelectorAll(":scope > :not(desc)")].forEach(n => n.remove());
    const x = lin(0, 1, 20, 366), y = lin(0, 3.6, 180, 12);
    line(svg, x(0), y(0), x(1), y(0), "axis");
    for (const t of [0, 0.25, 0.5, 0.75, 1]) text(svg, x(t), 196, String(t), { "text-anchor": "middle", class: "muted small" });
    text(svg, x(1), 208, "uncertainty u", { "text-anchor": "end", class: "muted small" });
    const tau = state.tauC;
    if (tau !== null) el("rect", { x: x(0), y: 12, width: x(tau) - x(0), height: 168, class: "band" }, svg);
    density(svg, x, y, BASE, "", false);
    density(svg, x, y, state.P, "", true);
    if (tau !== null) { line(svg, x(tau), 8, x(tau), 182, "tau"); tauText(svg, x(tau) + 4, 20, " = " + tau.toFixed(3) + " (from c)", { class: "tauT small halo" }); }
    legend($("l4"), [
      { svg: '<svg width="22" height="10" aria-hidden="true"><path d="M1,5H21" stroke="var(--correct)" stroke-width="2"/></svg>', label: "correct in c′" },
      { svg: '<svg width="22" height="10" aria-hidden="true"><path d="M1,5H21" stroke="var(--wrong)" stroke-width="2" stroke-dasharray="7 2"/></svg>', label: "wrong in c′" },
      { svg: '<svg width="22" height="10" aria-hidden="true"><path d="M1,5H21" stroke="var(--axis)" stroke-width="1.4" stroke-dasharray="2 3"/></svg>', label: "the same in c (dotted)" }]);
    const tb = $("tab4"); tb.textContent = "";
    const add = (cells, head) => { const tr = document.createElement("tr"); cells.forEach((c, i) => { const t = document.createElement(head || i === 0 ? "th" : "td"); if (i === 0) { t.className = "l"; if (!head) t.scope = "row"; } t.textContent = c; tr.appendChild(t); }); tb.appendChild(tr); };
    add(["at the threshold from c", "condition c", "condition c′"], true);
    add(["AUROC", auroc(BASE).toFixed(3), auroc(state.P).toFixed(3)]);
    if (tau === null) { $("m4").textContent = "No threshold was selected in step 3, so there is nothing to transfer."; step5(); return; }
    const rc = evalAt(LC, tau), ru = evalAt(LU, tau);
    state.fapU = ru.A;
    add(["FAP (α = " + ALPHA + ")", rc.A.toFixed(4), ru.A.toFixed(4)]);
    add(["retention", pct(rc.R), pct(ru.R)]);
    const dAU = Math.abs(auroc(state.P) - auroc(BASE)) > 5e-4, dF = ru.A - rc.A;
    const fapTxt = ru.A > ALPHA ? "exceeds the limit in c′" : "stays within the limit in c′";
    $("m4").textContent = (dAU ? "AUROC changed, " : "AUROC is unchanged, ") + "and the FAP at the transferred threshold " +
      (Math.abs(dF) < 5e-4 ? "is unchanged" : dF > 0 ? "rose" : "fell") + "; it " + fapTxt + ".";
    step5();
  }

  // ---------- step 5: test in c' ----------
  const TEST = draws(606, 5000);
  const nOf = v => Math.min(5000, Math.round(Math.pow(10, 1 + 2.7 * v / 1000)));
  function interval(F, n, tau) {
    const r = evalAt(F, tau, n), d2 = state.delta / 2;
    const U = HB.hbUpper(r.S, r.n, d2), L = HB.hbLower(r.S, r.n, d2);
    return { A: r.A, L, U, o: HB.outcome(L, U, ALPHA) };
  }
  function step5() {
    const n = nOf(+$("n5").value); $("o-n5").textContent = int(n);
    const svg = $("svg5"); [...svg.querySelectorAll(":scope > :not(desc)")].forEach(k => k.remove());
    const chips = $("chips5"); chips.textContent = "";
    if (state.tauC === null) { badge($("out5"), "no threshold selected"); return; }
    const F = label(TEST, state.P), r = interval(F, n, state.tauC);
    badge($("out5"), r.o);
    const lo = 1e-4, x = log(lo, 1, 30, 366), y = 50;
    for (const t of UI.decades(lo, 1)) { line(svg, x(t), 22, x(t), 72, "gridline"); text(svg, x(t), 88, t === 1 ? "1" : "10" + sup(Math.round(Math.log10(t))), { "text-anchor": "middle", class: "muted small" }); }
    text(svg, x(1), 104, "FAP in c′ (log scale)", { "text-anchor": "end", class: "muted small" });
    line(svg, x(ALPHA), 14, x(ALPHA), 78, "limit"); text(svg, x(ALPHA) + 3, 14, "α", { class: "muted" });
    const col = { A: "var(--c-A)", N: "var(--c-N)", Q: "var(--axis)" }[OUT[r.o]];
    el("rect", { x: x(Math.max(r.L, lo)), y: y - 6, width: Math.max(2, x(r.U) - x(Math.max(r.L, lo))), height: 12, rx: 6, fill: col, opacity: 0.85 }, svg);
    text(svg, x(Math.max(r.L, lo)), y - 10, "L", { "text-anchor": "middle", class: "small" });
    text(svg, x(r.U), y - 10, "U", { "text-anchor": "middle", class: "small" });
    if (r.A > 0) el("circle", { cx: x(r.A), cy: y, r: 3, fill: "var(--bg)", stroke: "var(--fg)", "stroke-width": 1.5 }, svg);
    if (state.fapU > 0) { const fx = x(Math.max(state.fapU, lo)); el("path", { d: `M${fx},${y + 9}l-5,9h10z`, fill: "var(--fg)" }, svg); }
    const leg = document.createElement("p"); leg.className = "note"; leg.style.margin = "0";
    leg.textContent = `n = ${int(n)}: Â = ${fmt(r.A, 3)}, interval [${fmt(r.L, 3)}, ${fmt(r.U, 3)}] at confidence ${1 - state.delta}. ` +
      `Triangle: FAP of the schematic model in c′ (${fmt(state.fapU, 3)}), which a real test does not know.`;
    chips.appendChild(leg);
    for (const m of [30, 100, 300, 1000, 5000]) {
      const o = interval(F, m, state.tauC).o, s = document.createElement("span");
      s.className = "outcome " + OUT[o]; s.textContent = "n = " + int(m) + ": " + o; chips.appendChild(s);
    }
  }

  // ---------- step 6: independent units ----------
  let UNITS = null;
  const aOf = v => Math.pow(10, -4 + 3 * v / 300);
  function step6() {
    const unit = document.querySelector("input[name=unit6]:checked").value, alpha = aOf(+$("a6").value), delta = state.delta;
    $("o-a6").textContent = fmt(alpha, 2);
    // schematic grid: five recorded sequences of ten frames
    const g = $("svg6a"); [...g.querySelectorAll(":scope > :not(desc)")].forEach(k => k.remove());
    for (let s = 0; s < 5; s++) {
      const yy = 6 + s * 16;
      if (unit !== "frame") el("rect", { x: 96, y: yy - 1, width: 202, height: 14, rx: 7, fill: "none", stroke: "var(--threshold)", "stroke-width": 1.6 }, g);
      text(g, 90, yy + 10, "sequence " + (s + 1), { "text-anchor": "end", class: "muted small" });
      for (let f = 0; f < 10; f++) el("rect", { x: 100 + f * 20, y: yy + 1, width: 14, height: 10, rx: 2, fill: "var(--shade)", stroke: unit === "frame" ? "var(--threshold)" : "var(--line)", "stroke-width": unit === "frame" ? 1.4 : 1 }, g);
    }
    text(g, 306, 46, "units counted:", { class: "muted small" });
    text(g, 306, 62, unit === "frame" ? "50 frames" : "5 sequences", { class: "tauT" });
    // zero-failure bound against alpha
    const svg = $("svg6"); [...svg.querySelectorAll(":scope > :not(desc)")].forEach(k => k.remove());
    const x = log(1e-4, 0.1, 50, 330), y = log(1, 1e5, 222, 12);
    for (const t of UI.decades(1e-4, 0.1)) { line(svg, x(t), 12, x(t), 222, "gridline"); text(svg, x(t), 238, "10" + sup(Math.round(Math.log10(t))), { "text-anchor": "middle", class: "muted small" }); }
    for (const t of UI.decades(1, 1e5)) { line(svg, 50, y(t), 330, y(t), "gridline"); text(svg, 45, y(t) + 4, t >= 1000 ? "10" + sup(Math.round(Math.log10(t))) : String(t), { "text-anchor": "end", class: "muted small" }); }
    text(svg, 330, 250, "limit α", { "text-anchor": "end", class: "muted small" });
    text(svg, 4, 8, "minimum independent units", { class: "muted small" });
    const curve = dp => { const p = []; for (let i = 0; i <= 60; i++) { const a = Math.pow(10, -4 + 3 * i / 60); p.push(x(a).toFixed(1) + "," + y(HB.zeroFailureBound(a, dp)).toFixed(1)); } return "M" + p.join("L"); };
    el("path", { d: curve(delta), fill: "none", stroke: "var(--axis)", "stroke-width": 1.5, "stroke-dasharray": "5 3" }, svg);
    el("path", { d: curve(delta / 2), fill: "none", stroke: "var(--threshold)", "stroke-width": 2 }, svg);
    const nT = Math.ceil(HB.zeroFailureBound(alpha, delta / 2) - 1e-9), nS = Math.ceil(HB.zeroFailureBound(alpha, delta) - 1e-9);
    line(svg, x(alpha), 12, x(alpha), 222, "tau", { "stroke-width": 1, opacity: 0.5 });
    el("circle", { cx: x(alpha), cy: y(nT), r: 4.5, fill: "var(--threshold)" }, svg);
    text(svg, x(alpha) + (x(alpha) > 240 ? -7 : 7), y(nT) - 6, int(nT), { class: "tauT", "text-anchor": x(alpha) > 240 ? "end" : "start" });
    // case study: recorded test units, split 0
    let rows = [];
    if (UNITS) {
      rows = UNITS.filter(u => u.split === 0 && u.part === "test" && u.unit === unit);
      for (const u of rows) {
        const ok = u.n >= nT, yy = y(u.n);
        const m = el("path", { d: `M${342},${yy}l5,-5l5,5l-5,5z`, fill: ok ? "var(--c-A)" : "none", stroke: "var(--fg)", "stroke-width": 1 }, svg);
        el("title", {}, m).textContent = `${u.pair}, ${u.condition}: ${int(u.n)} ${u.unit_name} (case study, test part, split 0)`;
      }
      text(svg, 347, 8, "case", { "text-anchor": "middle", class: "muted small" });
    }
    legend($("l6"), [
      { svg: '<svg width="22" height="10" aria-hidden="true"><path d="M1,5H21" stroke="var(--threshold)" stroke-width="2"/></svg>', label: "testing, δ′ = δ/2" },
      { svg: '<svg width="22" height="10" aria-hidden="true"><path d="M1,5H21" stroke="var(--axis)" stroke-width="1.5" stroke-dasharray="5 3"/></svg>', label: "selecting, δ′ = δ" },
      { svg: '<svg width="12" height="12" aria-hidden="true"><path d="M1,6l5,-5l5,5l-5,5z" fill="none" stroke="var(--fg)"/></svg>', label: "case study test units (filled: at least the minimum)" }]);
    const word = unit === "frame" ? "frames" : "recorded sequences";
    let msg = `At α = ${fmt(alpha, 2)} and δ = ${delta}, testing needs at least ${int(nT)} independent units per condition and selecting at least ${int(nS)}, all without a false acceptance. Counted in ${word}`;
    if (rows.length) {
      const ns = rows.map(r => r.n), k = rows.filter(r => r.n >= nT).length;
      msg += `, the test parts of the case study hold ${int(Math.min(...ns))} to ${int(Math.max(...ns))} units; ${k} of ${rows.length} reach the minimum.`;
    } else msg += ".";
    if (unit !== "frame") msg += " This is the number of sequences to record per condition before the test can show the limit to be met.";
    $("m6").textContent = msg;
    const tb = $("tab6"); tb.textContent = "";
    if (rows.length) {
      const h = document.createElement("tr"); ["condition", "test units", "≥ " + int(nT) + "?"].forEach((c, i) => { const t = document.createElement("th"); t.textContent = c; if (!i) t.className = "l"; h.appendChild(t); }); tb.appendChild(h);
      for (const u of rows) { const tr = document.createElement("tr"); [`${u.pair}: ${u.condition}`, int(u.n) + " " + u.unit_name, u.n >= nT ? "yes" : "no"].forEach((c, i) => { const t = document.createElement(i ? "td" : "th"); if (!i) { t.className = "l"; t.scope = "row"; } t.textContent = c; tr.appendChild(t); }); tb.appendChild(tr); }
    }
  }

  // ---------- step 7: outcomes and measures (after paper, Table 5) ----------
  const MEAS = [
    ["applicable", "The test shows, at error probability at most δ/2 if the units are independent, that the transferred threshold meets the target in c′.",
      ["Use the threshold in c′ if the share of annotated objects that reach the motion planner also meets a second target on missed objects. Report the retention and the number of independent units with the outcome."]],
    ["not applicable", "The test shows, at error probability at most δ/2 if the units are independent, that the transferred threshold does not meet the target in c′.",
      ["Detector supplier: select a threshold in c′ and provide a run-time signal for c′, or use one common threshold that passes the selection in each condition.",
        "Vehicle manufacturer: restrict the operational design domain or the functionality, or add a measure in tracking, fusion or motion planning."]],
    ["not determined", "No statement: the data of c′ do not suffice, or the FAP lies close to α. The outcome can hide an exceeded limit.",
      ["Record further independent units in c′ (step 6 gives the minimum) and treat c′ as not verified until then."]],
    ["no threshold selected", "The lowest candidate threshold already fails in c with the available data, so there is nothing to transfer.",
      ["Record further independent units in c, or request a reallocation of α at vehicle level."]]];
  function step7(sel, focus) {
    const tabs = $("tabs7"); tabs.textContent = "";
    MEAS.forEach((m, i) => {
      const b = document.createElement("button"); b.type = "button"; b.setAttribute("role", "tab"); b.id = "tab7-" + i;
      b.className = "outcome " + OUT[m[0]]; b.textContent = m[0]; b.setAttribute("aria-selected", i === sel); b.tabIndex = i === sel ? 0 : -1;
      b.setAttribute("aria-controls", "panel7");
      b.addEventListener("click", () => step7(i, true));
      b.addEventListener("keydown", e => { const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key]; if (d) { e.preventDefault(); e.stopPropagation(); step7((i + d + 4) % 4, true); } });
      tabs.appendChild(b); if (i === sel && focus) b.focus();
    });
    const p = $("panel7"); p.setAttribute("aria-labelledby", "tab7-" + sel); p.textContent = "";
    const dl = document.createElement("dl");
    const add = (t, d) => { const a = document.createElement("dt"), b = document.createElement("dd"); a.textContent = t; b.textContent = d; dl.append(a, b); };
    add("Meaning for the performance target", MEAS[sel][1]);
    MEAS[sel][2].forEach((d, i) => add(i ? "" : "Measure that follows", d));
    p.appendChild(dl);
  }

  // ---------- navigation ----------
  const CH = [...document.querySelectorAll(".wt-ch")];
  let cur = 0;
  const ol = $("wt-steps");
  CH.forEach((c, i) => {
    const li = document.createElement("li"), b = document.createElement("button");
    b.type = "button"; b.innerHTML = `${i + 1}<span class="wt-st">${c.dataset.short}</span>`; b.setAttribute("aria-label", `Step ${i + 1}: ${c.querySelector("h2").textContent}`);
    b.addEventListener("click", () => go(i)); li.appendChild(b); ol.appendChild(li);
    c.querySelector("h2").tabIndex = -1;
  });
  function go(i) {
    i = Math.max(0, Math.min(CH.length - 1, i));
    CH[i].scrollIntoView({ block: "start" });
    CH[i].querySelector("h2").focus({ preventScroll: true });
    setCur(i);
  }
  function setCur(i) {
    cur = i;
    [...ol.querySelectorAll("button")].forEach((b, j) => { if (j === i) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current"); b.classList.toggle("done", j < i); });
    $("wt-fill").style.width = ((i + 1) / CH.length * 100) + "%";
    $("wt-prev").disabled = i === 0; $("wt-next").disabled = i === CH.length - 1;
    $("wt-live").textContent = `Step ${i + 1} of ${CH.length}`;
  }
  function onScroll() {
    let i = 0;
    const lim = window.innerHeight * 0.4;
    CH.forEach((c, j) => { if (c.getBoundingClientRect().top < lim) i = j; });
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) i = CH.length - 1;
    if (i !== cur) setCur(i);
  }
  $("wt-prev").addEventListener("click", () => go(cur - 1));
  $("wt-next").addEventListener("click", () => go(cur + 1));
  document.addEventListener("keydown", e => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const t = e.target, tag = t && t.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || (t && t.getAttribute && t.getAttribute("role") === "tab")) return;
    if (e.key === "ArrowRight") { e.preventDefault(); go(cur + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(cur - 1); }
  });
  window.addEventListener("scroll", onScroll, { passive: true });

  // ---------- wiring ----------
  $("t1").addEventListener("input", step1);
  $("t2").addEventListener("input", step2);
  $("b2").addEventListener("click", () => { $("t2").value = 0; step2(); });
  $("d3").min = 0; $("d3").max = DELTAS.length - 1; $("d3").value = DELTAS.indexOf(0.05);
  $("d3").addEventListener("input", () => { step3(); step6(); });
  for (const k in SL) $(SL[k][0]).addEventListener("input", e => { state.P[k] = +e.target.value; step4(); });
  $("s5").addEventListener("input", e => { state.P.share = +e.target.value; step4(); });
  $("b4").addEventListener("click", () => { state.P = Object.assign({}, BASE); step4(); });
  $("n5").addEventListener("input", step5);
  $("a6").addEventListener("input", step6);
  document.querySelectorAll("input[name=unit6]").forEach(r => r.addEventListener("change", step6));

  step1(); step2(); step3(); step6(); step7(0); setCur(0); onScroll();
  fetch("data/units.json").then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(d => {
    UNITS = d.units; step6();
  }).catch(e => { $("st6").textContent = "Could not read data/units.json (" + e.message + "); the case study markers need the page to be opened over HTTP."; });

  // self-check of the schematic model: the share of wrong detections is kept when the spread over frames changes
  if (typeof console !== "undefined") {
    const share = p => { let w = 0, a = 0; for (const f of label(BIGC.slice(0, 4000), p)) for (const d of f) { a++; if (d.wrong) w++; } return w / a; };
    const s0 = share(BASE), s1 = share(Object.assign({}, BASE, { conc: 1 }));
    console.assert(Math.abs(s0 - s1) < 0.02, "spread over frames changed the share of wrong detections", s0, s1);
  }
})();

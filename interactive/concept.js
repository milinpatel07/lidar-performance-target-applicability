// Schematic simulator of the four changes in the detections (Sect. 3.4 of the paper). Not data.
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { el, text, lin, fmt } = UI;
  const SD = 0.1, BASE = 0.3, TAU = 0.4, FRAMES = 500, KMAX = 8, SEED = 20261023;
  const SEL = { share: 0.3, sep: 2, shift: 0, conc: 0 };

  // standard normal distribution function (Abramowitz and Stegun 7.1.26)
  function Phi(x) {
    const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x / 2);
    return x >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
  }
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  // fixed simulated set: frame sizes, one uniform and one standard normal value per detection
  const SET = (function () {
    const r = mulberry32(SEED), frames = [];
    for (let f = 0; f < FRAMES; f++) {
      const k = 1 + Math.floor(r() * KMAX), dets = [];
      for (let i = 0; i < k; i++) {
        const u1 = Math.max(r(), 1e-12), u2 = r();
        dets.push({ w: r(), z: Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) });
      }
      frames.push(dets);
    }
    return frames;
  })();

  function evaluate(p) {
    const muC = BASE + p.shift, muW = muC + p.sep * SD;
    const accC = Phi((TAU - muC) / SD), accW = Phi((TAU - muW) / SD);
    const pooled = p.share * accW / (p.share * accW + (1 - p.share) * accC);
    const auroc = Phi(p.sep / Math.SQRT2);
    // frame weights: frames with few detections get a larger probability of wrong detections as conc grows
    const gamma = 3 * p.conc;
    const wts = SET.map(d => Math.pow(d.length, -gamma));
    const nDet = SET.reduce((s, d) => s + d.length, 0);
    const mean = SET.reduce((s, d, i) => s + d.length * wts[i], 0) / nDet;
    let sumA = 0, nWrong = 0, acc = 0, accWrong = 0;
    SET.forEach((dets, i) => {
      const pf = Math.min(1, p.share * wts[i] / mean);
      let a = 0, fa = 0;
      for (const d of dets) {
        const wrong = d.w < pf;
        if (wrong) nWrong++;
        const u = (wrong ? muW : muC) + SD * d.z;
        if (u <= TAU) { a++; if (wrong) fa++; }
      }
      acc += a; accWrong += fa;
      sumA += a ? fa / a : 0;
    });
    return { muC, muW, auroc, pooled, retention: accC, fap: sumA / FRAMES, simShare: nWrong / nDet, simPooled: acc ? accWrong / acc : 0 };
  }

  function density(svg, p, r) {
    [...svg.querySelectorAll("g")].forEach(n => n.remove());
    const g = el("g", {}, svg);
    const W = 400, H = 200, M = { l: 10, r: 10, t: 10, b: 30 };
    const x = lin(0, 1, M.l, W - M.r);
    const peak = 1 / (SD * Math.sqrt(2 * Math.PI));
    const y = lin(0, peak * 0.95, H - M.b, M.t);
    const pdf = (u, mu) => Math.exp(-0.5 * Math.pow((u - mu) / SD, 2)) / (SD * Math.sqrt(2 * Math.PI));
    const pts = (mu, wgt, upto) => {
      const out = [];
      for (let i = 0; i <= 200; i++) { const u = i / 200; if (upto !== undefined && u > upto) break; out.push([u, wgt * pdf(u, mu)]); }
      return out;
    };
    // accepted wrong detections: area under the wrong curve left of tau
    const aw = pts(r.muW, p.share, TAU);
    const area = "M" + x(0) + "," + y(0) + aw.map(q => "L" + x(q[0]).toFixed(1) + "," + y(q[1]).toFixed(1)).join("") + "L" + x(TAU) + "," + y(pdf(TAU, r.muW) * p.share).toFixed(1) + "L" + x(TAU) + "," + y(0) + "Z";
    el("path", { d: area, fill: "var(--wrong)", opacity: 0.3 }, g);
    const line = (arr) => arr.map((q, i) => (i ? "L" : "M") + x(q[0]).toFixed(1) + "," + y(q[1]).toFixed(1)).join("");
    el("path", { d: line(pts(r.muC, 1 - p.share)), fill: "none", stroke: "var(--correct)", "stroke-width": 2 }, g);
    el("path", { d: line(pts(r.muW, p.share)), fill: "none", stroke: "var(--wrong)", "stroke-width": 2, "stroke-dasharray": "6 3" }, g);
    el("line", { x1: x(TAU), x2: x(TAU), y1: M.t, y2: H - M.b, stroke: "var(--threshold)", "stroke-width": 2 }, g);
    text(g, x(TAU) + 4, M.t + 10, "τ (transferred)", {});
    el("line", { x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: "axis" }, g);
    text(g, M.l, H - 10, "accepted ←", { class: "muted" });
    text(g, W - M.r, H - 10, "→ rejected", { class: "muted", "text-anchor": "end" });
    text(g, W / 2, H - 10, "indicator value u", { "text-anchor": "middle" });
  }

  function legend() {
    const lg = $("legend");
    const item = (fn, label) => { const s = document.createElement("span"); const svg = el("svg", { width: 26, height: 12, "aria-hidden": "true" }); fn(svg); s.appendChild(svg); s.appendChild(document.createTextNode(label)); lg.appendChild(s); };
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--correct)", "stroke-width": 2 }, s), "correct detections");
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--wrong)", "stroke-width": 2, "stroke-dasharray": "6 3" }, s), "wrong detections");
    item(s => el("rect", { x: 4, y: 1, width: 18, height: 10, fill: "var(--wrong)", opacity: 0.3 }, s), "false acceptances (accepted wrong detections)");
    item(s => el("line", { x1: 13, x2: 13, y1: 0, y2: 12, stroke: "var(--threshold)", "stroke-width": 2 }, s), "transferred threshold τ");
    const n = document.createElement("span"); n.className = "note"; n.textContent = "Curve heights are scaled by the share of each kind of detection."; lg.appendChild(n);
  }

  function params() {
    return { share: Number($("s-share").value), sep: Number($("s-sep").value), shift: Number($("s-shift").value), conc: Number($("s-conc").value) };
  }

  function render() {
    const pu = params();
    $("o-share").textContent = pu.share.toFixed(2); $("o-sep").textContent = pu.sep.toFixed(2);
    $("o-shift").textContent = (pu.shift >= 0 ? "+" : "") + pu.shift.toFixed(3); $("o-conc").textContent = pu.conc.toFixed(2);
    const rs = evaluate(SEL), ru = evaluate(pu);
    density($("d-sel"), SEL, rs); density($("d-use"), pu, ru);
    const t = $("res"); t.textContent = "";
    const h = t.insertRow(); ["schematic quantity", "condition of selection", "condition of use", "depends on"].forEach((s, i) => { const th = document.createElement("th"); th.textContent = s; if (!i || i === 3) th.className = "l"; h.appendChild(th); });
    const add = (k, a, b, dep) => { const r = t.insertRow(); const c = r.insertCell(); c.className = "l"; c.textContent = k; r.insertCell().textContent = a; r.insertCell().textContent = b; const d = r.insertCell(); d.className = "l"; d.textContent = dep; };
    add("AUROC (from the distributions)", fmt(rs.auroc, 3), fmt(ru.auroc, 3), "separation only");
    add("share of wrong detections (simulated set)", fmt(rs.simShare, 3), fmt(ru.simShare, 3), "share");
    add("retention: share of correct detections accepted", fmt(rs.retention, 3), fmt(ru.retention, 3), "shift");
    add("pooled share of wrong among accepted (from the distributions)", fmt(rs.pooled, 3), fmt(ru.pooled, 3), "separation, share, shift");
    add("FAP: mean over frames of the per-frame share (simulated set)", fmt(rs.fap, 3), fmt(ru.fap, 3), "separation, share, shift, spread over frames");
    const dA = Math.abs(ru.auroc - rs.auroc) < 5e-4, dF = ru.fap - rs.fap;
    $("msg").textContent = (dA ? "AUROC is unchanged" : "AUROC changed") + `; the schematic FAP at the transferred threshold ${Math.abs(dF) < 5e-4 ? "is unchanged" : (dF > 0 ? "rose" : "fell") + " by " + fmt(Math.abs(dF), 2)}.`;
  }

  ["s-share", "s-sep", "s-shift", "s-conc"].forEach(id => $(id).addEventListener("input", render));
  $("reset").addEventListener("click", () => { $("s-share").value = SEL.share; $("s-sep").value = SEL.sep; $("s-shift").value = SEL.shift; $("s-conc").value = SEL.conc; render(); });
  legend();
  render();
})();

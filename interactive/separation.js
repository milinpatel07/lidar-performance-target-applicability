// Interactive version of Fig. 5 of the paper: ROC curves and estimated FAP against the threshold.
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { el, text, clear, lin, log, fmt, tip } = UI;
  const W = 400, H = 380, M = { l: 52, r: 12, t: 14, b: 44 };
  const FMIN = 1e-3, FMAX = 1;
  const IND = { u_s: "spatial indicator u_s", u_e: "existence indicator u_e" };
  // statements of Sect. 5.2 of the paper on each transfer (no numbers; the numbers on this page are read or computed)
  const READING = {
    kitti_distance: "Paper, Sect. 5.2: with distance, separation weakened and wrong detections became more frequent, so AUROC shows this change.",
    nuscenes_weather: "Paper, Sect. 5.2: in rain the AUROC of u_e did not decrease, and the transferred threshold selected at 0.1† marked nearly the same operating point on both curves, yet the FAP in rain exceeded the limit. More wrong detections and a different spread over frames accompanied this; AUROC shows neither.",
    dataset_detector: "Paper, Sect. 5.2: u_s took lower values on KITTI, so the threshold selected on nuScenes lay high on the KITTI scale and accepted a larger share of the KITTI wrong detections, although u_s separated correct from wrong detections better on KITTI. The values shifted; AUROC does not change under a shift that keeps the order of the values."
  };
  let data = null, panel = null, highlight = "0.1";

  function auroc(roc) {
    const p = roc.slice().sort((a, b) => a[0] - b[0]);
    let s = 0;
    for (let i = 1; i < p.length; i++) s += (p[i][0] - p[i - 1][0]) * (p[i][1] + p[i - 1][1]) / 2;
    return s;
  }
  function nearest(fap, tau) {
    let best = fap[0];
    for (const pt of fap) if (Math.abs(pt[0] - tau) < Math.abs(best[0] - tau)) best = pt;
    return best;
  }
  const styleOf = (c) => c === panel.condition_of_selection ? { dash: null, name: c + " (condition of selection)" } : { dash: "6 4", name: c + " (condition of use)" };

  function axes(g, x, y, xlab, ylab, xt, yt, ylog) {
    for (const t of yt) {
      el("line", { x1: M.l, x2: W - M.r, y1: y(t), y2: y(t), class: "gridline" }, g);
      text(g, M.l - 4, y(t) + 4, ylog ? fmt(t) : t.toFixed(1), { "text-anchor": "end", class: "muted" });
    }
    for (const t of xt) text(g, x(t), H - M.b + 15, t.toFixed(2).replace(/0$/, ""), { "text-anchor": "middle", class: "muted" });
    el("line", { x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: "axis" }, g);
    el("line", { x1: M.l, x2: M.l, y1: M.t, y2: H - M.b, class: "axis" }, g);
    text(g, (M.l + W - M.r) / 2, H - 8, xlab, { "text-anchor": "middle" });
    const cy = (M.t + H - M.b) / 2;
    text(g, 12, cy, ylab, { "text-anchor": "middle", transform: `rotate(-90 12 ${cy})` });
  }

  function opMarker(g, op, x, y, which, cond) {
    const isHi = which === highlight;
    const a = { stroke: "var(--ink)", "stroke-width": isHi ? 2.2 : 1.2, fill: which === "0.1" ? "var(--bg)" : "var(--ink)", opacity: isHi ? 1 : 0.55 };
    const cx = x(op.withheld), cy = y(op.rejected);
    const m = which === "0.1" ? el("rect", Object.assign({ x: cx - 5, y: cy - 5, width: 10, height: 10 }, a), g) : el("circle", Object.assign({ cx, cy, r: 5 }, a), g);
    const lines = [`${cond}, τ = ${fmt(op.tau)} (selected at ${which === "0.1" ? "0.1†" : "10⁻²"})`, `correct detections withheld ${fmt(op.withheld, 3)}`, `wrong detections rejected ${fmt(op.rejected, 3)}`, `source line ${op.source_row}`];
    m.addEventListener("pointermove", e => tip(lines, e)); m.addEventListener("pointerleave", () => tip(null));
  }

  function drawRoc() {
    const svg = $("roc"); [...svg.querySelectorAll("g")].forEach(n => n.remove());
    const g = el("g", {}, svg);
    const x = lin(0, 1, M.l, W - M.r), y = lin(0, 1.02, H - M.b, M.t);
    axes(g, x, y, "correct detections withheld", "wrong detections rejected", [0, 0.5, 1], [0, 0.5, 1], false);
    el("line", { x1: x(0), y1: y(0), x2: x(1), y2: y(1), stroke: "var(--grid)", "stroke-dasharray": "2 3" }, g);
    for (const c of [panel.condition_of_selection, panel.condition_of_use]) {
      const d = panel.conditions[c], s = styleOf(c);
      const pts = d.roc.slice().reverse().map(p => x(p[0]).toFixed(1) + "," + y(p[1]).toFixed(1)).join(" ");
      el("polyline", { points: pts, fill: "none", stroke: "var(--ink)", "stroke-width": 2, "stroke-dasharray": s.dash }, g);
    }
    for (const c of [panel.condition_of_selection, panel.condition_of_use]) {
      for (const op of panel.conditions[c].operating_points) {
        const which = Math.abs(op.tau - panel.tau_selected["0.1"]) < 1e-12 ? "0.1" : "0.01";
        opMarker(g, op, x, y, which, c);
      }
    }
  }

  function drawFap(tau) {
    const svg = $("fap"); [...svg.querySelectorAll("g")].forEach(n => n.remove());
    const g = el("g", {}, svg);
    const tmax = Math.max(...Object.values(panel.conditions).map(d => d.fap[d.fap.length - 1][0]));
    const x = lin(0, tmax, M.l, W - M.r), y = log(FMIN, FMAX, H - M.b, M.t);
    const xt = [0, tmax / 3, 2 * tmax / 3, tmax].map(v => +v.toPrecision(2));
    axes(g, x, y, "threshold τ on " + panel.indicator, "estimated FAP (log scale)", xt, [1e-3, 1e-2, 1e-1, 1], true);
    for (const a of [0.1, 0.01]) {
      el("line", { x1: M.l, x2: W - M.r, y1: y(a), y2: y(a), stroke: "var(--limit)", "stroke-dasharray": "2 3" }, g);
      text(g, W - M.r - 2, y(a) - 3, a === 0.1 ? "0.1†" : "10⁻²", { "text-anchor": "end", class: "muted" });
    }
    const t01 = panel.tau_selected["0.1"];
    el("line", { x1: x(t01), x2: x(t01), y1: M.t, y2: H - M.b, stroke: "var(--ink)", "stroke-width": 1, opacity: 0.6 }, g);
    const conds = [panel.condition_of_selection, panel.condition_of_use];
    conds.forEach((c, k) => {
      const d = panel.conditions[c], s = styleOf(c);
      // break the line where the estimate is 0 (no point on a log axis)
      let path = "", pen = false;
      for (const p of d.fap) {
        if (p[1] <= 0) { pen = false; continue; }
        path += (pen ? "L" : "M") + x(p[0]).toFixed(1) + "," + y(p[1]).toFixed(1);
        pen = true;
      }
      el("path", { d: path, fill: "none", stroke: "var(--ink)", "stroke-width": 2, "stroke-dasharray": s.dash }, g);
      const iv = d.interval;
      if (iv) {
        const bx = x(t01) + (k ? 7 : -7);
        el("line", { x1: bx, x2: bx, y1: y(Math.max(iv.L, FMIN)), y2: y(iv.U), stroke: "var(--threshold)", "stroke-width": 2.5 }, g);
        const m = el("rect", { x: bx - 4, y: y(iv.A_hat) - 4, width: 8, height: 8, fill: "var(--bg)", stroke: "var(--threshold)", "stroke-width": 2 }, g);
        const lines = [`${c}: interval at τ selected at 0.1†`, `L ${fmt(iv.L, 4)}, estimate ${fmt(iv.A_hat, 4)}, U ${fmt(iv.U, 4)}`, `source line ${iv.source_row}`];
        m.addEventListener("pointermove", e => tip(lines, e)); m.addEventListener("pointerleave", () => tip(null));
      }
      const p = nearest(d.fap, tau);
      el("line", { x1: x(p[0]), x2: x(p[0]), y1: M.t, y2: H - M.b, stroke: "var(--threshold)", "stroke-width": 1, "stroke-dasharray": "1 2" }, g);
      if (p[1] > 0) el("circle", { cx: x(p[0]), cy: y(Math.max(p[1], FMIN)), r: 5, fill: k ? "var(--bg)" : "var(--ink)", stroke: "var(--ink)", "stroke-width": 2 }, g);
    });
  }

  function readout(tau) {
    const t = $("readout"); clear(t);
    const h = t.insertRow(); ["condition", "τ (nearest recorded curve point)", "estimated FAP", "AUROC (computed from the recorded ROC points)"].forEach((s, i) => { const th = document.createElement("th"); th.textContent = s; if (!i) th.className = "l"; h.appendChild(th); });
    for (const c of [panel.condition_of_selection, panel.condition_of_use]) {
      const d = panel.conditions[c], p = nearest(d.fap, tau), r = t.insertRow();
      const c0 = r.insertCell(); c0.className = "l"; c0.textContent = styleOf(c).name;
      r.insertCell().textContent = fmt(p[0], 4);
      r.insertCell().textContent = fmt(p[1], 4);
      r.insertCell().textContent = fmt(auroc(d.roc), 3);
    }
    $("tau-val").textContent = "= " + fmt(tau, 4);
  }

  function ops() {
    const t = $("ops"); clear(t);
    const h = t.insertRow();
    ["condition", "threshold", "τ", "correct withheld", "wrong rejected", "L", "estimated FAP", "U"].forEach((s, i) => { const th = document.createElement("th"); th.textContent = s; if (i < 2) th.className = "l"; h.appendChild(th); });
    for (const c of [panel.condition_of_selection, panel.condition_of_use]) {
      const d = panel.conditions[c];
      for (const op of d.operating_points.slice().sort((a, b) => b.tau - a.tau)) {
        const is01 = Math.abs(op.tau - panel.tau_selected["0.1"]) < 1e-12;
        const r = t.insertRow();
        const a = r.insertCell(); a.className = "l"; a.textContent = c;
        const b = r.insertCell(); b.className = "l"; b.textContent = "selected at " + (is01 ? "0.1†" : "10⁻²") + " in " + panel.condition_of_selection;
        [fmt(op.tau, 4), fmt(op.withheld, 3), fmt(op.rejected, 3)].forEach(v => { r.insertCell().textContent = v; });
        const iv = is01 ? d.interval : null;
        [iv ? fmt(iv.L, 4) : "not recorded", iv ? fmt(iv.A_hat, 4) : "not recorded", iv ? fmt(iv.U, 4) : "not recorded"].forEach(v => { r.insertCell().textContent = v; });
      }
    }
    const cs = panel.condition_of_selection, cu = panel.condition_of_use;
    const a1 = auroc(panel.conditions[cs].roc), a2 = auroc(panel.conditions[cu].roc);
    const o1 = panel.conditions[cs].operating_points.find(o => Math.abs(o.tau - panel.tau_selected["0.1"]) < 1e-12);
    const o2 = panel.conditions[cu].operating_points.find(o => Math.abs(o.tau - panel.tau_selected["0.1"]) < 1e-12);
    const i1 = panel.conditions[cs].interval, i2 = panel.conditions[cu].interval;
    $("explain").textContent = `Computed here: AUROC ${fmt(a1, 3)} in ${cs} and ${fmt(a2, 3)} in ${cu}. ` +
      `At the threshold selected at 0.1† in ${cs}, the operating point moves by ${fmt(Math.abs(o2.withheld - o1.withheld), 2)} in correct detections withheld and ` +
      `by ${fmt(Math.abs(o2.rejected - o1.rejected), 2)} in wrong detections rejected, while the estimated FAP changes from ${fmt(i1.A_hat, 3)} to ${fmt(i2.A_hat, 3)}. ` +
      READING[panel.id];
  }

  function legend() {
    const lg = $("legend"); lg.textContent = "";
    const item = (fn, label) => { const s = document.createElement("span"); const svg = el("svg", { width: 26, height: 12, "aria-hidden": "true" }); fn(svg); s.appendChild(svg); s.appendChild(document.createTextNode(label)); lg.appendChild(s); };
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--ink)", "stroke-width": 2 }, s), styleOf(panel.condition_of_selection).name);
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--ink)", "stroke-width": 2, "stroke-dasharray": "6 4" }, s), styleOf(panel.condition_of_use).name);
    item(s => el("rect", { x: 8, y: 1, width: 10, height: 10, fill: "var(--bg)", stroke: "var(--ink)", "stroke-width": 1.5 }, s), "operating point, τ selected at 0.1†");
    item(s => el("circle", { cx: 13, cy: 6, r: 5, fill: "var(--ink)" }, s), "operating point, τ selected at 10⁻²");
    item(s => el("line", { x1: 13, x2: 13, y1: 0, y2: 12, stroke: "var(--threshold)", "stroke-width": 2.5 }, s), "interval [L, U] at τ selected at 0.1†");
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--limit)", "stroke-dasharray": "2 3" }, s), "limits 0.1† and 10⁻²");
  }

  function render() {
    const tau = Number($("in-tau").value);
    drawRoc(); drawFap(tau); readout(tau);
  }
  function choose() {
    panel = data.panels.find(p => p.id === $("in-panel").value);
    const tmax = Math.max(...Object.values(panel.conditions).map(d => d.fap[d.fap.length - 1][0]));
    const s = $("in-tau"); s.max = tmax; s.step = "any"; s.value = panel.tau_selected["0.1"];
    highlight = "0.1";
    legend(); ops(); render();
  }

  fetch("data/separation.json").then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(d => {
    data = d;
    const sel = $("in-panel");
    d.panels.forEach(p => { const o = document.createElement("option"); o.value = p.id; o.textContent = `${p.pair}: ${p.condition_of_selection} → ${p.condition_of_use} (${IND[p.indicator]})`; sel.appendChild(o); });
    $("status").textContent = d.meta.note;
    sel.addEventListener("input", choose);
    $("in-tau").addEventListener("input", render);
    $("go-01").addEventListener("click", () => { $("in-tau").value = panel.tau_selected["0.1"]; highlight = "0.1"; render(); });
    $("go-001").addEventListener("click", () => { $("in-tau").value = panel.tau_selected["0.01"]; highlight = "0.01"; render(); });
    choose();
  }).catch(e => { $("status").textContent = "Could not read data/separation.json (" + e.message + "). Open the page over HTTP."; });
})();

// Interactive version of Fig. 6 of the paper: lowest limit that n independent units can show to be met.
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { el, text, clear, log, fmt, int, limitLabel, tip } = UI;
  const W = 760, H = 420, M = { l: 64, r: 16, t: 16, b: 46 };
  const X0 = 5, X1 = 40000, Y0 = 6e-5, Y1 = 0.6;
  const LIMITS = [{ a: 1e-4, ex: false }, { a: 1e-3, ex: false }, { a: 1e-2, ex: false }, { a: 0.05, ex: true }, { a: 0.1, ex: true }];
  // marker style per dataset and unit: nuScenes circles, KITTI squares; filled for frames, open for recorded sequences
  const KIND = {
    "nuScenes|frame": { id: "u-nf", name: "nuScenes frames", shape: "circle", fill: true, color: "var(--correct)" },
    "nuScenes|recorded sequence": { id: "u-ns", name: "nuScenes scenes", shape: "circle", fill: false, color: "var(--correct)" },
    "KITTI|frame": { id: "u-kf", name: "KITTI frames", shape: "square", fill: true, color: "var(--ink)" },
    "KITTI|recorded sequence": { id: "u-kd", name: "KITTI drives", shape: "square", fill: false, color: "var(--ink)" }
  };
  let data = null;

  function settings() {
    const delta = Number($("in-delta").value);
    const raw = $("in-alpha").value.trim();
    const alpha = raw === "" ? null : Number(raw);
    const errs = [];
    if (!(delta > 0 && delta < 1)) errs.push("δ must lie between 0 and 1.");
    if (alpha !== null && !(alpha > 0 && alpha < 1)) errs.push("α must lie between 0 and 1.");
    return { delta, alpha: errs.length ? null : alpha, errs, split: Number($("in-split").value), part: $("in-part").value };
  }

  function marker(g, kind, cx, cy) {
    const common = { stroke: kind.color, "stroke-width": 1.6, fill: kind.fill ? kind.color : "var(--bg)" };
    if (kind.shape === "circle") return el("circle", Object.assign({ cx, cy, r: 5 }, common), g);
    return el("rect", Object.assign({ x: cx - 4.5, y: cy - 4.5, width: 9, height: 9 }, common), g);
  }

  function legend() {
    const lg = $("legend"); lg.textContent = "";
    const item = (svgFn, label) => {
      const s = document.createElement("span");
      const svg = el("svg", { width: 26, height: 12, "aria-hidden": "true" }); svgFn(svg); s.appendChild(svg);
      s.appendChild(document.createTextNode(label)); lg.appendChild(s);
    };
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--muted)", "stroke-width": 2 }, s), "selecting a threshold, δ′ = δ");
    item(s => el("line", { x1: 1, x2: 25, y1: 6, y2: 6, stroke: "var(--ink)", "stroke-width": 2, "stroke-dasharray": "5 3" }, s), "testing a threshold, δ′ = δ/2");
    Object.values(KIND).forEach(k => item(s => marker(s, k, 13, 6), k.name));
  }

  function draw() {
    const st = settings();
    $("in-note").textContent = st.errs.join(" ");
    const svg = $("chart");
    [...svg.querySelectorAll("g")].forEach(n => n.remove());
    const g = el("g", {}, svg);
    if (!(st.delta > 0 && st.delta < 1)) return;
    const x = log(X0, X1, M.l, W - M.r), y = log(Y0, Y1, H - M.b, M.t);
    // grid and axes
    for (const t of [10, 100, 1000, 10000]) {
      el("line", { x1: x(t), x2: x(t), y1: M.t, y2: H - M.b, class: "gridline" }, g);
      text(g, x(t), H - M.b + 16, int(t), { "text-anchor": "middle", class: "muted" });
    }
    el("line", { x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: "axis" }, g);
    el("line", { x1: M.l, x2: M.l, y1: M.t, y2: H - M.b, class: "axis" }, g);
    text(g, (M.l + W - M.r) / 2, H - 8, "independent units without a false acceptance, n (log scale)", { "text-anchor": "middle" });
    const yl = text(g, 14, (M.t + H - M.b) / 2, "lowest limit that can be shown to be met", { "text-anchor": "middle", transform: `rotate(-90 14 ${(M.t + H - M.b) / 2})` });
    yl.setAttribute("class", "muted");
    for (const L of LIMITS) {
      el("line", { x1: M.l, x2: W - M.r, y1: y(L.a), y2: y(L.a), stroke: "var(--limit)", "stroke-width": 1, "stroke-dasharray": L.ex ? "2 3" : null }, g);
      text(g, M.l - 4, y(L.a) + 4, limitLabel(L.a) + (L.ex ? "†" : ""), { "text-anchor": "end" });
    }
    if (st.alpha !== null && st.alpha >= Y0 && st.alpha <= Y1) {
      el("line", { x1: M.l, x2: W - M.r, y1: y(st.alpha), y2: y(st.alpha), stroke: "var(--threshold)", "stroke-width": 1.5 }, g);
      text(g, W - M.r - 4, y(st.alpha) - 4, "own limit α = " + fmt(st.alpha), { "text-anchor": "end" });
    }
    // curves
    const curve = (dp) => {
      const pts = [];
      for (let i = 0; i <= 240; i++) {
        const n = Math.pow(10, Math.log10(X0) + i / 240 * (Math.log10(X1) - Math.log10(X0)));
        const v = HB.lowestLimit(n, dp);
        if (v >= Y0 && v <= Y1) pts.push(x(n).toFixed(1) + "," + y(v).toFixed(1));
      }
      return pts.join(" ");
    };
    el("polyline", { points: curve(st.delta), fill: "none", stroke: "var(--muted)", "stroke-width": 2 }, g);
    el("polyline", { points: curve(st.delta / 2), fill: "none", stroke: "var(--ink)", "stroke-width": 2, "stroke-dasharray": "6 4" }, g);
    text(g, x(X0) + 6, y(1.6e-4), "target limits: solid grey lines; exploratory limits (†): dotted", { class: "muted" });
    // markers
    if (!data) return;
    const dp = st.part === "test" ? st.delta / 2 : st.delta;
    const shown = data.units.filter(u => u.split === st.split && u.part === st.part && $(KIND[u.dataset + "|" + u.unit].id).checked);
    const mg = el("g", {}, g);
    for (const u of shown) {
      const v = HB.lowestLimit(u.n, dp);
      const k = KIND[u.dataset + "|" + u.unit];
      const m = marker(mg, k, x(Math.max(u.n, X0)), y(Math.min(Math.max(v, Y0), Y1)));
      m.setAttribute("tabindex", "0");
      m.setAttribute("aria-label", `${u.pair}, ${u.condition}: ${u.n} ${u.unit_name}, lowest limit ${fmt(v, 3)}`);
      const lines = [`${u.pair}, ${u.condition}`, `${int(u.n)} ${u.unit_name}, ${partName(u.part)}, split ${u.split}`, `lowest limit (computed from n): ${fmt(v, 3)}`, `${u.source_file}, line ${u.source_row}`];
      m.addEventListener("pointermove", e => tip(lines, e));
      m.addEventListener("pointerleave", () => tip(null));
      m.addEventListener("focus", () => { const b = m.getBoundingClientRect(); tip(lines, { clientX: b.right, clientY: b.bottom }); });
      m.addEventListener("blur", () => tip(null));
    }
    tables(st, shown, dp);
  }

  function partName(p) { return p === "test" ? "test part" : p === "selection" ? "selection part" : "all recorded sequences of the condition"; }

  function tables(st, shown, dp) {
    const need = $("need"); clear(need);
    const hr = need.insertRow(); ["limit α", "units for selecting (δ′ = δ)", "units for testing (δ′ = δ/2)"].forEach((h, i) => { const th = document.createElement("th"); th.textContent = h; if (!i) th.className = "l"; hr.appendChild(th); });
    const lims = LIMITS.map(L => ({ a: L.a, lab: limitLabel(L.a) + (L.ex ? "†" : "") }));
    if (st.alpha !== null) lims.push({ a: st.alpha, lab: fmt(st.alpha) + " (own)" });
    for (const L of lims) {
      const r = need.insertRow();
      const c0 = r.insertCell(); c0.className = "l"; c0.textContent = L.lab;
      r.insertCell().textContent = int(Math.ceil(HB.zeroFailureBound(L.a, st.delta) - 1e-9));
      r.insertCell().textContent = int(Math.ceil(HB.zeroFailureBound(L.a, st.delta / 2) - 1e-9));
    }
    const t = $("units"); clear(t);
    const h = t.insertRow();
    ["pair of conditions", "condition", "unit", "n", "lowest limit (computed)", "lowest target limit reachable", "source"].forEach((s, i) => { const th = document.createElement("th"); th.textContent = s; if (i < 3 || i === 6) th.className = "l"; h.appendChild(th); });
    if (!shown.length) { const r = t.insertRow(); const c = r.insertCell(); c.colSpan = 7; c.className = "l"; c.textContent = st.part === "all" ? "No unit type selected, or frames: the part 'all' lists recorded sequences only." : "No unit type selected."; return; }
    for (const u of shown.slice().sort((a, b) => a.n - b.n)) {
      const v = HB.lowestLimit(u.n, dp);
      const reach = [1e-4, 1e-3, 1e-2].find(a => v <= a);
      const r = t.insertRow();
      [u.pair, u.condition, u.unit_name].forEach(s => { const c = r.insertCell(); c.className = "l"; c.textContent = s; });
      r.insertCell().textContent = int(u.n);
      r.insertCell().textContent = fmt(v, 3);
      r.insertCell().textContent = reach ? limitLabel(reach) : "none";
      const c = r.insertCell(); c.className = "l"; c.textContent = `${u.source_file}, line ${u.source_row}`;
    }
  }

  ["in-delta", "in-alpha", "in-split", "in-part", "u-nf", "u-ns", "u-kf", "u-kd"].forEach(id => $(id).addEventListener("input", draw));
  legend();
  draw();
  fetch("data/units.json").then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(d => {
    data = d; $("status").textContent = `${d.units.length} recorded unit counts (generator ${d.meta.generator_version}).`; draw();
  }).catch(e => { $("status").textContent = "Could not read data/units.json (" + e.message + "). The curves are computed; open the page over HTTP to see the markers."; });
})();

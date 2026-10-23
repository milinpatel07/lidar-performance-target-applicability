// Applicability test calculator. Statistics: stats.js (port of experiments/m1_range_kitti.py).
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { el, text, clear, log, fmt, int, limitLabel } = UI;
  const CODE = { "applicable": "A", "not applicable": "N", "not determined": "Q", "no threshold selected": "D" };
  const TARGET = [1e-2, 1e-3, 1e-4];

  function mode() { return document.querySelector("input[name=mode]:checked").value; }

  function read() {
    const n = Math.floor(Number($("in-n").value));
    const alpha = Number($("in-alpha").value), delta = Number($("in-delta").value);
    const errs = [];
    if (!(n >= 1)) errs.push("n must be a whole number of at least 1.");
    if (!(alpha > 0 && alpha < 1)) errs.push("α must lie between 0 and 1.");
    if (!(delta > 0 && delta < 1)) errs.push("δ must lie between 0 and 1.");
    let S;
    if (mode() === "mean") {
      const a = Number($("in-a").value);
      if (!(a >= 0 && a <= 1)) errs.push("Â must lie between 0 and 1.");
      S = a * n;
    } else {
      const k = Math.floor(Number($("in-k").value));
      if (!(k >= 0 && k <= n)) errs.push("The count must lie between 0 and n.");
      S = k;
    }
    return { n, alpha, delta, S, errs };
  }

  function compute(n, S, alpha, delta) {
    const p = HB.hbPvalue(S, n, alpha);
    const U = HB.hbUpper(S, n, delta / 2), L = HB.hbLower(S, n, delta / 2);
    return {
      Ahat: S / n, p, pass: p <= delta, L, U, outcome: HB.outcome(L, U, alpha),
      eqSel: Math.ceil(HB.zeroFailureBound(alpha, delta) - 1e-9), eqTest: Math.ceil(HB.zeroFailureBound(alpha, delta / 2) - 1e-9),
      hbSel: HB.nRequired(alpha, delta), hbTest: HB.nRequired(alpha, delta / 2),
      lowSel: HB.lowestLimit(n, delta), lowTest: HB.lowestLimit(n, delta / 2)
    };
  }

  function row(tbl, label, value, note) {
    const tr = document.createElement("tr");
    const th = document.createElement("th"); th.className = "l"; th.scope = "row"; th.textContent = label;
    const td = document.createElement("td"); td.textContent = value;
    const tn = document.createElement("td"); tn.className = "l"; tn.textContent = note || "";
    tr.append(th, td, tn); tbl.appendChild(tr);
  }

  function strip(r, alpha) {
    const svg = $("strip"); clear(svg);
    // keep the title and desc for assistive technology
    el("title", { id: "strip-title" }, svg).textContent = "Interval of the FAP against the limit";
    const d = el("desc", { id: "strip-desc" }, svg);
    d.textContent = `FAP interval from ${fmt(r.L)} to ${fmt(r.U)}, estimate ${fmt(r.Ahat)}, limit ${fmt(alpha)}; outcome ${r.outcome}.`;
    const lo = 1e-5, x = log(lo, 1, 40, 700), y = 44;
    for (const t of UI.decades(lo, 1)) {
      el("line", { x1: x(t), x2: x(t), y1: 18, y2: 66, class: "gridline" }, svg);
      text(svg, x(t), 82, t === 1 ? "1" : "10" + UI.sup(Math.round(Math.log10(t))), { "text-anchor": "middle", class: "muted" });
    }
    el("line", { x1: 40, x2: 700, y1: 66, y2: 66, class: "axis" }, svg);
    text(svg, 700, 94, "FAP (log scale)", { class: "muted", "text-anchor": "end" });
    // limit
    el("line", { x1: x(alpha), x2: x(alpha), y1: 12, y2: 66, stroke: "var(--wrong)", "stroke-width": 2, "stroke-dasharray": "5 3" }, svg);
    text(svg, x(alpha), 10, "α = " + fmt(alpha), { "text-anchor": x(alpha) > 640 ? "end" : "middle" });
    // interval
    const xl = r.L < lo ? 40 : x(r.L), xu = x(r.U);
    el("line", { x1: xl, x2: xu, y1: y, y2: y, stroke: "var(--ink)", "stroke-width": 3, "stroke-linecap": "round" }, svg);
    if (r.L >= lo) el("line", { x1: xl, x2: xl, y1: y - 8, y2: y + 8, stroke: "var(--ink)", "stroke-width": 2 }, svg);
    else text(svg, 44, y - 10, "L below 10⁻⁵", { class: "muted" });
    el("line", { x1: xu, x2: xu, y1: y - 8, y2: y + 8, stroke: "var(--ink)", "stroke-width": 2 }, svg);
    if (r.Ahat >= lo) el("circle", { cx: x(r.Ahat), cy: y, r: 5, fill: "var(--bg)", stroke: "var(--ink)", "stroke-width": 2 }, svg);
    text(svg, xu + 6, y + 4, "U", { class: "muted" });
  }

  function update() {
    const { n, alpha, delta, S, errs } = read();
    $("lab-mean").hidden = mode() !== "mean";
    $("lab-count").hidden = mode() !== "count";
    $("in-note").textContent = errs.join(" ");
    const tbl = $("r-table"); clear(tbl);
    if (errs.length) { $("r-outcome").textContent = "–"; $("r-outcome").className = "outcome"; clear($("strip")); return; }
    const r = compute(n, S, alpha, delta);
    $("r-outcome").textContent = r.outcome;
    $("r-outcome").className = "outcome " + CODE[r.outcome];
    strip(r, alpha);
    const head = document.createElement("tr");
    ["quantity", "value", "meaning"].forEach((h, i) => { const th = document.createElement("th"); th.textContent = h; if (i !== 1) th.className = "l"; head.appendChild(th); });
    tbl.appendChild(head);
    row(tbl, "mean per-unit share Â", fmt(r.Ahat, 6), "sum S = " + fmt(S, 6) + " over n = " + int(n) + " units");
    row(tbl, "HB p-value for FAP > α", fmt(r.p, 4), r.pass ? "≤ δ: a candidate with these selection data passes" : "> δ: a candidate with these selection data fails");
    row(tbl, "lower bound L", fmt(r.L, 6), "at δ/2 = " + fmt(delta / 2));
    row(tbl, "upper bound U", fmt(r.U, 6), "at δ/2 = " + fmt(delta / 2) + "; [L, U] at confidence " + fmt(1 - delta));
    row(tbl, "Eq. 5, units for selecting (δ′ = δ)", int(r.eqSel), "ln δ / ln(1 − α), rounded up; " + (n >= r.eqSel ? "n reaches it" : "n is below it"));
    row(tbl, "Eq. 5, units for testing (δ′ = δ/2)", int(r.eqTest), "ln(δ/2) / ln(1 − α), rounded up; " + (n >= r.eqTest ? "n reaches it" : "n is below it"));
    row(tbl, "HB test, units for selecting", int(r.hbSel), "smallest n at which n units without a false acceptance pass at δ");
    row(tbl, "HB test, units for testing", int(r.hbTest), "smallest n at which n units without a false acceptance give U ≤ α");
    row(tbl, "lowest limit, selecting", fmt(r.lowSel, 4), "1 − δ^(1/n): the lowest limit n units without a false acceptance can show to be met");
    row(tbl, "lowest limit, testing", fmt(r.lowTest, 4), "1 − (δ/2)^(1/n)");
    const met = TARGET.filter(a => r.lowTest <= a).map(limitLabel);
    row(tbl, "target limits reachable when testing", met.length ? met.join(", ") : "none", "of 10⁻², 10⁻³, 10⁻⁴, with n units and no false acceptance");
  }

  // ---- recorded rows ----
  let recs = [];
  function label(r) {
    const ex = r.limit_type === "exploratory" ? "†" : "";
    return `${r.indicator} · ${r.condition_of_selection} → ${r.condition_of_use} · α = ${limitLabel(r.alpha)}${ex} · split ${r.split}` +
      (r.pair.indexOf("KITTI") >= 0 || r.pair.indexOf("dataset") >= 0 ? (r.kitti_rule ? " · KITTI rule" : " · as run") : "");
  }
  function loadRecords() {
    fetch("../explorer/data/outcomes.json").then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(d => {
      recs = d.records.filter(r => r.unit === "recorded sequence" && r.estimate === "FAP" && r.A_hat !== null && r.n_eval_units && r.U !== null);
      recs.sort((a, b) => (a.pair + a.indicator + a.condition_of_selection + a.condition_of_use).localeCompare(b.pair + b.indicator + b.condition_of_selection + b.condition_of_use) || b.alpha - a.alpha || a.split - b.split || (a.kitti_rule - b.kitti_rule));
      const sel = $("rec-select"); clear(sel);
      const groups = {};
      recs.forEach((r, i) => {
        if (!groups[r.pair]) { groups[r.pair] = document.createElement("optgroup"); groups[r.pair].label = r.pair; sel.appendChild(groups[r.pair]); }
        const o = document.createElement("option"); o.value = i; o.textContent = label(r) + " · " + r.outcome; groups[r.pair].appendChild(o);
      });
      sel.disabled = false; $("rec-load").disabled = false;
      $("rec-status").textContent = `${recs.length} rows of the sequence-level evaluation with a selected threshold.`;
    }).catch(e => {
      $("rec-status").textContent = "Could not read ../explorer/data/outcomes.json (" + e.message + "). Open the page over HTTP, for example on GitHub Pages or with python3 -m http.server -d site in the repository root.";
    });
  }
  function loadRow() {
    const r = recs[Number($("rec-select").value)];
    if (!r) return;
    document.querySelector("input[name=mode][value=mean]").checked = true;
    $("in-n").value = r.n_eval_units; $("in-a").value = r.A_hat; $("in-alpha").value = r.alpha; $("in-delta").value = 0.05;
    update();
    const n = r.n_eval_units, S = r.A_hat * n;
    const U = HB.hbUpper(S, n, 0.025), L = HB.hbLower(S, n, 0.025), out = HB.outcome(L, U, r.alpha);
    const t = $("rec-table"); clear(t); t.hidden = false;
    const h = document.createElement("tr");
    ["", "recorded", "recomputed here", "absolute difference"].forEach(s => { const th = document.createElement("th"); th.textContent = s; h.appendChild(th); });
    t.appendChild(h);
    const add = (k, a, b, diff) => {
      const tr = document.createElement("tr");
      const th = document.createElement("th"); th.className = "l"; th.scope = "row"; th.textContent = k; tr.appendChild(th);
      [a, b, diff].forEach(v => { const td = document.createElement("td"); td.textContent = v; tr.appendChild(td); });
      t.appendChild(tr);
    };
    add("L", fmt(r.L, 10), fmt(L, 10), fmt(Math.abs(L - r.L), 2));
    add("U", fmt(r.U, 10), fmt(U, 10), fmt(Math.abs(U - r.U), 2));
    add("outcome", r.outcome, out, r.outcome === out ? "same" : "differs");
    $("rec-note").textContent = `Source: ${r.source_file}, line ${r.source_row}. Test units n = ${n} recorded sequences; ` +
      `selection units ${r.n_select_units}; Â = ${fmt(r.A_hat, 6)}; retention ${r.retention === null ? "not recorded" : fmt(r.retention, 3)}; δ = 0.05.`;
  }

  document.querySelectorAll("#inputs input").forEach(i => i.addEventListener("input", update));
  $("rec-load").addEventListener("click", loadRow);
  update();
  loadRecords();
})();

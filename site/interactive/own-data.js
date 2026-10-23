// Page logic of own-data.html. Computation: apptest.js and stats.js. Nothing is sent anywhere.
(function () {
  "use strict";
  const $ = id => document.getElementById(id);
  const { el, text, clear, lin, log, fmt, int } = UI;
  const CODE = { "applicable": "A", "not applicable": "N", "not determined": "Q", "no threshold selected": "D" };
  const LETTER = { A: "A", N: "N", Q: "?", D: "–" };
  const S = { parsed: null, rows: null, source: "", division: null, all: null, pair: null, settings: null };

  // ---------- loading ----------
  function msg(lines, cls) {
    const box = $("load-msgs"); clear(box);
    for (const l of lines) { const p = document.createElement("p"); p.className = cls || "note"; p.textContent = l; box.appendChild(p); }
  }
  function loaded(parsed, source) {
    S.parsed = parsed; S.source = source; S.all = null; S.pair = null;
    if (parsed.errors.length) {
      $("load-status").textContent = `${source}: ${parsed.rows.length} rows read, ${parsed.errors.length} problem(s); the test is not run until they are fixed.`;
      msg(parsed.errors, "warn");
      ["div-sec", "set-sec", "res-sec", "mx-sec"].forEach(id => { $(id).hidden = true; });
      return;
    }
    msg(parsed.warnings, "warn");
    const conds = AppTest.conditions(parsed.rows);
    $("load-status").textContent = `${source}: ${int(parsed.rows.length)} detections, ${conds.length} conditions (${conds.join(", ")})` +
      (parsed.hasSequence ? ", with sequence ids" : ", without sequence ids") + (parsed.hasPart ? ", with a part column." : ", without a part column.");
    if (conds.length < 1) return;
    $("div-sec").hidden = false;
    $("div-by").querySelector("option[value=sequence]").disabled = !parsed.hasSequence;
    if (!parsed.hasSequence) $("div-by").value = "frame";
    $("div-file").hidden = !parsed.hasPart;
    $("s-unit").querySelector("option[value=sequence]").disabled = !parsed.hasSequence;
    if (!parsed.hasSequence) $("s-unit").value = "frame";
    if (parsed.hasPart) useFileParts(); else applyDivision();
    fillConditions(conds);
    $("set-sec").hidden = false;
    run();
  }
  function useFileParts() {
    S.rows = S.parsed.rows; S.division = null;
    $("div-text").textContent = "The file has a part column; it is used as given. A random division can replace it.";
  }
  function applyDivision() {
    const by = $("div-by").value, share = Number($("div-share").value), seed = Math.floor(Number($("div-seed").value));
    if (!(share > 0 && share < 1)) { $("div-text").textContent = "The selection share must lie between 0 and 1."; return; }
    S.rows = AppTest.divide(S.parsed.rows, by, share, seed);
    S.division = { by, share, seed };
    const keys = by === "sequence" ? new Set(S.rows.map(r => r.sequence)) : new Set(S.rows.map(r => (r.sequence || "") + "\u0001" + r.frame));
    const nSel = new Set(S.rows.filter(r => r.part === "selection").map(r => by === "sequence" ? r.sequence : (r.sequence || "") + "\u0001" + r.frame)).size;
    $("div-text").textContent = `${S.parsed.hasPart ? "The part column of the file is replaced: " : "The file has no part column: "}` +
      `random division ${by === "sequence" ? "by recorded sequence" : "by frame"} with seed ${seed}; ${int(nSel)} of ${int(keys.size)} ` +
      `${by === "sequence" ? "sequences" : "frames"} in the selection part, the others in the test part.` +
      (by === "frame" && S.parsed.hasSequence ? " With a division by frame, frames of one recorded sequence fall into both parts, so test units are not independent of selection units." : "");
  }
  function fillConditions(conds) {
    for (const [id, k] of [["s-c", 0], ["s-c2", Math.min(1, conds.length - 1)]]) {
      const s = $(id); clear(s);
      conds.forEach(c => { const o = document.createElement("option"); o.value = c; o.textContent = c; s.appendChild(o); });
      s.value = conds[k];
    }
  }
  function readFile(file) {
    const r = new FileReader();
    r.onload = () => loaded(AppTest.parseCSV(String(r.result)), file.name);
    r.onerror = () => { $("load-status").textContent = "The file could not be read."; };
    r.readAsText(file);
  }

  // ---------- settings ----------
  function settings() {
    const alpha = Number($("s-alpha").value), delta = Number($("s-delta").value), unit = $("s-unit").value;
    const errs = [];
    if (!(alpha > 0 && alpha < 1)) errs.push("α must lie between 0 and 1.");
    if (!(delta > 0 && delta < 1)) errs.push("δ must lie between 0 and 1.");
    let candidates = null;
    if ($("s-cand").value === "list") {
      candidates = $("s-list").value.split(/[\s,;]+/).filter(s => s !== "").map(Number);
      if (!candidates.length || candidates.some(v => !Number.isFinite(v))) errs.push("The list of candidate thresholds must hold numbers.");
    }
    return { alpha, delta, unit, candidates, errs, c: $("s-c").value, c2: $("s-c2").value };
  }

  function run() {
    if (!S.rows) return;
    const st = settings();
    $("set-note").textContent = st.errs.join(" ");
    if (st.errs.length) return;
    const opts = { alpha: st.alpha, delta: st.delta, unit: st.unit, candidates: st.candidates };
    S.settings = st;
    S.all = AppTest.runAll(S.rows, opts);
    S.pair = S.all.pairs.find(p => p.c === st.c && p.c2 === st.c2);
    showPair(S.pair);
    matrix();
  }

  // ---------- one pair ----------
  function showPair(p) {
    $("res-sec").hidden = false;
    $("res-h").textContent = `4. Outcome for ${p.c} → ${p.c2}` + (p.c === p.c2 ? " (own condition)" : "");
    const o = $("r-outcome"); o.textContent = p.outcome; o.className = "outcome " + CODE[p.outcome];
    const w = $("r-warn"); clear(w);
    const warn = s => { const d = document.createElement("p"); d.className = "warn"; d.textContent = s; w.appendChild(d); };
    if (p.nSelection < p.eq5Selection) warn(`The selection part of ${p.c} holds ${int(p.nSelection)} units, fewer than the ${int(p.eq5Selection)} that Eq. 5 requires for selecting at α = ${fmt(p.alpha)} and δ = ${fmt(p.delta)}: no candidate can pass.`);
    if (p.nTest < p.eq5Test) warn(`The test part of ${p.c2} holds ${int(p.nTest)} units, fewer than the ${int(p.eq5Test)} that Eq. 5 requires for testing (δ/2): the outcome applicable is not reachable.`);
    if (p.unit === "frame" && S.parsed.hasSequence) warn("Frame-level evaluation: frames of one recorded sequence are not independent, so the stated error probability is not guaranteed.");
    strip(p);
    const t = $("r-table"); clear(t);
    const h = t.insertRow(); ["quantity", "value", "meaning"].forEach((s, i) => { const th = document.createElement("th"); th.textContent = s; if (i !== 1) th.className = "l"; h.appendChild(th); });
    const add = (k, v, m) => { const r = t.insertRow(); const a = r.insertCell(); a.className = "l"; a.textContent = k; r.insertCell().textContent = v; const b = r.insertCell(); b.className = "l"; b.textContent = m || ""; };
    const unitName = p.unit === "frame" ? "frames" : "recorded sequences";
    add("candidate thresholds", int(p.selection.candidates.length), p.candidateSource === "list" ? "from the list" : "quantiles of u, " + p.candidateSource + " of " + (p.c === p.c2 ? p.c : p.c + " and " + p.c2));
    add("selected threshold τ_c", p.tau === null ? "none" : fmt(p.tau, 6), p.tau === null ? "the lowest candidate fails in " + p.c : "candidate " + (p.selection.index + 1) + " of " + p.selection.candidates.length);
    add("units in the selection part of c", int(p.nSelection), unitName + "; Eq. 5 minimum " + int(p.eq5Selection));
    add("units in the test part of c′", int(p.nTest), unitName + "; Eq. 5 minimum " + int(p.eq5Test));
    if (p.test) {
      add("Â in c′", fmt(p.test.A_hat, 6), "mean per-unit share of false acceptances");
      add("L", fmt(p.test.L, 6), "at δ/2 = " + fmt(p.delta / 2));
      add("U", fmt(p.test.U, 6), "at δ/2; [L, U] at confidence " + fmt(1 - p.delta));
      add("retention in c′", fmt(p.test.retention, 4), "share of the correct detections of the test part of c′ that τ_c accepts");
      if (p.c !== p.c2) add("own-condition check in c", p.ownCheck.outcome, `Â ${fmt(p.ownCheck.A_hat, 4)}, [L, U] = [${fmt(p.ownCheck.L, 4)}, ${fmt(p.ownCheck.U, 4)}], retention ${fmt(p.ownCheck.retention, 4)}, n ${int(p.ownCheck.n)}`);
    }
    pchart(p);
  }

  function strip(p) {
    const svg = $("strip"); [...svg.querySelectorAll("g")].forEach(n => n.remove());
    const g = el("g", {}, svg);
    const lo = 1e-5, x = log(lo, 1, 40, 700), y = 44, a = p.alpha;
    for (const t of UI.decades(lo, 1)) {
      el("line", { x1: x(t), x2: x(t), y1: 18, y2: 66, class: "gridline" }, g);
      text(g, x(t), 82, t === 1 ? "1" : "10" + UI.sup(Math.round(Math.log10(t))), { "text-anchor": "middle", class: "muted" });
    }
    el("line", { x1: 40, x2: 700, y1: 66, y2: 66, class: "axis" }, g);
    text(g, 700, 96, "FAP in c′ (log scale)", { class: "muted", "text-anchor": "end" });
    el("line", { x1: x(a), x2: x(a), y1: 12, y2: 66, stroke: "var(--wrong)", "stroke-width": 2, "stroke-dasharray": "5 3" }, g);
    text(g, x(a), 10, "α = " + fmt(a), { "text-anchor": x(a) > 640 ? "end" : "middle" });
    if (!p.test) { text(g, 50, y + 4, "no threshold selected: nothing to test", { class: "muted" }); return; }
    const r = p.test, xl = r.L < lo ? 40 : x(r.L), xu = x(r.U);
    el("line", { x1: xl, x2: xu, y1: y, y2: y, stroke: "var(--ink)", "stroke-width": 3, "stroke-linecap": "round" }, g);
    if (r.L >= lo) el("line", { x1: xl, x2: xl, y1: y - 8, y2: y + 8, stroke: "var(--ink)", "stroke-width": 2 }, g);
    else text(g, 44, y - 10, "L below 10⁻⁵", { class: "muted" });
    el("line", { x1: xu, x2: xu, y1: y - 8, y2: y + 8, stroke: "var(--ink)", "stroke-width": 2 }, g);
    if (r.A_hat >= lo) el("circle", { cx: x(r.A_hat), cy: y, r: 5, fill: "var(--bg)", stroke: "var(--ink)", "stroke-width": 2 }, g);
    const d = svg.querySelector("title"); d.textContent = `Interval of the FAP in ${p.c2}: [${fmt(r.L)}, ${fmt(r.U)}], estimate ${fmt(r.A_hat)}, limit ${fmt(a)}; ${r.outcome}.`;
  }

  function pchart(p) {
    const svg = $("pchart"); [...svg.querySelectorAll("g")].forEach(n => n.remove());
    const g = el("g", {}, svg);
    const W = 720, H = 240, M = { l: 56, r: 12, t: 12, b: 40 };
    const cand = p.selection.candidates, pv = p.selection.pValues;
    if (!cand.length) { text(g, M.l, H / 2, "no candidate thresholds", { class: "muted" }); return; }
    const t0 = cand[0], t1 = cand[cand.length - 1] > t0 ? cand[cand.length - 1] : t0 + 1;
    const x = lin(t0, t1, M.l, W - M.r), P0 = 1e-6, y = log(P0, 1, H - M.b, M.t);
    for (const t of [1e-6, 1e-4, 1e-2, 1]) {
      el("line", { x1: M.l, x2: W - M.r, y1: y(t), y2: y(t), class: "gridline" }, g);
      text(g, M.l - 4, y(t) + 4, t === 1 ? "1" : "10" + UI.sup(Math.round(Math.log10(t))), { "text-anchor": "end", class: "muted" });
    }
    for (let k = 0; k <= 4; k++) { const t = t0 + (t1 - t0) * k / 4; text(g, x(t), H - M.b + 15, fmt(t, 3), { "text-anchor": "middle", class: "muted" }); }
    el("line", { x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: "axis" }, g);
    text(g, (M.l + W - M.r) / 2, H - 6, "candidate threshold τ (u ≤ τ accepted)", { "text-anchor": "middle" });
    el("line", { x1: M.l, x2: W - M.r, y1: y(p.delta), y2: y(p.delta), stroke: "var(--wrong)", "stroke-width": 1.5, "stroke-dasharray": "5 3" }, g);
    text(g, W - M.r - 2, y(p.delta) - 4, "δ = " + fmt(p.delta), { "text-anchor": "end" });
    const pts = cand.map((t, j) => x(t).toFixed(1) + "," + y(Math.max(pv[j], P0)).toFixed(1)).join(" ");
    el("polyline", { points: pts, fill: "none", stroke: "var(--muted)", "stroke-width": 1.5 }, g);
    const firstFail = p.selection.index + 1 < cand.length ? p.selection.index + 1 : -1;
    cand.forEach((t, j) => {
      const sel = j === p.selection.index, fail = j === firstFail;
      const m = el("circle", { cx: x(t), cy: y(Math.max(pv[j], P0)), r: sel || fail ? 5 : 2.5,
        fill: sel ? "var(--c-A)" : (pv[j] <= p.delta ? "var(--ink)" : "var(--bg)"), stroke: fail ? "var(--c-N)" : "var(--ink)", "stroke-width": fail ? 2.5 : 1 }, g);
      const lines = [`τ = ${fmt(t, 6)} (candidate ${j + 1})`, `p = ${fmt(pv[j], 4)}${pv[j] <= p.delta ? " ≤ δ: passes" : " > δ: fails"}`];
      if (sel) lines.push("selected"); if (fail) lines.push("first candidate that fails");
      m.addEventListener("pointermove", e => UI.tip(lines, e)); m.addEventListener("pointerleave", () => UI.tip(null));
    });
  }

  // ---------- matrix ----------
  function matrix() {
    $("mx-sec").hidden = false;
    const lg = $("mx-legend"); clear(lg);
    for (const [k, name] of [["A", "applicable"], ["N", "not applicable"], ["Q", "not determined"], ["D", "no threshold selected"]]) {
      const s = document.createElement("span"); const q = document.createElement("span"); q.className = "sq " + k; q.textContent = LETTER[k]; q.setAttribute("aria-hidden", "true");
      s.append(q, document.createTextNode(name)); lg.appendChild(s);
    }
    const t = $("matrix"); clear(t);
    const cs = S.all.conditions;
    const h = t.insertRow(); const c0 = document.createElement("th"); c0.textContent = "c \\ c′"; h.appendChild(c0);
    cs.forEach(c => { const th = document.createElement("th"); th.scope = "col"; th.textContent = c; h.appendChild(th); });
    for (const c of cs) {
      const r = t.insertRow(); const th = document.createElement("th"); th.scope = "row"; th.textContent = c; r.appendChild(th);
      for (const c2 of cs) {
        const p = S.all.pairs.find(q => q.c === c && q.c2 === c2);
        const td = r.insertCell(); const b = document.createElement("button"); b.type = "button";
        const k = CODE[p.outcome];
        const sq = document.createElement("span"); sq.className = "sq " + k; sq.textContent = LETTER[k]; sq.setAttribute("aria-hidden", "true");
        const small = document.createElement("span"); small.className = "note"; small.textContent = p.tau === null ? "–" : "τ " + fmt(p.tau, 3);
        b.append(sq, small);
        b.setAttribute("aria-label", `${c} to ${c2}: ${p.outcome}` + (p.tau === null ? "" : `, threshold ${fmt(p.tau, 4)}`));
        b.setAttribute("aria-pressed", p === S.pair ? "true" : "false");
        b.addEventListener("click", () => { $("s-c").value = c; $("s-c2").value = c2; S.pair = p; showPair(p); matrix(); $("res-h").scrollIntoView({ behavior: "smooth", block: "start" }); });
        td.appendChild(b);
      }
    }
  }

  // ---------- export ----------
  function download(name, type, content) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([content], { type }));
    a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }
  function resultRows() {
    return S.all.pairs.map(p => ({
      condition_of_selection: p.c, condition_of_use: p.c2, unit: p.unit, alpha: p.alpha, delta: p.delta,
      candidates: p.selection.candidates.length, candidate_source: p.candidateSource, tau: p.tau,
      n_selection: p.nSelection, n_test: p.nTest, eq5_selection: p.eq5Selection, eq5_test: p.eq5Test,
      A_hat: p.test ? p.test.A_hat : null, L: p.test ? p.test.L : null, U: p.test ? p.test.U : null,
      retention: p.test ? p.test.retention : null, outcome: p.outcome
    }));
  }
  function exportCSV() {
    const rows = resultRows(), keys = Object.keys(rows[0]);
    const q = v => v === null || v === undefined || (typeof v === "number" && !Number.isFinite(v)) ? "" : (/[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v));
    download("applicability_results.csv", "text/csv", [keys.join(",")].concat(rows.map(r => keys.map(k => q(r[k])).join(","))).join("\n") + "\n");
  }
  function exportJSON() {
    const st = S.settings;
    const obj = { input: S.source, division: S.division || "part column of the file",
      settings: { alpha: st.alpha, delta: st.delta, unit: st.unit, candidates: st.candidates ? st.candidates : "quantiles 0.01..1.00 of u over both conditions of each pair" },
      results: resultRows(),
      pairs: S.all.pairs.map(p => ({ condition_of_selection: p.c, condition_of_use: p.c2, candidates: p.selection.candidates,
        p_values: p.selection.pValues, selected_index: p.selection.index, tau: p.tau, test: p.test, own_condition_check: p.ownCheck })) };
    download("applicability_results.json", "application/json", JSON.stringify(obj, (k, v) => (typeof v === "number" && !Number.isFinite(v)) ? null : v, 1));
  }

  // ---------- events ----------
  $("file").addEventListener("change", e => { if (e.target.files[0]) readFile(e.target.files[0]); });
  const drop = $("drop");
  ["dragenter", "dragover"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => { const f = e.dataTransfer.files[0]; if (f) readFile(f); });
  function loadSynthetic() {
    const rows = AppTest.synthetic(1);
    loaded({ rows, hasSequence: true, hasPart: false, errors: [], warnings: [] }, "synthetic example (seed 1, not data)");
  }
  $("synth").addEventListener("click", loadSynthetic);
  if (location.hash === "#synthetic") loadSynthetic();
  $("div-apply").addEventListener("click", () => { applyDivision(); run(); });
  $("div-file").addEventListener("click", () => { useFileParts(); run(); });
  $("dl-data").addEventListener("click", () => { if (S.rows) download("detections_divided.csv", "text/csv", AppTest.toCSV(S.rows, S.parsed.hasSequence)); });
  $("s-cand").addEventListener("input", () => { $("s-list-lab").hidden = $("s-cand").value !== "list"; });
  ["s-c", "s-c2", "s-unit", "s-cand"].forEach(id => $(id).addEventListener("input", run));
  ["s-alpha", "s-delta"].forEach(id => $(id).addEventListener("change", run));
  $("run").addEventListener("click", run);
  $("dl-csv").addEventListener("click", exportCSV);
  $("dl-json").addEventListener("click", exportJSON);
})();

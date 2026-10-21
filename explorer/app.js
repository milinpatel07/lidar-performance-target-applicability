/* Outcome explorer: reads data/outcomes.json (written by tools/build_explorer_data.py) and draws the outcome grid.
   Plain JavaScript without libraries, so that the page works offline. The pure functions at the top are also
   loaded by Node for testing (module.exports at the end). */
"use strict";

var PAIRS = [
  ["KITTI distance", [["near", "far"], ["far", "near"]], [["near", "near"], ["far", "far"]]],
  ["nuScenes distance", [["near", "far"], ["far", "near"]], [["near", "near"], ["far", "far"]]],
  ["nuScenes weather", [["clear", "rain"], ["rain", "clear"]], [["clear", "clear"], ["rain", "rain"]]],
  ["change of dataset and detector", [["nuScenes", "KITTI"], ["KITTI", "nuScenes"]],
    [["KITTI", "KITTI"], ["nuScenes", "nuScenes"]]]
];
var ALPHAS = [0.01, 0.001, 0.0001, 0.05, 0.1];
var INDICATORS = { u_s: "u_s (spatial)", u_e: "u_e (existence)" };
var OUTCOMES = [
  ["A", "applicable", "A"], ["N", "not applicable", "N"],
  ["?", "not determined", "Q"], ["-", "no threshold selected", "D"]
];
var VIEWS = {
  frame: { division: "by frame", unit: "frame", method: null },
  seq_frame: { division: "by recorded sequence", unit: "frame", method: null },
  seq_seq: { division: "by recorded sequence", unit: "recorded sequence", method: null },
  postA: { division: "by recorded sequence", unit: "recorded sequence", method: "post-hoc Method A" },
  postB: { division: "by recorded sequence", unit: "recorded sequence", method: "post-hoc Method B" }
};

function alphaLabel(a) {
  return { 0.01: "10⁻²", 0.001: "10⁻³", 0.0001: "10⁻⁴", 0.05: "0.05†", 0.1: "0.1†" }[a];
}

/* The KITTI rule can be switched off only where the files hold rows without it (not for post-hoc). */
function ruleAvailable(view) { return VIEWS[view].method === null; }

function selectRecords(records, state) {
  var v = VIEWS[state.view];
  var rule = ruleAvailable(state.view) ? state.kittiRule : true;
  return records.filter(function (r) {
    return r.division === v.division && r.unit === v.unit && r.method === v.method &&
      (r.kitti_rule === null || r.kitti_rule === rule);
  });
}

/* Records of one grid cell, ordered by split. */
function cellRecords(recs, pair, sel, use, ind, alpha) {
  return recs.filter(function (r) {
    return r.pair === pair && r.condition_of_selection === sel && r.condition_of_use === use &&
      r.indicator === ind && r.alpha === alpha;
  }).sort(function (a, b) { return a.split - b.split; });
}

/* Counts in the order A, ?, N, - as in docs/results.md, e.g. "A1 ?3 N1". */
function codeSummary(cell) {
  var n = {};
  cell.forEach(function (r) { n[r.code] = (n[r.code] || 0) + 1; });
  return ["A", "?", "N", "-"].filter(function (c) { return n[c]; })
    .map(function (c) { return c + n[c]; }).join(" ");
}

function rowsFor(state) {
  var rows = [];
  PAIRS.forEach(function (p) {
    var dirs = p[1].concat(state.includeOwn ? p[2] : []);
    dirs.forEach(function (d) { rows.push({ pair: p[0], sel: d[0], use: d[1], own: d[0] === d[1] }); });
  });
  return rows;
}

function fmt(x) {
  if (x === null || x === undefined) return "";
  if (x === 0) return "0";
  return Math.abs(x) >= 1e-3 ? String(+x.toPrecision(4)) : x.toExponential(3);
}

if (typeof module !== "undefined") {
  module.exports = { PAIRS: PAIRS, ALPHAS: ALPHAS, VIEWS: VIEWS, selectRecords: selectRecords,
    cellRecords: cellRecords, codeSummary: codeSummary, rowsFor: rowsFor, alphaLabel: alphaLabel, fmt: fmt };
}

/* ---- page ---- */
if (typeof document !== "undefined") {
  (function () {
    var DATA = null;
    var state = { view: "frame", kittiRule: true, ind: "both", includeOwn: false };
    var $ = function (id) { return document.getElementById(id); };
    var outcomeName = {};
    OUTCOMES.forEach(function (o) { outcomeName[o[0]] = o[1]; });

    function el(tag, attrs, text) {
      var e = document.createElement(tag);
      for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
      if (text !== undefined) e.textContent = text;
      return e;
    }

    function square(code) {
      var cls = OUTCOMES.filter(function (o) { return o[0] === code; })[0][2];
      return el("span", { "class": "sq " + cls, "aria-hidden": "true" }, code);
    }

    function legend() {
      var box = $("legend");
      OUTCOMES.forEach(function (o) {
        var s = el("span");
        s.appendChild(square(o[0]));
        s.appendChild(document.createTextNode(o[0] + " " + o[1]));
        box.appendChild(s);
      });
      box.appendChild(el("span", {}, "squares: splits 0 to 4, left to right; † exploratory limit, not a safety target"));
    }

    function indicators() { return state.ind === "both" ? ["u_s", "u_e"] : [state.ind]; }

    function drawGrid() {
      var recs = selectRecords(DATA.records, state);
      var grid = $("grid");
      grid.textContent = "";
      var inds = indicators();
      var head = el("thead");
      var h1 = el("tr"), h2 = el("tr");
      h1.appendChild(el("th", { rowspan: "2", scope: "col" }, "condition of selection → condition of use"));
      inds.forEach(function (i) { h1.appendChild(el("th", { colspan: String(ALPHAS.length), scope: "colgroup" }, INDICATORS[i])); });
      inds.forEach(function () {
        ALPHAS.forEach(function (a) {
          h2.appendChild(el("th", { scope: "col", "class": a >= 0.05 ? "expl" : "" }, "α = " + alphaLabel(a)));
        });
      });
      head.appendChild(h1); head.appendChild(h2); grid.appendChild(head);
      var body = el("tbody");
      var last = null;
      rowsFor(state).forEach(function (row) {
        if (row.pair !== last) {
          var pr = el("tr");
          pr.appendChild(el("th", { colspan: String(1 + inds.length * ALPHAS.length), scope: "rowgroup", "class": "pair" }, row.pair));
          body.appendChild(pr);
          last = row.pair;
        }
        var tr = el("tr");
        var label = row.sel + " → " + row.use + (row.own ? " (own condition)" : "");
        tr.appendChild(el("th", { scope: "row", "class": "row" }, label));
        inds.forEach(function (ind) {
          ALPHAS.forEach(function (a) {
            var td = el("td", { "class": a >= 0.05 ? "expl" : "" });
            var cell = cellRecords(recs, row.pair, row.sel, row.use, ind, a);
            if (!cell.length) { td.className += " empty"; td.textContent = "no data"; tr.appendChild(td); return; }
            var summ = codeSummary(cell);
            var words = cell.map(function (r) { return "split " + r.split + " " + r.outcome; }).join(", ");
            var b = el("button", { type: "button", "class": "cell", "aria-pressed": "false",
              "aria-label": row.pair + ", " + label + ", " + INDICATORS[ind] + ", limit " + alphaLabel(a) + ": " + words });
            var sq = el("span", { "class": "sq-row" });
            cell.forEach(function (r) { sq.appendChild(square(r.code)); });
            b.appendChild(sq);
            b.appendChild(el("span", { "class": "codes", "aria-hidden": "true" }, summ));
            b.addEventListener("click", function () {
              Array.prototype.forEach.call(grid.querySelectorAll(".cell[aria-pressed=true]"),
                function (x) { x.setAttribute("aria-pressed", "false"); });
              b.setAttribute("aria-pressed", "true");
              drawDetail(row, label, ind, a, cell);
            });
            td.appendChild(b);
            tr.appendChild(td);
          });
        });
        body.appendChild(tr);
      });
      grid.appendChild(body);
      var v = VIEWS[state.view];
      grid.setAttribute("aria-label", "Outcomes, division " + v.division + ", unit " + v.unit + (v.method ? ", " + v.method : ""));
      $("status").textContent = recs.length + " records in this view.";
    }

    function drawDetail(row, label, ind, a, cell) {
      var post = cell[0].estimate === "Y";
      var v = VIEWS[state.view];
      $("detail").hidden = false;
      $("detail-title").textContent = (post ? "Post-hoc. " : "") + row.pair + ", " + label + ", " + INDICATORS[ind] +
        ", limit α = " + alphaLabel(a);
      var t = $("detail-table");
      t.textContent = "";
      var cols = ["split", "outcome", "τ", post ? "mean of Y" : "FAP estimate", "L", "U", "retention",
        "units, selection part", "units, test part", "source"];
      var tr = el("tr");
      cols.forEach(function (c) { tr.appendChild(el("th", { scope: "col" }, c)); });
      var th = el("thead"); th.appendChild(tr); t.appendChild(th);
      var tb = el("tbody");
      cell.forEach(function (r) {
        var x = el("tr");
        x.appendChild(el("td", {}, String(r.split)));
        x.appendChild(el("td", { "class": "l" }, r.code + " " + r.outcome));
        var none = r.code === "-" ? "none" : "not in file";
        [r.tau, r.A_hat, r.L, r.U, r.retention].forEach(function (val) {
          x.appendChild(el("td", val === null ? {} : { title: String(val) }, val === null ? none : fmt(val)));
        });
        [r.n_select_units, r.n_eval_units].forEach(function (val) {
          x.appendChild(el("td", {}, val === null ? "not in file" : String(val)));
        });
        var src = el("td", { "class": "l" });
        src.appendChild(el("a", { href: "https://github.com/milinpatel07/lidar-performance-target-applicability/blob/main/" + r.source_file + "#L" + r.source_row }, r.source_file + ", line " + r.source_row));
        x.appendChild(src);
        tb.appendChild(x);
      });
      t.appendChild(tb);
      var note = "Division " + v.division + ", unit " + v.unit + ". ";
      if (post) note += "Post-hoc: the estimate and [L, U] refer to the transformed sequence loss Y and are compared with α. ";
      note += "\"none\": no threshold was selected. \"not in file\": the source file has no such column. " +
        "Values are rounded to four significant digits; hover for the value in the file.";
      $("detail-note").textContent = note;
      $("detail-title").focus();
    }

    function sync() {
      var avail = ruleAvailable(state.view);
      $("f-rule").disabled = !avail;
      $("f-note").textContent = avail
        ? "The KITTI rule changes only the rows of KITTI distance and of the change of dataset and detector."
        : "Post-hoc entries exist with the KITTI rule only. Added after the parameters of the study were fixed.";
      $("detail").hidden = true;
      drawGrid();
    }

    function init(data) {
      DATA = data;
      legend();
      $("f-view").addEventListener("change", function (e) { state.view = e.target.value; sync(); });
      $("f-rule").addEventListener("change", function (e) { state.kittiRule = e.target.checked; sync(); });
      $("f-ind").addEventListener("change", function (e) { state.ind = e.target.value; sync(); });
      $("f-own").addEventListener("change", function (e) { state.includeOwn = e.target.checked; sync(); });
      var m = data.meta;
      $("meta").textContent = "Data file: " + m.records + " records, " + m.generator + " " + m.generator_version +
        ", " + m.date + ". SHA-256 of the source files are listed in its meta object.";
      sync();
    }

    fetch("data/outcomes.json")
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(init)
      .catch(function (e) {
        $("status").textContent = "data/outcomes.json could not be loaded (" + e.message + "). " +
          "Open the page through a web server, e.g. python -m http.server in the repository root.";
      });
  })();
}

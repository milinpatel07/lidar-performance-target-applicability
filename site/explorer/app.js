/* Results browser: reads data/outcomes.json (written by case_study/tools/build_explorer_data.py) and draws the outcome grid.
   Plain JavaScript without libraries, so that the page works offline. The pure functions at the top are also
   loaded by Node for testing (module.exports below; test: tests/test_explorer.mjs). */
"use strict";

var REPO = "https://github.com/milinpatel07/lidar-performance-target-applicability";
var DELTA = 0.05;   // error probability of the study (Sect. 4.4 of the paper)
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
/* division, unit and method are the labels of the data file; label is the term of the paper (Sect. 4.3). */
var VIEWS = {
  frame: { division: "by frame", unit: "frame", method: null,
    label: "frame-level evaluation (division by frame, frame as unit)" },
  seq_frame: { division: "by recorded sequence", unit: "frame", method: null,
    label: "third run (division by recorded sequence, frame as unit)" },
  seq_seq: { division: "by recorded sequence", unit: "recorded sequence", method: null,
    label: "sequence-level evaluation (division by recorded sequence, sequence as unit)" },
  postA: { division: "by recorded sequence", unit: "recorded sequence", method: "post-hoc Method A",
    label: "post-hoc Method A (sequence as unit; added after the outcomes were known)" },
  postB: { division: "by recorded sequence", unit: "recorded sequence", method: "post-hoc Method B",
    label: "post-hoc Method B (sequence as unit; added after the outcomes were known)" }
};
var DEFAULT_STATE = { view: "frame", kittiRule: true, ind: "both", limit: "all", includeOwn: false, cell: null };
var FRAME_UNIT_WARNING = "Frames of one recorded sequence are not independent, so the stated error probability " +
  "is not guaranteed for the outcomes in this view.";

function alphaLabel(a) {
  return { 0.01: "10⁻²", 0.001: "10⁻³", 0.0001: "10⁻⁴", 0.05: "0.05†", 0.1: "0.1†" }[a];
}

/* The KITTI rule can be switched off only where the files hold rows without it (not for post-hoc). */
function ruleAvailable(view) { return VIEWS[view].method === null; }

/* True if the view counts frames as units, so that its error probability rests on independent frames. */
function isFrameUnit(view) { return VIEWS[view].unit === "frame"; }

function selectRecords(records, state) {
  var v = VIEWS[state.view];
  var rule = ruleAvailable(state.view) ? state.kittiRule : true;
  return records.filter(function (r) {
    return r.division === v.division && r.unit === v.unit && r.method === v.method &&
      (r.kitti_rule === null || r.kitti_rule === rule);
  });
}

/* Limits shown as columns: all, or the one chosen. */
function alphasFor(state) {
  return state.limit === "all" ? ALPHAS.slice() : ALPHAS.filter(function (a) { return String(a) === String(state.limit); });
}

/* Records of the current view after the indicator, limit and own-condition filters (the rows of the CSV export). */
function visibleRecords(records, state) {
  var inds = state.ind === "both" ? ["u_s", "u_e"] : [state.ind];
  var alphas = alphasFor(state);
  return selectRecords(records, state).filter(function (r) {
    return inds.indexOf(r.indicator) >= 0 && alphas.indexOf(r.alpha) >= 0 && (state.includeOwn || !r.own_condition);
  });
}

/* Records of one grid cell, ordered by split. */
function cellRecords(recs, pair, sel, use, ind, alpha) {
  return recs.filter(function (r) {
    return r.pair === pair && r.condition_of_selection === sel && r.condition_of_use === use &&
      r.indicator === ind && r.alpha === alpha;
  }).sort(function (a, b) { return a.split - b.split; });
}

/* Counts in the order A, ?, N, - as in case_study/docs/results.md, e.g. "A1 ?3 N1". */
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

/* Minimum number of independent units without a false acceptance, Eq. 5 of the paper: n >= ln(d) / ln(1 - alpha),
   with d = delta for selecting and d = delta / 2 for testing a threshold. */
function minUnits(alpha, d) {
  return Math.ceil(Math.log(d) / Math.log(1 - alpha));
}

/* Link to a line of a result file; ?plain=1 makes GitHub show numbered lines also for CSV files. */
function sourceUrl(file, row) {
  return REPO + "/blob/main/" + file + "?plain=1#L" + row;
}

/* Logarithmic position in [x0, x1] of v on the axis lo..hi (values at or below lo are drawn at x0). */
function logX(v, lo, hi, x0, x1) {
  var c = Math.min(Math.max(v, lo), hi);
  return x0 + (x1 - x0) * (Math.log(c) - Math.log(lo)) / (Math.log(hi) - Math.log(lo));
}

/* Geometry of the strip of one split: interval [L, U] and limit alpha on a log axis of the FAP; test units n against
   the Eq. 5 minimum for testing on a log axis of n. Returns null parts where a value is missing. */
function stripGeometry(r, width) {
  var x0 = 4, x1 = width - 4, lo = 1e-5, hi = 1;
  var g = { width: width, interval: null, units: null };
  if (r.L !== null && r.U !== null && r.L !== undefined && r.U !== undefined) {
    g.interval = { xL: logX(r.L, lo, hi, x0, x1), xU: logX(r.U, lo, hi, x0, x1), xA: logX(r.alpha, lo, hi, x0, x1),
      lowClamped: r.L <= lo, meetsLimit: r.U <= r.alpha, exceedsLimit: r.L > r.alpha };
  }
  if (r.n_eval_units !== null && r.n_eval_units !== undefined) {
    var nMin = minUnits(r.alpha, DELTA / 2), nlo = 1, nhi = 1e5;
    g.units = { n: r.n_eval_units, nMin: nMin, xN: logX(r.n_eval_units, nlo, nhi, x0, x1),
      xMin: logX(nMin, nlo, nhi, x0, x1), reached: r.n_eval_units >= nMin };
  }
  return g;
}

/* URL hash of the page state, e.g. #view=frame&rule=1&ind=both&limit=all&own=0&cell=... */
function encodeHash(s) {
  var p = ["view=" + s.view, "rule=" + (s.kittiRule ? 1 : 0), "ind=" + s.ind, "limit=" + s.limit, "own=" + (s.includeOwn ? 1 : 0)];
  if (s.cell) p.push("cell=" + encodeURIComponent([s.cell.pair, s.cell.sel, s.cell.use, s.cell.ind, s.cell.alpha].join("|")));
  return "#" + p.join("&");
}

function decodeHash(h) {
  var s = {}, k;
  for (k in DEFAULT_STATE) s[k] = DEFAULT_STATE[k];
  (h || "").replace(/^#/, "").split("&").forEach(function (kv) {
    var i = kv.indexOf("="); if (i < 0) return;
    var key = kv.slice(0, i), val = kv.slice(i + 1);
    if (key === "view" && VIEWS[val]) s.view = val;
    else if (key === "rule") s.kittiRule = val !== "0";
    else if (key === "ind" && (val === "both" || INDICATORS[val])) s.ind = val;
    else if (key === "limit" && (val === "all" || ALPHAS.map(String).indexOf(val) >= 0)) s.limit = val;
    else if (key === "own") s.includeOwn = val === "1";
    else if (key === "cell") {
      var c = decodeURIComponent(val).split("|");
      if (c.length === 5 && INDICATORS[c[3]] && ALPHAS.indexOf(+c[4]) >= 0)
        s.cell = { pair: c[0], sel: c[1], use: c[2], ind: c[3], alpha: +c[4] };
    }
  });
  if (s.cell && s.cell.sel === s.cell.use) s.includeOwn = true;
  return s;
}

var CSV_COLUMNS = ["view", "pair", "condition_of_selection", "condition_of_use", "indicator", "alpha", "limit_type",
  "split", "outcome", "tau", "estimate", "A_hat", "L", "U", "retention", "n_select_units", "n_eval_units",
  "kitti_rule", "source_file", "source_row"];

function csvField(v) {
  if (v === null || v === undefined) return "";
  var s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

/* CSV of the records of the current view; the column view holds the term of the paper. */
function toCSV(recs, view) {
  var lines = [CSV_COLUMNS.join(",")];
  recs.forEach(function (r) {
    lines.push(CSV_COLUMNS.map(function (c) { return csvField(c === "view" ? VIEWS[view].label : r[c]); }).join(","));
  });
  return lines.join("\n") + "\n";
}

if (typeof module !== "undefined") {
  module.exports = { PAIRS: PAIRS, ALPHAS: ALPHAS, VIEWS: VIEWS, DELTA: DELTA, DEFAULT_STATE: DEFAULT_STATE,
    FRAME_UNIT_WARNING: FRAME_UNIT_WARNING, selectRecords: selectRecords, visibleRecords: visibleRecords,
    alphasFor: alphasFor, cellRecords: cellRecords, codeSummary: codeSummary, rowsFor: rowsFor, alphaLabel: alphaLabel,
    fmt: fmt, isFrameUnit: isFrameUnit, minUnits: minUnits, sourceUrl: sourceUrl, logX: logX,
    stripGeometry: stripGeometry, encodeHash: encodeHash, decodeHash: decodeHash, toCSV: toCSV };
}

/* ---- page ---- */
if (typeof document !== "undefined") {
  (function () {
    var DATA = null;
    var state = decodeHash(location.hash);
    var $ = function (id) { return document.getElementById(id); };
    var SVG = "http://www.w3.org/2000/svg";

    function el(tag, attrs, text) {
      var e = document.createElement(tag);
      for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
      if (text !== undefined) e.textContent = text;
      return e;
    }

    function sv(tag, attrs, text) {
      var e = document.createElementNS(SVG, tag);
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
      box.appendChild(el("span", {}, "squares: splits 0 to 4, left to right; † exploratory limit, which defines no performance target"));
    }

    function indicators() { return state.ind === "both" ? ["u_s", "u_e"] : [state.ind]; }

    function writeHash() {
      var h = encodeHash(state);
      if (location.hash !== h) history.replaceState(null, "", h);
    }

    function drawGrid() {
      var recs = selectRecords(DATA.records, state);
      var grid = $("grid");
      grid.textContent = "";
      var inds = indicators(), alphas = alphasFor(state);
      $("unit-banner").hidden = !isFrameUnit(state.view);
      var head = el("thead");
      var h1 = el("tr"), h2 = el("tr");
      h1.appendChild(el("th", { rowspan: "2", scope: "col" }, "condition of selection → condition of use"));
      inds.forEach(function (i) { h1.appendChild(el("th", { colspan: String(alphas.length), scope: "colgroup" }, INDICATORS[i])); });
      inds.forEach(function () {
        alphas.forEach(function (a) {
          h2.appendChild(el("th", { scope: "col", "class": a >= 0.05 ? "expl" : "" }, "α = " + alphaLabel(a)));
        });
      });
      head.appendChild(h1); head.appendChild(h2); grid.appendChild(head);
      var body = el("tbody");
      var last = null, selected = null;
      rowsFor(state).forEach(function (row) {
        if (row.pair !== last) {
          var pr = el("tr");
          pr.appendChild(el("th", { colspan: String(1 + inds.length * alphas.length), scope: "rowgroup", "class": "pair" }, row.pair));
          body.appendChild(pr);
          last = row.pair;
        }
        var tr = el("tr");
        var label = row.sel + " → " + row.use + (row.own ? " (own condition)" : "");
        tr.appendChild(el("th", { scope: "row", "class": "row" }, label));
        inds.forEach(function (ind) {
          alphas.forEach(function (a) {
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
            var open = function (focus) {
              Array.prototype.forEach.call(grid.querySelectorAll(".cell[aria-pressed=true]"),
                function (x) { x.setAttribute("aria-pressed", "false"); });
              b.setAttribute("aria-pressed", "true");
              state.cell = { pair: row.pair, sel: row.sel, use: row.use, ind: ind, alpha: a };
              writeHash();
              drawDetail(row, label, ind, a, cell, focus);
            };
            b.addEventListener("click", function () { open(true); });
            var c = state.cell;
            if (c && c.pair === row.pair && c.sel === row.sel && c.use === row.use && c.ind === ind && c.alpha === a) selected = open;
            td.appendChild(b);
            tr.appendChild(td);
          });
        });
        body.appendChild(tr);
      });
      grid.appendChild(body);
      grid.setAttribute("aria-label", "Outcomes, " + VIEWS[state.view].label);
      $("status").textContent = visibleRecords(DATA.records, state).length + " records in this view (" + VIEWS[state.view].label + ").";
      if (selected) selected(false); else { state.cell = null; $("detail").hidden = true; }
    }

    function strip(r) {
      var g = stripGeometry(r, 170);
      var s = sv("svg", { width: "170", height: "34", viewBox: "0 0 170 34", "class": "strip", role: "img" });
      var words = [];
      if (g.interval) {
        var i = g.interval;
        s.appendChild(sv("line", { x1: "4", x2: "166", y1: "9", y2: "9", "class": "axis" }));
        s.appendChild(sv("line", { x1: String(i.xA), x2: String(i.xA), y1: "2", y2: "16", "class": "limit" }));
        s.appendChild(sv("line", { x1: String(i.xL), x2: String(Math.max(i.xU, i.xL + 1)), y1: "9", y2: "9",
          "class": "iv " + (i.meetsLimit ? "ok" : i.exceedsLimit ? "bad" : "mid") }));
        words.push("[L, U] = [" + fmt(r.L) + ", " + fmt(r.U) + "] against α = " + r.alpha +
          (i.lowClamped ? " (L below 1e-5 drawn at the axis start)" : ""));
      }
      if (g.units) {
        var u = g.units;
        s.appendChild(sv("line", { x1: "4", x2: "166", y1: "27", y2: "27", "class": "axis" }));
        s.appendChild(sv("rect", { x: "4", y: "24", width: String(Math.max(u.xN - 4, 1)), height: "6", "class": "nbar " + (u.reached ? "ok" : "bad") }));
        s.appendChild(sv("line", { x1: String(u.xMin), x2: String(u.xMin), y1: "21", y2: "33", "class": "limit" }));
        words.push(u.n + " test units against the Eq. 5 minimum " + u.nMin + (u.reached ? " (reached)" : " (not reached)"));
      }
      if (!words.length) return el("span", { "class": "note" }, "no interval");
      s.setAttribute("aria-label", words.join("; "));
      s.appendChild(sv("title", {}, words.join("; ")));
      return s;
    }

    function drawDetail(row, label, ind, a, cell, focus) {
      var post = cell[0].estimate === "Y";
      var v = VIEWS[state.view];
      $("detail").hidden = false;
      $("detail-title").textContent = (post ? "Post-hoc. " : "") + row.pair + ", " + label + ", " + INDICATORS[ind] +
        ", limit α = " + alphaLabel(a);
      var t = $("detail-table");
      t.textContent = "";
      var cols = ["split", "outcome", "τ", post ? "mean of Y" : "FAP estimate", "L", "U", "retention",
        "units, selection part", "units, test part", "[L, U] against α; test units against Eq. 5", "source"];
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
        var st = el("td", { "class": "l" });
        st.appendChild(strip(r));
        x.appendChild(st);
        var src = el("td", { "class": "l" });
        src.appendChild(el("a", { href: sourceUrl(r.source_file, r.source_row) }, r.source_file + ", line " + r.source_row));
        x.appendChild(src);
        tb.appendChild(x);
      });
      t.appendChild(tb);
      var note = v.label + ". ";
      if (isFrameUnit(state.view)) note += FRAME_UNIT_WARNING + " ";
      if (post) note += "Post-hoc: the estimate and [L, U] refer to the transformed sequence loss Y and are compared with α. ";
      note += "\"none\": no threshold selected (the lowest candidate threshold fails in the condition of selection). " +
        "\"not in file\": the source file has no such column. Strip: upper line [L, U] on a log axis from 10⁻⁵ to 1 with α " +
        "as a vertical mark; lower bar the test units on a log axis from 1 to 10⁵ with the Eq. 5 minimum for testing, " +
        "ln(δ/2)/ln(1 − α) with δ = 0.05, as a vertical mark (drawn only where the file records the units). " +
        "Values are rounded to four significant digits; hover for the value in the file.";
      $("detail-note").textContent = note;
      if (focus) $("detail-title").focus();
    }

    function downloadCSV() {
      var recs = visibleRecords(DATA.records, state);
      var blob = new Blob([toCSV(recs, state.view)], { type: "text/csv" });
      var a = el("a", { href: URL.createObjectURL(blob), download: "outcomes_" + state.view + ".csv" });
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    }

    function sync() {
      var avail = ruleAvailable(state.view);
      $("f-view").value = state.view; $("f-rule").checked = state.kittiRule; $("f-ind").value = state.ind;
      $("f-limit").value = String(state.limit); $("f-own").checked = state.includeOwn;
      $("f-rule").disabled = !avail;
      $("f-note").textContent = avail
        ? "The KITTI rule changes only the rows of KITTI distance and of the change of dataset and detector."
        : "Post-hoc entries exist with the KITTI rule only. Added after the parameters of the study were fixed.";
      writeHash();
      drawGrid();
    }

    function init(data) {
      DATA = data;
      legend();
      var change = function (key, get) {
        return function (e) { state[key] = get(e.target); state.cell = null; sync(); };
      };
      $("f-view").addEventListener("change", change("view", function (t) { return t.value; }));
      $("f-rule").addEventListener("change", change("kittiRule", function (t) { return t.checked; }));
      $("f-ind").addEventListener("change", change("ind", function (t) { return t.value; }));
      $("f-limit").addEventListener("change", change("limit", function (t) { return t.value; }));
      $("f-own").addEventListener("change", change("includeOwn", function (t) { return t.checked; }));
      $("f-csv").addEventListener("click", downloadCSV);
      window.addEventListener("hashchange", function () {
        if (location.hash !== encodeHash(state)) { state = decodeHash(location.hash); sync(); }
      });
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
          "Open the page through a web server, e.g. python3 -m http.server -d site in the repository root.";
      });
  })();
}

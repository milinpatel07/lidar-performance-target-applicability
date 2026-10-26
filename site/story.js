/* The idea in two minutes: eight scenes on one SVG stage. Marks are schematic (seeded), not data. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var C = { correct: "#0072b2", wrong: "#d55e00", appl: "#009e73", notdet: "#e6c700", gate: "#6a3d9a",
            applText: "#007a5a", wrongText: "#b34700",
            ink: "#1a1a1a", grey: "#5a5a5a", light: "#eef2f7", rain: "#9fb3c8" };
  var X0 = 60, X1 = 660, GATE = 360, Y0 = 110, Y1 = 290;

  var seed = 11;
  function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
  function beta(a, b) {   /* mean-matched draw from a small sum of uniforms; enough for a schematic */
    var m = a / (a + b), s = 0;
    for (var i = 0; i < 4; i++) s += rnd();
    return Math.min(0.98, Math.max(0.02, m + (s / 4 - 0.5) * 0.55));
  }

  var marks = [];
  for (var i = 0; i < 46; i++) marks.push({ wrong: false, u: beta(2, 6) });
  for (var j = 0; j < 14; j++) marks.push({ wrong: true, u: j < 2 ? 0.38 + 0.08 * j : beta(6, 2), rain: j >= 2 && j < 8 });
  marks.forEach(function (m) {
    m.cloudX = 160 + rnd() * 400; m.cloudY = 80 + rnd() * 230; m.y = Y0 + 10 + rnd() * (Y1 - Y0 - 20);
    m.rainU = m.rain ? Math.max(0.05, m.u - 0.3 - rnd() * 0.15) : m.u;
  });
  function xOf(u) { return X0 + u * (X1 - X0); }

  function el(name, attrs, parent) {
    var e = document.createElementNS(NS, name);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function text(parent, x, y, s, size, weight, fill, anchor) {
    var t = el("text", { x: x, y: y, "font-size": size || 14, "font-weight": weight || "normal", fill: fill || C.ink,
      "text-anchor": anchor || "start", "font-family": "Segoe UI, Helvetica, Arial, sans-serif" }, parent);
    t.textContent = s;
    return t;
  }

  var svg = document.getElementById("stage");
  el("rect", { width: 720, height: 380, fill: "#ffffff" }, svg);
  var L = {};
  function layer(name) { L[name] = el("g", { "class": "layer", opacity: 0 }, svg); return L[name]; }

  /* rain backdrop */
  var rain = layer("rain");
  el("rect", { x: 0, y: 0, width: 720, height: 380, fill: "#f2f6fa" }, rain);
  for (var r = 0; r < 70; r++) {
    var rx = rnd() * 720, ry = rnd() * 380;
    el("line", { x1: rx, y1: ry, x2: rx - 6, y2: ry + 16, stroke: C.rain, "stroke-width": 1.2 }, rain);
  }
  text(rain, 700, 32, "rain", 16, "bold", "#5f7a94", "end");

  /* axis, passed-on region, gate */
  var axis = layer("axis");
  el("line", { x1: X0, y1: Y1 + 18, x2: X1, y2: Y1 + 18, stroke: C.ink, "stroke-width": 1.5 }, axis);
  text(axis, X0, Y1 + 40, "sure", 13, "normal", C.grey);
  text(axis, X1, Y1 + 40, "unsure", 13, "normal", C.grey, "end");
  text(axis, (X0 + X1) / 2, Y1 + 40, "how unsure the detector is about each report", 13, "normal", C.grey, "middle");
  var pass = layer("pass");
  el("rect", { x: X0, y: Y0 - 14, width: GATE - X0, height: Y1 - Y0 + 28, fill: C.light, rx: 6 }, pass);
  text(pass, X0 + 8, Y0 - 22, "passed on to the car's planning", 13, "bold", C.grey);
  text(pass, GATE + 8, Y0 - 22, "rejected", 13, "bold", C.grey);
  var gate = layer("gate");
  el("line", { x1: GATE, y1: Y0 - 40, x2: GATE, y2: Y1 + 26, stroke: C.gate, "stroke-width": 3, "stroke-dasharray": "8 5" }, gate);
  text(gate, GATE, Y0 - 46, "gate (threshold)", 14, "bold", C.gate, "middle");

  /* marks */
  var markLayer = el("g", {}, svg);
  marks.forEach(function (m) {
    var g = el("g", { "class": "mark" }, markLayer);
    if (m.wrong) el("path", { d: "M-6,-6 L6,6 M-6,6 L6,-6", stroke: C.wrong, "stroke-width": 3, "stroke-linecap": "round" }, g);
    else el("circle", { r: 6, fill: C.correct }, g);
    m.node = g;
  });
  var legend = layer("legend");
  el("circle", { cx: 30, cy: 360, r: 6, fill: C.correct }, legend);
  text(legend, 42, 365, "right report", 13, "normal", C.grey);
  el("path", { d: "M144,354 L156,366 M144,366 L156,354", stroke: C.wrong, "stroke-width": 3, "stroke-linecap": "round" }, legend);
  text(legend, 164, 365, "wrong report", 13, "normal", C.grey);

  /* decision: one bar against the limit, then the three answers */
  function limitLine(parent, y) {
    el("line", { x1: 60, y1: y, x2: 680, y2: y, stroke: C.ink, "stroke-width": 2, "stroke-dasharray": "7 5" }, parent);
    text(parent, 60, y - 10, "target: at most this share wrong", 13, "bold", C.ink, "start");
  }
  function bar(parent, x, lo, hi, col) {
    el("line", { x1: x, y1: lo, x2: x, y2: hi, stroke: col, "stroke-width": 16, "stroke-linecap": "round" }, parent);
  }
  var one = layer("one");
  limitLine(one, 160);
  bar(one, 360, 120, 230, C.notdet);
  el("circle", { cx: 360, cy: 175, r: 5, fill: C.ink }, one);
  text(one, 390, 120, "the share of wrong reports that pass in rain", 13, "normal", C.grey);
  text(one, 390, 138, "lies somewhere on this bar", 13, "normal", C.grey);
  var three = layer("three");
  limitLine(three, 160);
  [[160, 205, 260, C.appl, "applicable", "target met"], [360, 120, 220, C.notdet, "not determined", "not enough data"],
   [560, 70, 140, C.wrong, "not applicable", "target missed"]].forEach(function (b) {
    bar(three, b[0], b[1], b[2], b[3]);
    text(three, b[0], 300, b[4], 16, "bold", b[3] === C.notdet ? "#7a6a00" : (b[3] === C.appl ? C.applText : C.wrongText), "middle");
    text(three, b[0], 320, b[5], 13, "normal", C.grey, "middle");
  });

  /* independent units: three drives, bar shrinking */
  var units = layer("units");
  ["#cfe3f3", "#fde0c8", "#d6efe5"].forEach(function (col, d) {
    var x0 = 40 + d * 220;
    el("rect", { x: x0, y: 60, width: 200, height: 110, rx: 10, fill: "none", stroke: C.grey, "stroke-dasharray": "5 4" }, units);
    text(units, x0 + 10, 80, "drive " + (d + 1), 13, "bold", C.grey);
    for (var f = 0; f < 8; f++) el("rect", { x: x0 + 12 + (f % 4) * 46, y: 90 + Math.floor(f / 4) * 36, width: 40, height: 28,
      rx: 4, fill: col }, units);
    text(units, x0 + 100, 190, "= 1 unit", 14, "bold", C.ink, "middle");
  });
  var shrink = el("g", {}, units);
  limitLine(shrink, 250);
  var longBar = el("g", { "class": "layer", opacity: 1 }, shrink);
  bar(longBar, 360, 225, 335, C.notdet);
  text(longBar, 390, 290, "few drives: not determined", 13, "bold", "#7a6a00");
  var shortBar = el("g", { "class": "layer", opacity: 0 }, shrink);
  bar(shortBar, 360, 262, 302, C.appl);
  text(shortBar, 390, 290, "many drives: decided (here applicable)", 13, "bold", C.applText);

  var scenes = [
    { t: "A detector reports what it sees",
      p: ["An automated car has an object detector. It looks at the road and reports the objects it finds.",
          "Most reports are right (blue dots). Some are wrong (orange crosses): an object where there is none, or in the wrong place."],
      show: ["legend"], pos: "cloud" },
    { t: "Each report comes with an uncertainty",
      p: ["The detector also says how unsure it is about each report. Right reports tend to be sure, wrong reports tend to be unsure, but not always."],
      show: ["legend", "axis"], pos: "u" },
    { t: "A gate passes only the sure reports",
      p: ["An uncertainty threshold works like a gate: reports left of it are passed on to the planning of the car, the others are rejected.",
          "A few wrong reports still pass. The gate is placed so that their share stays below a limit, for example 1 in 100. This limit is the performance target."],
      show: ["legend", "axis", "pass", "gate"], pos: "u" },
    { t: "Then the weather changes",
      p: ["The gate was placed on recordings from clear weather. In rain, some wrong reports look sure and move left, while the gate stays where it is.",
          "So more wrong reports pass. Is the target still met in rain? A safety analysis according to ISO 21448 (safety of the intended functionality) asks this for each potential triggering condition it identifies."],
      show: ["legend", "axis", "pass", "gate", "rain"], pos: "rain" },
    { t: "Measure it on recorded rain data",
      p: ["The applicability test keeps the gate unchanged and checks it on recordings made in rain.",
          "It does not give one number but a range (the bar) in which the true share of wrong passed-on reports lies, with a stated chance of being wrong."],
      show: ["one"], pos: "hide" },
    { t: "Three possible answers",
      p: ["If the whole bar lies below the limit, the target is met: applicable. If the whole bar lies above, it is missed: not applicable.",
          "If the bar crosses the limit, the data cannot decide: not determined. That is not a pass; it means: record more.",
          "A gate that rejects almost every report meets any limit. So every applicable answer is reported with the share of right reports the gate still passes on (the retention)."],
      show: ["three"], pos: "hide" },
    { t: "Count drives, not frames",
      p: ["A camera or LiDAR records many snapshots (frames) per drive, and frames of one drive repeat each other: the same road, weather and traffic. Ten frames of one drive do not count as ten independent pieces of evidence.",
          "The stated chance of being wrong holds only if the units counted are independent, so the test counts drives. More drives make the bar shorter until it lies wholly on one side of the limit (here below it; it can equally end above it). The test also gives the least number of drives needed to show that the target is met."],
      show: ["units"], pos: "hide", shrink: true },
    { t: "Where to go next",
      p: ["The same test, step by step and with the statistics, is in the walk-through. You can also run it on your own data in this browser."],
      html: "<div class='next-cards'><a href='interactive/walkthrough.html'><strong>Walk-through</strong>the test in seven steps, with the statistics</a>" +
            "<a href='interactive/own-data.html'><strong>Your own data</strong>run the test on a CSV file in the browser</a>" +
            "<a href='explorer/'><strong>Results browser</strong>every outcome of the case study on KITTI and nuScenes</a>" +
            "<a href='https://github.com/milinpatel07/lidar-performance-target-applicability'><strong>Code and paper</strong>Python package, documentation, citation</a></div>",
      show: ["three"], pos: "hide" }
  ];

  var cur = 0;
  var titleEl = document.getElementById("scene-title"), textEl = document.getElementById("scene-text");
  var back = document.getElementById("back"), next = document.getElementById("next"), dots = document.getElementById("dots");
  scenes.forEach(function (s, k) {
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("aria-label", "Scene " + (k + 1) + ": " + s.t);
    b.addEventListener("click", function () { go(k); });
    dots.appendChild(b);
  });

  function place(mode) {
    marks.forEach(function (m) {
      var x, y = m.y, o = 1;
      if (mode === "cloud") { x = m.cloudX; y = m.cloudY; }
      else if (mode === "rain") x = xOf(m.rainU);
      else x = xOf(m.u);
      if (mode === "hide") { x = xOf(m.u); o = 0; }
      m.node.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)";
      m.node.style.opacity = o;
    });
  }

  function go(k) {
    cur = Math.max(0, Math.min(scenes.length - 1, k));
    var s = scenes[cur];
    titleEl.textContent = (cur + 1) + ". " + s.t;
    textEl.innerHTML = s.p.map(function (q) { return "<p>" + q + "</p>"; }).join("") + (s.html || "");
    Object.keys(L).forEach(function (n) { L[n].setAttribute("opacity", s.show.indexOf(n) >= 0 ? 1 : 0); });
    place(s.pos);
    longBar.setAttribute("opacity", 1); shortBar.setAttribute("opacity", 0);
    if (s.shrink) setTimeout(function () {   /* more independent drives: a shorter bar, below the limit */
      if (scenes[cur].shrink) { longBar.setAttribute("opacity", 0); shortBar.setAttribute("opacity", 1); }
    }, 1400);
    back.disabled = cur === 0;
    next.disabled = cur === scenes.length - 1;
    Array.prototype.forEach.call(dots.children, function (b, i) {
      if (i === cur) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
    });
    if (history.replaceState) history.replaceState(null, "", "#" + (cur + 1));
  }

  back.addEventListener("click", function () { go(cur - 1); });
  next.addEventListener("click", function () { go(cur + 1); });
  document.addEventListener("keydown", function (e) {
    if (e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.key === "ArrowRight") go(cur + 1);
    if (e.key === "ArrowLeft") go(cur - 1);
  });
  var start = parseInt((location.hash || "#1").slice(1), 10);
  go(isNaN(start) ? 0 : start - 1);
})();

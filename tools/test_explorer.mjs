// Tests of the functions of explorer/app.js that do not touch the page, and of explorer/data/outcomes.json against
// the counts of the paper. Run from the repository root: node tools/test_explorer.mjs (Node 18 or later, no packages).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const X = require(join(root, "explorer", "app.js"));
const DATA = JSON.parse(readFileSync(join(root, "explorer", "data", "outcomes.json"), "utf8"));
const EXPL = [0.01, 0.05, 0.1];
const state = (o) => Object.assign({}, X.DEFAULT_STATE, o);
const transfers = (view) => X.selectRecords(DATA.records, state({ view })).filter((r) => !r.own_condition && EXPL.includes(r.alpha));
const decided = (recs) => recs.filter((r) => r.code === "A" || r.code === "N");

test("minUnits follows Eq. 5 (299 and 368 at 1e-2, 2,995 at 1e-3)", () => {
  assert.equal(X.minUnits(0.01, 0.05), 299);
  assert.equal(X.minUnits(0.01, 0.025), 368);
  assert.equal(X.minUnits(0.001, 0.05), 2995);
  assert.equal(X.minUnits(0.1, 0.05), 29);
});

test("view labels use the terms of the paper and match index.html", () => {
  assert.match(X.VIEWS.frame.label, /^frame-level evaluation/);
  assert.match(X.VIEWS.seq_seq.label, /^sequence-level evaluation/);
  assert.match(X.VIEWS.seq_frame.label, /^third run/);
  const html = readFileSync(join(root, "explorer", "index.html"), "utf8");
  for (const [k, v] of Object.entries(X.VIEWS)) {
    assert.ok(html.includes(`<option value="${k}">${v.label}</option>`), `index.html option ${k}`);
  }
  assert.ok(html.includes('id="unit-banner"'));
});

test("frame-unit views are flagged, sequence-unit views are not", () => {
  assert.equal(X.isFrameUnit("frame"), true);
  assert.equal(X.isFrameUnit("seq_frame"), true);
  assert.equal(X.isFrameUnit("seq_seq"), false);
  assert.equal(X.isFrameUnit("postA"), false);
});

test("frame-level evaluation: 168 of 240 transfer outcomes applicable or not applicable (Sect. 5.1)", () => {
  const t = transfers("frame");
  assert.equal(t.length, 240);
  assert.equal(decided(t).length, 168);
});

test("sequence-level evaluation: 5 of 240, all on nuScenes and applicable at 0.1 (Sect. 5.1)", () => {
  const t = transfers("seq_seq");
  assert.equal(t.length, 240);
  const d = decided(t);
  assert.equal(d.length, 5);
  assert.ok(d.every((r) => r.pair.startsWith("nuScenes") && r.code === "A" && r.alpha === 0.1));
});

test("cellRecords and codeSummary", () => {
  const recs = X.selectRecords(DATA.records, state({}));
  const cell = X.cellRecords(recs, "change of dataset and detector", "nuScenes", "KITTI", "u_s", 0.01);
  assert.deepEqual(cell.map((r) => r.split), [0, 1, 2, 3, 4]);
  assert.equal(X.codeSummary(cell), "N5");
  assert.equal(X.codeSummary([{ code: "A" }, { code: "?" }, { code: "A" }, { code: "N" }]), "A2 ?1 N1");
});

test("visibleRecords applies indicator, limit and own-condition filters", () => {
  const all = X.visibleRecords(DATA.records, state({ includeOwn: true }));
  const one = X.visibleRecords(DATA.records, state({ ind: "u_s", limit: "0.1" }));
  assert.ok(one.length > 0 && one.length < all.length);
  assert.ok(one.every((r) => r.indicator === "u_s" && r.alpha === 0.1 && !r.own_condition));
  assert.deepEqual(X.alphasFor(state({ limit: "0.001" })), [0.001]);
  assert.equal(X.alphasFor(state({})).length, 5);
});

test("sourceUrl shows numbered lines (?plain=1#L<n>)", () => {
  assert.equal(X.sourceUrl("results/m7_scene_split/m7_scene_split.csv", 12),
    "https://github.com/milinpatel07/lidar-performance-target-applicability/blob/main/results/m7_scene_split/m7_scene_split.csv?plain=1#L12");
});

test("hash state round trip and defaults", () => {
  const s = state({ view: "seq_seq", kittiRule: false, ind: "u_e", limit: "0.05",
    cell: { pair: "nuScenes weather", sel: "clear", use: "rain", ind: "u_e", alpha: 0.05 } });
  const back = X.decodeHash(X.encodeHash(s));
  assert.deepEqual(back, s);
  assert.deepEqual(X.decodeHash(""), X.DEFAULT_STATE);
  assert.deepEqual(X.decodeHash("#view=nonsense&limit=7&ind=x"), X.DEFAULT_STATE);
  const own = X.decodeHash("#cell=" + encodeURIComponent("nuScenes weather|rain|rain|u_e|0.1"));
  assert.equal(own.includeOwn, true);
});

test("stripGeometry places [L, U], alpha and the units on their axes", () => {
  const g = X.stripGeometry({ L: 0.001, U: 0.006, alpha: 0.01, n_eval_units: 2209 }, 170);
  assert.ok(g.interval.xL < g.interval.xU && g.interval.xU < g.interval.xA);
  assert.equal(g.interval.meetsLimit, true);
  assert.equal(g.units.nMin, 368);
  assert.equal(g.units.reached, true);
  const h = X.stripGeometry({ L: 0, U: 0.2, alpha: 0.1, n_eval_units: null }, 170);
  assert.equal(h.interval.lowClamped, true);
  assert.equal(h.units, null);
  assert.equal(X.stripGeometry({ L: null, U: null, alpha: 0.1, n_eval_units: 21 }, 170).units.reached, false);
});

test("toCSV writes one line per record with the view term and quotes fields with commas", () => {
  const recs = X.visibleRecords(DATA.records, state({ ind: "u_s", limit: "0.01" }));
  const csv = X.toCSV(recs, "frame");
  const lines = csv.trimEnd().split("\n");
  assert.equal(lines.length, recs.length + 1);
  assert.ok(lines[0].startsWith("view,pair,"));
  assert.ok(lines[1].startsWith('"frame-level evaluation (division by frame, frame as unit)",'));
});

// Helpers shared by the interactive pages: SVG elements, scales, axes, number format, tooltip.
(function (root) {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function text(parent, x, y, s, attrs) {
    const t = el("text", Object.assign({ x: x, y: y }, attrs || {}), parent);
    t.textContent = s;
    return t;
  }
  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  function lin(d0, d1, r0, r1) {
    const f = v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
    f.domain = [d0, d1];
    return f;
  }
  function log(d0, d1, r0, r1) {
    const a = Math.log10(d0), b = Math.log10(d1);
    const f = v => r0 + (Math.log10(Math.min(Math.max(v, d0), d1)) - a) / (b - a) * (r1 - r0);
    f.domain = [d0, d1];
    return f;
  }

  // number format: up to `sig` significant digits, exponent form below 1e-3
  function fmt(v, sig) {
    if (v === null || v === undefined || Number.isNaN(v)) return "–";
    sig = sig || 4;
    if (v === 0) return "0";
    const a = Math.abs(v);
    if (a < 1e-3 || a >= 1e6) {
      const e = Math.floor(Math.log10(a));
      const m = v / Math.pow(10, e);
      return (+m.toPrecision(sig)).toString() + "·10" + sup(e);
    }
    return (+v.toPrecision(sig)).toString();
  }
  function sup(e) {
    const m = { "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };
    return String(e).split("").map(c => m[c]).join("");
  }
  function int(v) { return Math.round(v).toLocaleString("en-US"); }
  function limitLabel(a) {
    const e = Math.log10(a);
    if (Math.abs(e - Math.round(e)) < 1e-9 && a < 0.05) return "10" + sup(Math.round(e));
    return String(a);
  }

  // tooltip that follows the pointer; content is plain text lines
  let tipEl = null;
  function tip(lines, evt) {
    if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("role", "tooltip"); document.body.appendChild(tipEl); }
    if (!lines) { tipEl.style.display = "none"; return; }
    tipEl.textContent = "";
    lines.forEach((l, i) => { if (i) tipEl.appendChild(document.createElement("br")); tipEl.appendChild(document.createTextNode(l)); });
    tipEl.style.display = "block";
    const x = Math.min(evt.clientX + 12, window.innerWidth - tipEl.offsetWidth - 8);
    const y = Math.min(evt.clientY + 12, window.innerHeight - tipEl.offsetHeight - 8);
    tipEl.style.left = x + "px"; tipEl.style.top = y + "px";
  }

  // log axis ticks at powers of ten within [d0, d1]
  function decades(d0, d1) {
    const out = [];
    for (let e = Math.ceil(Math.log10(d0) - 1e-9); e <= Math.floor(Math.log10(d1) + 1e-9); e++) out.push(Math.pow(10, e));
    return out;
  }

  root.UI = { el, text, clear, lin, log, fmt, int, sup, limitLabel, tip, decades };
})(this);

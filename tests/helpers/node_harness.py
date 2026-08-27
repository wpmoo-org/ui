from __future__ import annotations

import json


# Shared Node harness: a minimal, permissive DOM stub good enough to run the
# real MooChart (and the Chart.js it bundles) outside a browser.
NODE_PREAMBLE = """
import MooChart from "./src/js/components/chart.js";

globalThis.window = globalThis;

const observerLog = [];
class TrackingObserver {
  constructor(callback) {
    this.callback = callback;
    this.observed = [];
    this.disconnected = false;
    observerLog.push(this);
  }
  observe(target, options) { this.observed.push({ target, options }); }
  disconnect() { this.disconnected = true; }
}

let canceledFrames = 0;
window.MutationObserver = TrackingObserver;
window.requestAnimationFrame = (callback) => setTimeout(callback, 0);
window.cancelAnimationFrame = (id) => { canceledFrames += 1; clearTimeout(id); };
window.getComputedStyle = () => ({ getPropertyValue: () => "rgb(13, 110, 253)" });

const documentElement = { dataset: { bsTheme: "light" } };
const ownerDocument = { documentElement, defaultView: window };

function makeCanvas() {
  const contextHandler = {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (prop === Symbol.toPrimitive) return () => "";
      return () => (prop === "measureText" ? { width: 0 } : undefined);
    },
  };
  const context = new Proxy({}, contextHandler);
  const canvas = {
    nodeType: 1,
    tagName: "CANVAS",
    style: {},
    width: 400,
    height: 200,
    getContext: () => context,
    addEventListener() {},
    removeEventListener() {},
    getBoundingClientRect: () => ({
      x: 0, y: 0, top: 0, left: 0, right: 400, bottom: 200,
      width: 400, height: 200,
    }),
    setAttribute() {},
    getAttribute: () => null,
    ownerDocument,
  };
  context.canvas = canvas;
  return canvas;
}

function makeRoot(attrs = {}, { withCanvas = true } = {}) {
  const attrMap = new Map(Object.entries(attrs));
  const canvas = makeCanvas();
  const root = {
    nodeType: 1,
    tagName: "DIV",
    style: {},
    ownerDocument,
    getAttribute: (name) => (attrMap.has(name) ? attrMap.get(name) : null),
    setAttribute: (name, value) => attrMap.set(name, String(value)),
    matches: (selector) => selector === ".chart",
    querySelector: (selector) =>
      ((selector === ":scope > canvas" || selector === "canvas") && withCanvas
        ? canvas
        : null),
    querySelectorAll: (selector) => (selector === ".chart" ? [root] : []),
  };
  return root;
}

function report(name, details = {}) {
  console.log(JSON.stringify({ name, ok: true, ...details }));
}
"""

VALID_DATA = json.dumps(
    {"labels": ["Jan", "Feb"], "datasets": [{"label": "Revenue", "data": [1, 2]}]}
)
NODE_TEST_TIMEOUT = 30

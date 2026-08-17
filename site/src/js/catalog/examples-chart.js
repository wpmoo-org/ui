// Chart catalog adapter. All rendering, theming, and lifecycle work is
// delegated to the public MooChart component (src/js/components/chart.js),
// which bundles Chart.js at build time through `chart.js/auto`. This module
// never touches Chart.js, a CDN, or `window.Chart` itself — it only discovers
// `.moo-chart` roots in the catalog and wires their disposal into
// initCatalog's dispose chain.

import MooChart from "../../../../src/js/components/chart.js";

const states = new WeakMap();

export function initExamplesChart(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const instances = [];
  root.querySelectorAll(".moo-chart").forEach((element) => {
    instances.push(MooChart.getOrCreateInstance(element));
  });

  const release = () => {
    instances.forEach((instance) => instance.dispose());
    states.delete(root);
  };

  states.set(root, release);
  return release;
}

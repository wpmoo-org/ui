// Chart catalog adapter. All rendering, theming, and lifecycle work is
// delegated to the public MooChart component (src/js/components/chart.js),
// which bundles Chart.js at build time through `chart.js/auto`. This module
// never touches Chart.js, a CDN, or `window.Chart` itself — it only discovers
// `.chart` roots in the catalog and wires their disposal into
// initCatalog's dispose chain.

import MooChart from "../../../../src/js/components/chart.js";

const states = new WeakMap();

function readThemeValue(element) {
  return element?.dataset?.bsTheme || element?.getAttribute?.("data-bs-theme");
}

function normalizeTheme(value) {
  return value === "dark" ? "dark" : "light";
}

function writeThemeValue(element, theme) {
  if (element?.dataset) {
    element.dataset.bsTheme = theme;
  } else {
    element?.setAttribute?.("data-bs-theme", theme);
  }
}

function ensureScopedTheme(container, ownerDocument) {
  const theme = normalizeTheme(
    readThemeValue(container) || readThemeValue(ownerDocument?.documentElement),
  );
  writeThemeValue(container, theme);
  return theme;
}

function resolveLiveThemeScope(container) {
  return container.closest?.(".moo-example__preview") || container;
}

function setElementHidden(element, hidden) {
  if (!element) return;
  if (element.toggleAttribute) {
    element.toggleAttribute("hidden", hidden);
  } else {
    element.hidden = hidden;
  }
}

const LIFECYCLE_STATES = {
  live: {
    ariaLabel: "Dispose chart",
    label: "Dispose",
  },
  disposed: {
    ariaLabel: "Reinitialize chart",
    label: "Reinitialize",
  },
};

function setLifecycleButtonState(button, isDisposed) {
  if (!button) return;
  const state = isDisposed ? "disposed" : "live";
  const config = LIFECYCLE_STATES[state];
  const label = button.querySelector?.("[data-chart-lifecycle-label]");
  const disposeIcon = button.querySelector?.('[data-chart-lifecycle-icon="dispose"]');
  const reinitIcon = button.querySelector?.('[data-chart-lifecycle-icon="reinit"]');

  if (button.dataset) {
    button.dataset.chartLifecycleState = state;
  } else {
    button.setAttribute?.("data-chart-lifecycle-state", state);
  }
  button.setAttribute?.("aria-label", config.ariaLabel);

  if (label) {
    label.textContent = config.label;
  } else if ("textContent" in button) {
    button.textContent = config.label;
  }
  setElementHidden(disposeIcon, isDisposed);
  setElementHidden(reinitIcon, !isDisposed);
}

export function initExamplesChart(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const instances = [];
  const cleanups = [];
  const liveThemeScopes = new WeakMap();
  try {
    const liveContainers = Array.from(root.querySelectorAll("[data-chart-live]"));
    liveContainers.forEach((container) => {
      const ownerDocument = container.ownerDocument || document;
      const themeScope = resolveLiveThemeScope(container);
      ensureScopedTheme(themeScope, ownerDocument);
      liveThemeScopes.set(container, themeScope);
    });

    root.querySelectorAll(".chart").forEach((element) => {
      instances.push(MooChart.getOrCreateInstance(element));
    });
    liveContainers.forEach((container) => {
      const chartRoot = container.querySelector(".chart");
      if (!chartRoot) return;

      const themeScope = liveThemeScopes.get(container) || container;
      const status = container.querySelector("[data-chart-status]");
      const setStatus = (message) => {
        if (status) status.textContent = message;
      };
      const rememberInstance = (instance) => {
        if (!instances.includes(instance)) instances.push(instance);
        return instance;
      };
      const themeButton = container.querySelector("[data-chart-theme]");
      const lifecycleButton = container.querySelector("[data-chart-lifecycle]");
      setLifecycleButtonState(lifecycleButton, false);

      const onTheme = () => {
        const nextTheme = readThemeValue(themeScope) === "dark" ? "light" : "dark";
        writeThemeValue(themeScope, nextTheme);
        setStatus(`Example theme: ${nextTheme}`);
      };
      const onLifecycle = () => {
        const instance = MooChart.getInstance(chartRoot);
        if (instance) {
          instance.dispose();
          setLifecycleButtonState(lifecycleButton, true);
          setStatus("Disposed");
          return;
        }

        rememberInstance(MooChart.getOrCreateInstance(chartRoot));
        setLifecycleButtonState(lifecycleButton, false);
        setStatus("Live");
      };

      themeButton?.addEventListener("click", onTheme);
      lifecycleButton?.addEventListener("click", onLifecycle);
      cleanups.push(() => {
        themeButton?.removeEventListener("click", onTheme);
        lifecycleButton?.removeEventListener("click", onLifecycle);
      });
    });
  } catch (error) {
    instances.forEach((instance) => instance.dispose());
    cleanups.forEach((cleanup) => cleanup());
    throw error;
  }

  let released = false;
  const release = () => {
    if (released) return;
    released = true;
    cleanups.forEach((cleanup) => cleanup());
    instances.forEach((instance) => instance.dispose());
    if (states.get(root) === release) {
      states.delete(root);
    }
  };

  states.set(root, release);
  return release;
}

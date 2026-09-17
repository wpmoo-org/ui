// Chart catalog adapter. All rendering, theming, and lifecycle work is
// delegated to the public MooChart component (src/js/components/chart.js),
// which bundles Chart.js at build time through `chart.js/auto`. This module
// never touches Chart.js, a CDN, or `window.Chart` itself — it only discovers
// `.chart` roots in the catalog and wires their disposal into
// initCatalog's dispose chain.

import MooChart from "../../../../src/js/components/chart.js";
import {
  findThemeOwner,
  resolveOwnerTheme,
  setOwnerTheme,
} from "../../../../src/js/theme-owner.js";
import { THEME_BUILDER_TOKEN_CHANGE_EVENT } from "./theme-builder-schema.js";

const states = new WeakMap();
const CHART_COLOR_TOKENS = [
  "--moo-chart-1",
  "--moo-chart-2",
  "--moo-chart-3",
  "--moo-chart-4",
  "--moo-chart-5",
];

function resolveLiveThemeScope(container) {
  return container.closest?.(".moo-example__preview") || container;
}

function createLiveThemeOwner(container, inheritedOwner = findThemeOwner(container)) {
  const scope = resolveLiveThemeScope(container);
  const view = container.ownerDocument?.defaultView;
  const inheritedTheme = resolveOwnerTheme(inheritedOwner, null, view);
  scope.classList?.add("moo-ui");
  setOwnerTheme(scope, inheritedTheme);
  return scope;
}

// The lifecycle preview deliberately owns only its light/dark switch. Its
// palette remains an explicit catalog-demo bridge from the page's Theme
// Builder, rather than changing the general nested-owner isolation contract.
function syncLiveChartPalette(themeScope, sourceOwner, view) {
  const sourceStyle = view?.getComputedStyle?.(sourceOwner);
  const targetStyle = themeScope?.style;
  if (!sourceStyle || !targetStyle?.setProperty) return;

  CHART_COLOR_TOKENS.forEach((token) => {
    const value = sourceStyle.getPropertyValue(token).trim();
    if (value && targetStyle.getPropertyValue?.(token)?.trim() !== value) {
      targetStyle.setProperty(token, value);
    }
  });
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
  const livePaletteSources = new Map();
  try {
    const liveContainers = Array.from(root.querySelectorAll("[data-chart-live]"));
    liveContainers.forEach((container) => {
      if (container.querySelector("[data-chart-theme]")) {
        const sourceOwner = findThemeOwner(container);
        const themeScope = createLiveThemeOwner(container, sourceOwner);
        liveThemeScopes.set(container, themeScope);
        if (sourceOwner) {
          syncLiveChartPalette(themeScope, sourceOwner, container.ownerDocument?.defaultView);
          livePaletteSources.set(themeScope, sourceOwner);
        }
      }
    });

    livePaletteSources.forEach((sourceOwner, themeScope) => {
      const view = themeScope.ownerDocument?.defaultView;
      const sync = () => syncLiveChartPalette(themeScope, sourceOwner, view);
      sourceOwner.addEventListener?.(THEME_BUILDER_TOKEN_CHANGE_EVENT, sync);
      cleanups.push(() =>
        sourceOwner.removeEventListener?.(THEME_BUILDER_TOKEN_CHANGE_EVENT, sync)
      );
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
        const nextTheme = themeScope.dataset?.bsTheme === "dark" ? "light" : "dark";
        setOwnerTheme(themeScope, nextTheme);
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

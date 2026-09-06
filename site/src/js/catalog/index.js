import Sidebar from "../../../../src/js/components/sidebar.js";
import { initAcceptancePortal } from "./acceptance.js";
import { initBlockFrames } from "./block-frame.js";
import { initBootstrapPreview } from "./bootstrap-preview.js";
import { initCardSpacing } from "./card-spacing.js";
import { initCatalogFilter } from "./catalog-filter.js";
import { initCatalogViewToggle } from "./catalog-view-toggle.js";
import { initCodePreview } from "./code-preview.js";
import { initCommand } from "./command.js";
import { initExamplesForms } from "./examples-forms.js";
import { initHomeMotion } from "./home-motion.js";
import { initSettingsPanel } from "./settings-panel.js";
import { initTheme } from "./theme.js";
import { initToc } from "./toc.js";

const states = new WeakMap();
const FEATURE_SELECTORS = {
  chartExamples: ".chart, [data-chart-live]",
  combobox: ".combobox",
  contextMenu: ".context-menu",
  datatable: ".datatable",
  datepicker: "[data-datepicker], [data-datepicker-range], [data-calendar]",
  slider: "[data-slider]",
  tasksExample: "[data-moo-example-tasks]",
  usersExample: "[data-moo-example-users]",
};

function hasFeature(root, selector) {
  return Boolean(root.querySelector?.(selector));
}

function reportLazyError(error) {
  setTimeout(() => {
    throw error;
  }, 0);
}

function initLazyFeature(root, selector, loadModule, initialize) {
  if (!hasFeature(root, selector)) {
    return null;
  }

  let released = false;
  let dispose = null;
  loadModule()
    .then((module) => {
      if (released) {
        return;
      }
      dispose = initialize(module);
      if (released) {
        dispose?.();
        dispose = null;
      }
    })
    .catch(reportLazyError);

  return () => {
    released = true;
    dispose?.();
    dispose = null;
  };
}

function pushLazyFeature(disposers, root, selector, loadModule, initialize) {
  const dispose = initLazyFeature(root, selector, loadModule, initialize);
  if (dispose) {
    disposers.push(dispose);
  }
}

export function initCatalog(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const disposers = [
    initTheme(root),
    initCatalogFilter(root),
    initCommand(root),
    initExamplesForms(root),
    initCatalogViewToggle(root),
    initSettingsPanel(root),
    initToc(root),
    initAcceptancePortal(root),
  ];

  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.tasksExample,
    () => import("./examples-tasks.js"),
    ({ initExamplesTasks }) => initExamplesTasks(root),
  );
  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.usersExample,
    () => import("./examples-users.js"),
    ({ initExamplesUsers }) => initExamplesUsers(root),
  );
  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.chartExamples,
    () => import("./examples-chart.js"),
    ({ initExamplesChart }) => initExamplesChart(root),
  );
  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.combobox,
    () => import("../../../../src/js/components/combobox.js"),
    ({ default: Combobox }) => {
      const instances = [];
      root.querySelectorAll(".combobox").forEach((element) => {
        instances.push(Combobox.getOrCreateInstance(element));
      });
      return () => instances.forEach((instance) => instance.dispose());
    },
  );
  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.datepicker,
    () => import("../../../../src/js/components/datepicker.js"),
    ({ default: Datepicker, MooCalendar, MooDateRangePicker }) => {
      const instances = [];
      root.querySelectorAll("[data-datepicker]").forEach((element) => {
        instances.push(Datepicker.getOrCreateInstance(element));
      });
      root.querySelectorAll("[data-datepicker-range]").forEach((element) => {
        instances.push(MooDateRangePicker.getOrCreateInstance(element));
      });
      root.querySelectorAll("[data-calendar]").forEach((element) => {
        if (element.closest("[data-datepicker], [data-datepicker-range]")) {
          return;
        }
        instances.push(MooCalendar.getOrCreateInstance(element));
      });
      return () => instances.forEach((instance) => instance.dispose());
    },
  );
  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.slider,
    () => import("../../../../src/js/components/slider.js"),
    ({ default: Slider }) => {
      const instances = [];
      root.querySelectorAll("[data-slider]").forEach((element) => {
        instances.push(Slider.getOrCreateInstance(element));
      });
      return () => instances.forEach((instance) => instance.dispose());
    },
  );

  disposers.push(initCodePreview(root));
  disposers.push(initBootstrapPreview(root));

  root.querySelectorAll('[data-slot="sidebar-wrapper"]').forEach((element) => {
    const instance = Sidebar.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.contextMenu,
    () => import("../../../../src/js/components/context-menu.js"),
    ({ default: ContextMenu }) => {
      const instances = [];
      root.querySelectorAll(".context-menu").forEach((element) => {
        instances.push(ContextMenu.getOrCreateInstance(element));
      });
      return () => instances.forEach((instance) => instance.dispose());
    },
  );
  pushLazyFeature(
    disposers,
    root,
    FEATURE_SELECTORS.datatable,
    () => import("../../../../src/js/components/datatable.js"),
    ({ default: DataTable }) => {
      const instances = [];
      root.querySelectorAll(".datatable").forEach((element) => {
        instances.push(DataTable.getOrCreateInstance(element));
      });
      return () => instances.forEach((instance) => instance.dispose());
    },
  );

  disposers.push(initHomeMotion(root));
  disposers.push(initBlockFrames(root));
  disposers.push(initCardSpacing(root));

  const dispose = () => {
    [...disposers].reverse().forEach((release) => release?.());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initCatalog(document), {
    once: true,
  });
} else {
  initCatalog(document);
}

import Combobox from "../../../../src/js/components/combobox.js";
import ContextMenu from "../../../../src/js/components/context-menu.js";
import DataTable from "../../../../src/js/components/datatable.js";
import Datepicker, { MooCalendar, MooDateRangePicker } from "../../../../src/js/components/datepicker.js";
import Slider from "../../../../src/js/components/slider.js";
import Sidebar from "../../../../src/js/components/sidebar.js";
import { initAcceptancePortal } from "./acceptance.js";
import { initBlockFrames } from "./block-frame.js";
import { initBootstrapPreview } from "./bootstrap-preview.js";
import { initCardSpacing } from "./card-spacing.js";
import { initCatalogFilter } from "./catalog-filter.js";
import { initCatalogViewToggle } from "./catalog-view-toggle.js";
import { initCodePreview } from "./code-preview.js";
import { initCommand } from "./command.js";
import { initExamplesChart } from "./examples-chart.js";
import { initExamplesForms } from "./examples-forms.js";
import { initExamplesTasks } from "./examples-tasks.js";
import { initExamplesUsers } from "./examples-users.js";
import { initHomeMotion } from "./home-motion.js";
import { initSettingsPanel } from "./settings-panel.js";
import { initTheme } from "./theme.js";
import { initToc } from "./toc.js";

const states = new WeakMap();

export function initCatalog(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const disposers = [
    initTheme(root),
    initCatalogFilter(root),
    initCommand(root),
    initExamplesForms(root),
    initExamplesTasks(root),
    initExamplesUsers(root),
    initExamplesChart(root),
    initCatalogViewToggle(root),
    initSettingsPanel(root),
    initToc(root),
    initAcceptancePortal(root),
  ];

  root.querySelectorAll(".combobox").forEach((element) => {
    const instance = Combobox.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  root.querySelectorAll("[data-datepicker]").forEach((element) => {
    const instance = Datepicker.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  root.querySelectorAll("[data-datepicker-range]").forEach((element) => {
    const instance = MooDateRangePicker.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  root.querySelectorAll("[data-calendar]").forEach((element) => {
    if (element.closest("[data-datepicker], [data-datepicker-range]")) {
      return;
    }
    const instance = MooCalendar.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  root.querySelectorAll("[data-slider]").forEach((element) => {
    const instance = Slider.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  disposers.push(initCodePreview(root));
  disposers.push(initBootstrapPreview(root));

  root.querySelectorAll('[data-slot="sidebar-wrapper"]').forEach((element) => {
    const instance = Sidebar.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  root.querySelectorAll(".context-menu").forEach((element) => {
    const instance = ContextMenu.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

  root.querySelectorAll(".datatable").forEach((element) => {
    const instance = DataTable.getOrCreateInstance(element);
    disposers.push(() => instance.dispose());
  });

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

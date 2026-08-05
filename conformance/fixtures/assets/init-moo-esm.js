/**
 * Generic Host Conformance Kit — moo-esm fixture initialization.
 *
 * Combobox and Sidebar are explicit-init components: nothing happens until
 * the host calls getOrCreateInstance on the documented roots. This file is
 * deliberately standalone so the runner can block it via route interception
 * for the lifecycle two-pass check (inert-before-init). The classes are
 * exposed on window.__mooConformance so the runner can exercise idempotent
 * initialization and invalid-root rejection against the same modules.
 */
import Combobox from "./combobox.js";
import Sidebar from "./sidebar.js";

const comboboxRoot = document.querySelector(".moo-ui .combobox");
const sidebarRoot = document.querySelector('.moo-ui [data-slot="sidebar-wrapper"]');

window.__mooConformance = { Combobox, Sidebar };
window.__mooConformanceInstances = {
  combobox: Combobox.getOrCreateInstance(comboboxRoot),
  sidebar: Sidebar.getOrCreateInstance(sidebarRoot),
};

document.body.dataset.mooEsmReady = "true";

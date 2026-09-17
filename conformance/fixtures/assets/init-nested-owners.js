import Sidebar from "../../../dist/js/sidebar.js";
import MooDatepicker from "../../../dist/js/datepicker.js";
import DataTable from "../../../dist/js/datatable.js";
import MooChart from "../../../dist/js/chart.js";

const OWNER_SELECTOR =
  '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';

const findThemeOwner = (node) => node?.closest?.(OWNER_SELECTOR) || null;
const ownerPortalRoot = (owner) => (
  Array.from(owner?.children || []).find((child) =>
    child.matches("[data-moo-overlay-portal-host]"),
  ) || owner
);

const portalRecords = {};
const recordPortal = (name, element, trigger) => {
  const owner = findThemeOwner(trigger || element);
  portalRecords[name] = {
    ownerId: owner?.id || null,
    parentId: element?.parentElement?.id || null,
    inBody: element?.parentElement === document.body,
  };
};

const restoreAfterHidden = new WeakMap();
const portalOverlay = (overlay, trigger, name) => {
  const owner = findThemeOwner(trigger || overlay);
  const portal = ownerPortalRoot(owner);
  if (!overlay || !portal || overlay.parentElement === portal) {
    recordPortal(name, overlay, trigger);
    return;
  }
  restoreAfterHidden.set(overlay, {
    parent: overlay.parentNode,
    nextSibling: overlay.nextSibling,
  });
  portal.append(overlay);
  recordPortal(name, overlay, trigger);
};

const restoreOverlay = (overlay) => {
  const original = restoreAfterHidden.get(overlay);
  if (!original?.parent?.isConnected) return;
  if (original.nextSibling?.parentNode === original.parent) {
    original.parent.insertBefore(overlay, original.nextSibling);
  } else {
    original.parent.append(overlay);
  }
  restoreAfterHidden.delete(overlay);
};

const outer = document.querySelector("#nested-owner-outer");
const inner = document.querySelector("#nested-owner-inner");
const owners = { outer, inner };

document.querySelectorAll("[data-nested-theme-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const owner = owners[button.dataset.nestedThemeToggle];
    if (!owner) return;
    owner.dataset.bsTheme = owner.dataset.bsTheme === "dark" ? "light" : "dark";
    localStorage.setItem(owner.dataset.mooThemeKey, owner.dataset.bsTheme);
  });
});

document.querySelectorAll("[data-nested-direction-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const owner = owners[button.dataset.nestedDirectionToggle];
    if (!owner) return;
    owner.dir = owner.dir === "rtl" ? "ltr" : "rtl";
    localStorage.setItem(owner.dataset.mooDirectionKey, owner.dir);
  });
});

document.addEventListener("click", (event) => {
  const trigger = event.target.closest?.('[data-bs-toggle="offcanvas"]');
  const target = trigger?.getAttribute("data-bs-target");
  if (target?.startsWith("#")) {
    portalOverlay(document.querySelector(target), trigger, "offcanvas");
  }
}, true);

document.addEventListener("show.bs.modal", (event) => {
  portalOverlay(event.target, event.relatedTarget, "modal");
});
document.addEventListener("hidden.bs.modal", (event) => restoreOverlay(event.target));
document.addEventListener("show.bs.offcanvas", (event) => {
  recordPortal("offcanvas", event.target, event.relatedTarget || event.target);
});
document.addEventListener("hidden.bs.offcanvas", (event) => restoreOverlay(event.target));

const { Tooltip, Popover, Toast } = window.bootstrap;
document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((trigger) => {
  const portal = ownerPortalRoot(findThemeOwner(trigger));
  Tooltip.getOrCreateInstance(trigger, { container: portal });
});
document.querySelectorAll('[data-bs-toggle="popover"]').forEach((trigger) => {
  const portal = ownerPortalRoot(findThemeOwner(trigger));
  Popover.getOrCreateInstance(trigger, { container: portal });
});

document.querySelector("[data-nested-toast-trigger]").addEventListener("click", (event) => {
  const trigger = event.currentTarget;
  const portal = ownerPortalRoot(findThemeOwner(trigger));
  const toast = document.createElement("div");
  toast.className = "toast align-items-center";
  toast.dataset.nestedToast = "true";
  toast.textContent = "Nested owner toast";
  portal.append(toast);
  Toast.getOrCreateInstance(toast, { animation: false }).show();
  recordPortal("toast", toast, trigger);
});

const sidebar = Sidebar.getOrCreateInstance(document.querySelector("#nested-owner-sidebar"));
const datepicker = MooDatepicker.getOrCreateInstance(
  document.querySelector("#nested-owner-datepicker"),
);
const datatable = DataTable.getOrCreateInstance(
  document.querySelector("#nested-owner-datatable"),
);
const chart = MooChart.getOrCreateInstance(document.querySelector("#nested-owner-chart"));

document.querySelector("#nested-owner-datepicker").addEventListener(
  "shown.moo.datepicker",
  (event) => recordPortal("datepicker", event.target.querySelector("[data-datepicker-popover]"), event.target),
);
document.querySelector("#nested-owner-datatable").addEventListener(
  "show.bs.dropdown",
  (event) => {
    const menu = event.target.closest(".dropdown")?.querySelector(".dropdown-menu") ||
      document.querySelector("#nested-owner-inner-portal > .dropdown-menu");
    recordPortal("datatable", menu, event.target);
  },
);

window.__nestedOwners = {
  chart,
  chartColors: {
    outer: getComputedStyle(outer).getPropertyValue("--bs-primary").trim(),
    inner: getComputedStyle(inner).getPropertyValue("--bs-primary").trim(),
  },
  datatable,
  datepicker,
  owners,
  portalRecords,
  sidebar,
};
document.body.dataset.nestedOwnersReady = "true";

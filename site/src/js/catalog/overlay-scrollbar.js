import OverlayScrollbar from "../../../../src/js/components/overlay-scrollbar.js";
import { resolveCatalogScrollHost } from "./scroll-host.js";

export function initCatalogScrollbar(root) {
  const catalog = root.querySelector('[data-moo-shell="catalog"]');
  if (!catalog) return;
  const owner = catalog.closest('.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]');
  const view = owner.ownerDocument.defaultView;
  let element;
  let instance;
  let originallyHidden;
  const release = () => {
    instance?.dispose();
    instance = null;
    element?.classList.toggle("no-scrollbar", originallyHidden);
  };
  const synchronize = () => {
    const next = resolveCatalogScrollHost(root).element;
    if (next !== element) {
      release();
      element = next;
      originallyHidden = element.classList.contains("no-scrollbar");
      element.classList.remove("no-scrollbar");
      try {
        instance = OverlayScrollbar.getOrCreateInstance(owner, { scrollElement: element, label: "Catalog scroll position" });
      } catch (error) {
        element.classList.toggle("no-scrollbar", originallyHidden);
        element = null;
        throw error;
      }
    } else {
      instance?.refresh();
    }
  };
  synchronize();
  view.addEventListener("resize", synchronize);
  return () => {
    view.removeEventListener("resize", synchronize);
    release();
  };
}

export function initOverlayScrollbarDemo(root) {
  const demo = root.querySelector("[data-overlay-scrollbar-demo]");
  if (!demo) return;
  const owner = demo.closest(".moo-ui");
  let instance = OverlayScrollbar.getOrCreateInstance(owner);
  const controls = [...demo.querySelectorAll("[data-overlay-scrollbar-controls] button")];
  const actions = [
    () => { owner.dataset.bsTheme = owner.dataset.bsTheme === "dark" ? "light" : "dark"; },
    () => {
      const html = owner.ownerDocument.documentElement;
      html.dir = html.dir === "rtl" ? "ltr" : "rtl";
      instance?.refresh();
    },
    () => {
      if (instance) {
        instance.dispose();
        instance = null;
      } else {
        instance = OverlayScrollbar.getOrCreateInstance(owner);
      }
      controls[2].textContent = instance ? "Use native scrollbar" : "Enable overlay scrollbar";
    },
  ];
  controls.forEach((control, index) => control.addEventListener("click", actions[index]));
  return () => {
    instance?.dispose();
    controls.forEach((control, index) => control.removeEventListener("click", actions[index]));
  };
}

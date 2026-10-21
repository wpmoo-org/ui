import TableOfContents from "../../../../src/js/components/toc.js";
import { resolveCatalogScrollHost } from "./scroll-host.js";

// Catalog reference recipe: native Bootstrap fade + public TOC/Separator.
// Hosts keep their own Header placement and native scroll-root integration.
export function initReadingBar(root) {
  const panel = root.querySelector("[data-catalog-reading-bar]");
  if (!panel) return;
  const document = panel.ownerDocument;
  const view = document.defaultView;
  const bootstrap = view.bootstrap;
  const compact = panel.closest('[data-page-hide-from="lg"]');
  const maskProperties = ["mask-position", "mask-size", "mask-repeat"];
  const listeners = [];
  let frame = 0;
  let stopped = false;
  let revealed = false;
  let compactMode;
  let previousHeight = 0;
  let visibilityRevision = 0;
  const appliedOffsets = new WeakMap();
  let scroller;
  let original;
  const originalInert = panel.inert;
  const originalHidden = panel.hidden;
  const originalShown = panel.classList.contains("show");
  const restore = () => {
    if (!scroller || !original) return;
    scroller.classList.toggle("scroll-fade-y", original.fade);
    for (const { name, value, priority } of original.mask) {
      if (value) scroller.style.setProperty(name, value, priority);
      else scroller.style.removeProperty(name);
    }
  };
  const listen = (target, type, handler, options) => {
    target.addEventListener(type, handler, options);
    listeners.push(() => target.removeEventListener(type, handler, options));
  };
  const update = () => {
    if (stopped) return;
    const nextScroller = resolveCatalogScrollHost(root).element;
    if (nextScroller !== scroller) {
      restore();
      scroller = nextScroller;
      original = {
        fade: scroller.classList.contains("scroll-fade-y"),
        mask: maskProperties.map(name => ({ name, value: scroller.style.getPropertyValue(name), priority: scroller.style.getPropertyPriority(name) })),
      };
    }
    const mobile = view.getComputedStyle(compact).display !== "none";
    const threshold = revealed ? 300 : Math.max(360, view.innerHeight / 2);
    const next = mobile && scroller.scrollTop > threshold;
    if (revealed && !next) {
      const trigger = panel.querySelector('[data-bs-toggle="dropdown"]');
      bootstrap?.Dropdown?.getInstance(trigger)?.hide();
      if (panel.contains(document.activeElement)) {
        panel.closest("header").querySelector(".moo-catalog__sidebar-toggle")?.focus({ preventScroll: true });
      }
    }
    revealed = next;
    panel.inert = !revealed;
    if (panel.dataset.catalogReadingBarVisible !== String(revealed)) panel.dataset.catalogReadingBarVisible = String(revealed);
    if (revealed && (panel.hidden || !panel.classList.contains("show"))) {
      visibilityRevision++;
      panel.hidden = false;
      // Establish the transparent rendered state before starting Bootstrap's
      // opacity transition; never animate height or move the reading column.
      void panel.offsetWidth;
      panel.classList.add("show");
    } else if (!revealed && !panel.hidden && panel.classList.contains("show")) {
      panel.classList.remove("show");
      const revision = ++visibilityRevision;
      // Native CSS transitions own timing (including reduced motion). A stale
      // completion cannot hide a bar that reopened during a fast scroll.
      Promise.allSettled(panel.getAnimations().map(animation => animation.finished)).then(() => {
        if (stopped || revealed || revision !== visibilityRevision) return;
        panel.hidden = true;
        schedule();
      });
    }
    const height = mobile ? panel.getBoundingClientRect().height : 0;
    if (compactMode !== undefined && mobile !== compactMode) {
      // When the responsive rail changes, retain an explicitly aligned
      // fragment below the new navigation boundary. Ordinary reveal/hide
      // never moves content or changes the reader's scroll position.
      let target;
      try { target = document.getElementById(decodeURIComponent(view.location.hash.slice(1))); } catch {}
      if (target && Math.abs(target.getBoundingClientRect().top - scroller.getBoundingClientRect().top - previousHeight) < 1) {
        scroller.scrollTop += previousHeight - height;
      }
    }
    compactMode = mobile;
    previousHeight = height;
    scroller.classList.toggle("scroll-fade-y", original.fade && (!mobile || scroller.scrollTop > 0));
    if (height > 0) {
      scroller.style.setProperty("mask-position", `0 ${height}px`);
      scroller.style.setProperty("mask-size", `100% calc(100% - ${height}px)`);
      scroller.style.setProperty("mask-repeat", "no-repeat");
    } else {
      for (const { name, value, priority } of original.mask) {
        if (value) scroller.style.setProperty(name, value, priority);
        else scroller.style.removeProperty(name);
      }
    }
    for (const nav of root.querySelectorAll("#catalog-toc-compact, #catalog-toc-list")) {
      const instance = TableOfContents.getInstance(nav);
      if (instance && (appliedOffsets.get(instance) === undefined || Math.abs(height - appliedOffsets.get(instance)) > 0.1)) {
        appliedOffsets.set(instance, height);
        instance.refresh({ activationOffset: height });
      }
    }
  };
  const schedule = () => {
    if (stopped || frame) return;
    frame = view.requestAnimationFrame(() => {
      frame = 0;
      update();
    });
  };
  listen(document, "scroll", schedule, { passive: true, capture: true });
  listen(root, "moo:catalog-toc-ready", update);
  listen(view, "resize", schedule);
  const resize = new view.ResizeObserver(schedule);
  for (const element of [panel, panel.closest("header"), panel.closest('[data-slot="page"]')]) {
    if (element) resize.observe(element);
  }
  update();
  return () => {
    stopped = true;
    view.cancelAnimationFrame(frame);
    resize.disconnect();
    listeners.forEach(remove => remove());
    visibilityRevision++;
    panel.getAnimations().forEach(animation => animation.cancel());
    panel.classList.toggle("show", originalShown);
    panel.hidden = originalHidden;
    panel.inert = originalInert;
    delete panel.dataset.catalogReadingBarVisible;
    restore();
    for (const nav of root.querySelectorAll("#catalog-toc-compact, #catalog-toc-list")) {
      TableOfContents.getInstance(nav)?.refresh({ activationOffset: 0 });
    }
  };
}

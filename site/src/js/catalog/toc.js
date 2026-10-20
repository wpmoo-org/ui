import { resolveCatalogScrollHost } from "./scroll-host.js";
import { initReadingBar } from "./reading-bar.js";

const states = new WeakMap();

export function initToc(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const releaseReadingBar = initReadingBar(root);
  const listeners = [];
  const timers = new Set();
  const focusableTargets = new Set();
  const listen = (target, type, handler, options) => {
    target?.addEventListener(type, handler, options);
    if (target) {
      listeners.push({ target, type, handler, options });
    }
  };
  const delay = (handler, wait) => {
    const id = view.setTimeout(() => {
      timers.delete(id);
      handler();
    }, wait);
    timers.add(id);
  };
  const clearTimers = () => {
    timers.forEach((id) => view.clearTimeout(id));
    timers.clear();
  };

  const targets = [
    ...root.querySelectorAll(".moo-doc-toc [data-toc] .nav-link"),
    ...root.querySelectorAll('#catalog-toc-compact a[href^="#"]'),
    ...root.querySelectorAll('#toc-demo-page [data-toc] a[href^="#"]'),
  ]
    .map((link) => {
      const hash = link.getAttribute("href");
      let id;
      try { id = decodeURIComponent(hash?.slice(1) || ""); } catch { return null; }
      const target = id ? root.getElementById(id) : null;
      return target ? { link, target } : null;
    })
    .filter(Boolean);
  const targetByHash = new Map(targets.map((item) => [item.link.getAttribute("href"), item]));
  const scrollHost = resolveCatalogScrollHost(root);
  const main = scrollHost.element;
  const documentNode = root.nodeType === 9 ? root : root.ownerDocument;
  const documentScroller =
    documentNode?.scrollingElement || documentNode?.documentElement;
  const ownsDocumentScroll = main === documentScroller;
  const resetWindowScroll = () => {
    if (view.scrollX !== 0 || view.scrollY !== 0) {
      view.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }
  };
  const alignTargetInMain = (target, behavior = "smooth") => {
    if (!ownsDocumentScroll) {
      resetWindowScroll();
    }
    const mainRect = main.getBoundingClientRect();
    const targetTop = target.getBoundingClientRect().top - mainRect.top + main.scrollTop;
    const reduceMotion = view.matchMedia("(prefers-reduced-motion: reduce)").matches;
    main.scrollTo({
      top: Math.max(0, targetTop -
        (root.querySelector('[data-catalog-reading-bar][data-catalog-reading-bar-visible="true"]')?.getBoundingClientRect().height || 0)),
      behavior: reduceMotion ? "auto" : behavior,
    });
    if (!ownsDocumentScroll) {
      resetWindowScroll();
      view.requestAnimationFrame(resetWindowScroll);
    }
  };
  const scrollTargetIntoMain = (target, behavior = "smooth") => {
    if (!main || !target) {
      return;
    }
    alignTargetInMain(target, behavior);
  };
  const navigateToHash = (hash, behavior = "smooth", updateHistory = false) => {
    const item = targetByHash.get(hash);
    if (!item) {
      return false;
    }
    if (updateHistory) {
      clearTimers();
    }
    if (updateHistory && view.location.hash !== hash) {
      view.history.pushState(null, "", hash);
    }
    scrollTargetIntoMain(item.target, behavior);
    return true;
  };
  const navigateCurrentHash = (behavior = "auto") => {
    if (!view.location.hash) {
      return false;
    }
    return navigateToHash(view.location.hash, behavior, false);
  };

  targets.forEach(({ link, target }) => {
    listen(link, "click", (event) => {
      const hash = link.getAttribute("href");
      if (!hash?.startsWith("#")) return;
      event.preventDefault();
      if (navigateToHash(hash, "smooth", true) && event.detail === 0) {
        if (!target.hasAttribute("tabindex") && target.tabIndex < 0) {
          target.setAttribute("tabindex", "-1");
          focusableTargets.add(target);
        }
        target.focus({ preventScroll: true });
      }
    });
  });

  if (targets.length > 0) {
    listen(view, "hashchange", () => {
      if (!navigateCurrentHash("auto")) {
        if (!ownsDocumentScroll) {
          resetWindowScroll();
        }
      }
    });
    if (navigateCurrentHash("auto")) {
      view.requestAnimationFrame(() => {
        navigateCurrentHash("auto");
        view.requestAnimationFrame(() => navigateCurrentHash("auto"));
      });
      delay(() => navigateCurrentHash("auto"), 250);
      delay(() => navigateCurrentHash("auto"), 700);
    }
  }

  const dispose = () => {
    releaseReadingBar?.();
    listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    timers.forEach((id) => view.clearTimeout(id));
    focusableTargets.forEach((target) => {
      if (target.getAttribute("tabindex") === "-1") {
        target.removeAttribute("tabindex");
      }
    });
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

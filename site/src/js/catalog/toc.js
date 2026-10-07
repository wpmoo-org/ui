import { resolveCatalogScrollHost } from "./scroll-host.js";

const states = new WeakMap();

export function initToc(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const listeners = [];
  const timers = new Set();
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

  const targets = Array.from(root.querySelectorAll(".moo-doc-toc [data-toc] .nav-link"))
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
  let chartFrame = 0;
  let chartClickUntil = 0;

  const chartNav = root.querySelector("[data-moo-chart-template-nav]");
  const chartNavScroller = chartNav?.querySelector(".moo-chart-template-nav__list") ?? chartNav;
  const chartTargets = Array.from(chartNav?.querySelectorAll(".nav-link") ?? [])
    .map((link) => {
      const id = link.getAttribute("href")?.slice(1);
      const target = id ? root.getElementById(id) : null;
      return target ? { link, target } : null;
    })
    .filter(Boolean);
  const chartTargetByHash = new Map(
    chartTargets.map((item) => [item.link.getAttribute("href"), item])
  );

  const activateChartLink = (activeLink) => {
    chartTargets.forEach(({ link }) => {
      const active = link === activeLink;
      link.classList.toggle("active", active);
      if (active) {
        link.setAttribute("aria-current", "true");
        const navRect = chartNavScroller?.getBoundingClientRect();
        const linkRect = link.getBoundingClientRect();
        if (chartNavScroller && navRect && linkRect.left < navRect.left) {
          chartNavScroller.scrollLeft -= navRect.left - linkRect.left;
        } else if (chartNavScroller && navRect && linkRect.right > navRect.right) {
          chartNavScroller.scrollLeft += linkRect.right - navRect.right;
        }
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };
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
      top: Math.max(0, targetTop - chartNavOffsetFor(target)),
      behavior: reduceMotion ? "auto" : behavior,
    });
    if (!ownsDocumentScroll) {
      resetWindowScroll();
      view.requestAnimationFrame(resetWindowScroll);
    }
  };
  const chartNavOffsetFor = (target) => {
    if (!chartNav || !target) {
      return 0;
    }
    const followsChartNav = Boolean(
      chartNav.compareDocumentPosition(target) & view.Node.DOCUMENT_POSITION_FOLLOWING
    );
    if (!followsChartNav) {
      return 0;
    }
    const rootFontSize = parseFloat(view.getComputedStyle(root.documentElement).fontSize);
    const navHeight = chartNav.getBoundingClientRect().height;
    const navTop = parseFloat(view.getComputedStyle(chartNav).top) || 0;
    return navTop + navHeight + rootFontSize * 2.25;
  };
  const scrollTargetIntoMain = (target, behavior = "smooth") => {
    if (!main || !target) {
      return;
    }
    alignTargetInMain(target, behavior);
  };
  const updateChartNav = () => {
    chartFrame = 0;
    if (chartTargets.length === 0 || Date.now() < chartClickUntil) {
      return;
    }
    const rootFontSize = parseFloat(view.getComputedStyle(root.documentElement).fontSize);
    const navBottom = chartNav?.getBoundingClientRect().bottom ?? rootFontSize * 3;
    const offset = navBottom + rootFontSize * 2.25;
    const atEnd = main ? main.scrollTop + main.clientHeight >= main.scrollHeight - 1 : false;
    let active = atEnd ? chartTargets[chartTargets.length - 1] : chartTargets[0];
    if (!atEnd) {
      chartTargets.forEach((item) => {
        if (item.target.getBoundingClientRect().top <= offset + 1) {
          active = item;
        }
      });
    }
    activateChartLink(active.link);
  };
  const requestChartNavUpdate = () => {
    if (chartFrame === 0) {
      chartFrame = view.requestAnimationFrame(updateChartNav);
    }
  };
  const navigateToHash = (hash, behavior = "smooth", updateHistory = false) => {
    const item = targetByHash.get(hash) ?? chartTargetByHash.get(hash);
    if (!item) {
      return false;
    }
    if (updateHistory) {
      clearTimers();
    }
    const chartItem = chartTargetByHash.get(hash);
    if (chartItem) {
      chartClickUntil = Date.now() + 900;
      activateChartLink(chartItem.link);
    } else {
      requestChartNavUpdate();
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

  targets.forEach(({ link }) => {
    listen(link, "click", (event) => {
      const hash = link.getAttribute("href");
      if (!hash?.startsWith("#")) return;
      event.preventDefault();
      navigateToHash(hash, "smooth", true);
    });
  });

  if (chartTargets.length > 0) {
    chartTargets.forEach(({ link }) => {
      listen(link, "click", (event) => {
        const hash = link.getAttribute("href");
        if (!hash?.startsWith("#")) {
          return;
        }
        event.preventDefault();
        navigateToHash(hash, "smooth", true);
      });
    });
    updateChartNav();
    listen(scrollHost.eventTarget, "scroll", requestChartNavUpdate, { passive: true });
    listen(view, "resize", requestChartNavUpdate);
  }

  if (targets.length > 0 || chartTargets.length > 0) {
    listen(view, "hashchange", () => {
      if (!navigateCurrentHash("auto")) {
        if (!ownsDocumentScroll) {
          resetWindowScroll();
        }
        requestChartNavUpdate();
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
    listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    if (chartFrame) {
      view.cancelAnimationFrame(chartFrame);
    }
    timers.forEach((id) => view.clearTimeout(id));
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

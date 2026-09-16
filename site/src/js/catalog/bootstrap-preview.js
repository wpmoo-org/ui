import { findThemeOwner, ownerPortalRoot } from "../../../../src/js/theme-owner.js";

const states = new WeakMap();

export function initBootstrapPreview(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const listeners = [];
  const modalPortals = new Map();
  const sheetPortals = new Map();
  const bootstrapInstances = new Set();
  const sharedToastStacks = new Map();
  const listen = (target, type, handler, options) => {
    target?.addEventListener(type, handler, options);
    if (target) {
      listeners.push({ target, type, handler, options });
    }
  };

  // Preview pages are designed to fit their frame width, so a horizontal
  // scroll offset is engine fallout — WebKit can keep a stale inner viewport
  // when the outer frame shrinks without a reload, and a later focus or
  // scroll-into-view parks the document at a bogus offset. Clamp it back
  // whenever the content actually fits; genuine overflow pages are untouched.
  const clampHorizontalScroll = () => {
    const doc = root.documentElement || root.ownerDocument?.documentElement;
    if (doc && doc.scrollLeft !== 0 && doc.scrollWidth <= doc.clientWidth + 1) {
      doc.scrollLeft = 0;
    }
  };
  listen(view, "scroll", clampHorizontalScroll, { passive: true });
  listen(view, "resize", clampHorizontalScroll, { passive: true });
  clampHorizontalScroll();

  const ownerPortalFor = (trigger) =>
    ownerPortalRoot(findThemeOwner(trigger));
  const portalFor = (trigger) => (
    ownerPortalFor(trigger) ||
    root.body ||
    root.documentElement ||
    null
  );
  const restorePortaledElement = (element, original) => {
    if (!original) {
      return;
    }
    if (original.owner?.isConnected === false) {
      element.remove();
      return;
    }
    if (original.parent?.isConnected) {
      if (original.nextSibling?.parentNode === original.parent) {
        original.parent.insertBefore(element, original.nextSibling);
      } else {
        original.parent.appendChild(element);
      }
      return;
    }
    element.remove();
  };

  const onModalShow = (event) => {
    const modal = event.target;
    const trigger = event.relatedTarget || modal;
    const portal = ownerPortalFor(trigger) || portalFor(modal);
    if (
      !(modal instanceof view.HTMLElement) ||
      !modal.classList.contains("modal") ||
      !modal.closest(".moo-catalog") ||
      !portal ||
      modal.parentElement === portal
    ) {
      return;
    }
    modalPortals.set(modal, {
      parent: modal.parentNode,
      nextSibling: modal.nextSibling,
      owner: findThemeOwner(modal),
    });
    portal.appendChild(modal);
  };
  const onModalHidden = (event) => {
    const modal = event.target;
    if (!(modal instanceof view.HTMLElement)) {
      return;
    }
    restorePortaledElement(modal, modalPortals.get(modal));
    modalPortals.delete(modal);
  };
  listen(root, "show.bs.modal", onModalShow, true);
  listen(root, "hidden.bs.modal", onModalHidden, true);

  const portalSheet = (sheet, trigger = sheet) => {
    const portal = portalFor(trigger) || portalFor(sheet);
    if (
      !(sheet instanceof view.HTMLElement) ||
      !sheet.classList.contains("sheet") ||
      !portal ||
      sheet.parentElement === portal
    ) {
      return;
    }
    sheet.dataset.mooCatalogSheet = "true";
    sheetPortals.set(sheet, {
      parent: sheet.parentNode,
      nextSibling: sheet.nextSibling,
      owner: findThemeOwner(trigger) || findThemeOwner(sheet),
    });
    portal.appendChild(sheet);
  };
  listen(root, "click", (event) => {
    const target = event.target instanceof view.Element
      ? event.target
      : event.target?.parentElement;
    const trigger = target?.closest?.('[data-bs-toggle="offcanvas"][data-bs-target]');
    const selector = trigger?.getAttribute("data-bs-target");
    if (selector?.startsWith("#")) {
      portalSheet(root.querySelector(selector), trigger);
    }
  }, true);
  listen(root, "show.bs.offcanvas", (event) => {
    const sheet = event.target;
    if (
      sheet instanceof view.HTMLElement &&
      sheet.dataset.mooCatalogSheet === "true"
    ) {
      portalSheet(sheet);
    }
  }, true);
  listen(root, "hidden.bs.offcanvas", (event) => {
    const sheet = event.target;
    if (sheet instanceof view.HTMLElement) {
      restorePortaledElement(sheet, sheetPortals.get(sheet));
      sheetPortals.delete(sheet);
    }
  }, true);
  root.querySelectorAll(".moo-catalog .offcanvas.sheet").forEach((sheet) => {
    portalSheet(sheet);
  });

  const Tooltip = view.bootstrap?.Tooltip;
  if (Tooltip) {
    // Bootstrap's default sanitizer allowlist has no <kbd>, but tooltip
    // shortcut hints legitimately render our Kbd component's native <kbd>
    // element. Extend only that allowlist tag; sanitization stays on for
    // everything else.
    const tooltipOptions = Tooltip.Default?.allowList
      ? { allowList: { ...Tooltip.Default.allowList, kbd: [] } }
      : {};
    root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((trigger) => {
      const portal = portalFor(trigger);
      bootstrapInstances.add(Tooltip.getOrCreateInstance(trigger, {
        ...tooltipOptions,
        container: portal,
      }));
    });
  }
  const Popover = view.bootstrap?.Popover;
  if (Popover) {
    root.querySelectorAll('[data-bs-toggle="popover"]').forEach((trigger) => {
      const portal = portalFor(trigger);
      bootstrapInstances.add(Popover.getOrCreateInstance(trigger, { container: portal }));
    });
  }
  const Toast = view.bootstrap?.Toast;
  if (Toast) {
    let toastSequence = 0;
    const toastStackVisibleLimit = 3;

    const isStackContainer = (element) => (
      element instanceof view.HTMLElement &&
      element.matches('.toast-container--stacked[data-toast-stack="deck"]')
    );
    const getStackContainer = (toast) => {
      const container = toast?.closest?.(
        '.toast-container--stacked[data-toast-stack="deck"]',
      );
      return isStackContainer(container) ? container : null;
    };
    const getSharedToastStack = (sourceContainer, trigger) => {
      if (!isStackContainer(sourceContainer)) {
        return sourceContainer;
      }

      const portal = ownerPortalFor(trigger) || portalFor(sourceContainer);
      if (!portal) {
        return sourceContainer;
      }
      const key = sourceContainer.dataset.toastStack || "deck";
      let stacks = sharedToastStacks.get(portal);
      if (!stacks) {
        stacks = new Map();
        sharedToastStacks.set(portal, stacks);
      }
      const existing = stacks.get(key);
      if (existing?.isConnected) {
        return existing;
      }

      const container = root.createElement("div");
      container.className = sourceContainer.className;
      container.dataset.toastStack = key;
      container.dataset.mooCatalogToastStack = "shared";
      portal.appendChild(container);
      stacks.set(key, container);
      return container;
    };
    const readNumber = (value, fallback) => {
      const number = Number.parseFloat(value);
      return Number.isFinite(number) ? number : fallback;
    };
    const readPixels = (value, computed) => {
      const number = readNumber(value, 0);
      const normalized = value.trim();
      if (normalized.endsWith("rem")) {
        const rootFontSize = readNumber(
          view.getComputedStyle(root.documentElement).fontSize,
          16,
        );
        return number * rootFontSize;
      }
      if (normalized.endsWith("em")) {
        return number * readNumber(computed.fontSize, 16);
      }
      return number;
    };
    const clearToastStackState = (toast) => {
      toast.removeAttribute("data-toast-stack-index");
      toast.removeAttribute("data-toast-stack-limited");
      toast.removeAttribute("data-toast-stack-entering");
      toast.removeAttribute("inert");
      toast.style.removeProperty("--moo-toast-stack-collapsed-y");
      toast.style.removeProperty("--moo-toast-stack-expanded-y");
      toast.style.removeProperty("--moo-toast-stack-scale");
      toast.style.removeProperty("--moo-toast-stack-z");
    };
    const updateToastStack = (container, pendingToast = null) => {
      if (!isStackContainer(container)) {
        return;
      }

      const toasts = Array.from(container.children).filter((child) => (
        child instanceof view.HTMLElement &&
        child.classList.contains("toast") &&
        (child.classList.contains("show") ||
          child.classList.contains("showing") ||
          child === pendingToast)
      ));
      if (toasts.length === 0) {
        container.removeAttribute("data-toast-stack-hovering");
        container.removeAttribute("data-toast-stack-active");
        return;
      }
      container.setAttribute("data-toast-stack-active", "");
      const spacingSource = toasts[0] || container;
      const computed = view.getComputedStyle(spacingSource);
      const gap = readPixels(
        computed.getPropertyValue("--moo-toast-stack-gap"),
        computed,
      );
      const peek = readPixels(
        computed.getPropertyValue("--moo-toast-stack-peek"),
        computed,
      );
      const scaleStep = readNumber(
        computed.getPropertyValue("--moo-toast-stack-scale-step"),
        0.1,
      );
      const minScale = readNumber(
        computed.getPropertyValue("--moo-toast-stack-min-scale"),
        0.5,
      );

      toasts.sort((left, right) => {
        const leftSequence = Number.parseInt(
          left.dataset.toastStackSequence || "0",
          10,
        );
        const rightSequence = Number.parseInt(
          right.dataset.toastStackSequence || "0",
          10,
        );
        return (Number.isFinite(rightSequence) ? rightSequence : 0) -
          (Number.isFinite(leftSequence) ? leftSequence : 0);
      });

      const stackHeight = toasts[0]?.offsetHeight ||
        toasts[0]?.getBoundingClientRect().height || 0;
      let expandedOffset = 0;
      toasts.forEach((toast, index) => {
        const height = toast.offsetHeight || toast.getBoundingClientRect().height;
        const scale = Math.max(minScale, 1 - index * scaleStep);
        const collapsedOffset = -(
          index * peek + (1 - scale) * stackHeight
        );
        const limited = index >= toastStackVisibleLimit;

        toast.dataset.toastStackIndex = String(index);
        if (limited) {
          toast.setAttribute("data-toast-stack-limited", "");
          toast.setAttribute("inert", "");
        } else {
          toast.removeAttribute("data-toast-stack-limited");
          toast.removeAttribute("inert");
        }
        toast.style.setProperty(
          "--moo-toast-stack-collapsed-y",
          `${collapsedOffset}px`,
        );
        toast.style.setProperty(
          "--moo-toast-stack-expanded-y",
          `${expandedOffset}px`,
        );
        toast.style.setProperty("--moo-toast-stack-scale", String(scale));
        toast.style.setProperty(
          "--moo-toast-stack-z",
          String(1000 - index),
        );
        expandedOffset -= height + gap;
      });
    };
    const isPointerInsideToastStack = (container, event) => {
      if (!isStackContainer(container)) {
        return false;
      }
      return Array.from(container.children).some((child) => {
        if (
          !(child instanceof view.HTMLElement) ||
          !child.classList.contains("toast") ||
          child.hasAttribute("data-toast-stack-limited")
        ) {
          return false;
        }
        const rect = child.getBoundingClientRect();
        return event.clientX >= rect.left &&
          event.clientX <= rect.right &&
          event.clientY >= rect.top &&
          event.clientY <= rect.bottom;
      });
    };
    const markToastStackHovering = (container) => {
      if (!isStackContainer(container)) {
        return;
      }
      container.setAttribute("data-toast-stack-hovering", "");
      updateToastStack(container);
    };
    const releaseToastStackHovering = (container) => {
      if (!isStackContainer(container)) {
        return;
      }
      container.removeAttribute("data-toast-stack-hovering");
      updateToastStack(container);
    };

    const hideToastFromDismissControl = (dismiss) => {
      if (
        !(dismiss instanceof view.HTMLElement) ||
        dismiss.matches(":disabled, [aria-disabled='true']")
      ) {
        return;
      }
      const target = dismiss.closest(".toast");
      if (target) {
        const instance = Toast.getOrCreateInstance(target);
        bootstrapInstances.add(instance);
        instance.hide();
      }
    };
    listen(root, "pointerover", (event) => {
      const toast = event.target instanceof view.Element
        ? event.target.closest(".toast")
        : null;
      const container = getStackContainer(toast);
      if (container && toast?.parentElement === container) {
        markToastStackHovering(container);
      }
    }, true);
    listen(root, "pointermove", (event) => {
      root
        .querySelectorAll(
          '.toast-container--stacked[data-toast-stack="deck"][data-toast-stack-hovering]',
        )
        .forEach((container) => {
          if (
            isStackContainer(container) &&
            !isPointerInsideToastStack(container, event)
          ) {
            releaseToastStackHovering(container);
          }
        });
    }, true);
    listen(root, "click", (event) => {
      const trigger = event.target instanceof view.Element
        ? event.target.closest("[data-toast-target]")
        : null;
      const selector = trigger?.dataset.toastTarget || "";
      const id = selector.startsWith("#") ? selector.slice(1) : selector;
      const target = id ? root.getElementById(id) : null;
      if (
        target instanceof view.HTMLTemplateElement &&
        target.dataset.toastTemplate === "toast"
      ) {
        const template = target;
        const sourceContainer = template.parentElement;
        const fragment = template.content.cloneNode(true);
        const toast = fragment.firstElementChild;
        if (
          !(sourceContainer instanceof view.HTMLElement) ||
          !(toast instanceof view.HTMLElement) ||
          !toast.classList.contains("toast")
        ) {
          return;
        }
        const container = getSharedToastStack(sourceContainer, trigger);
        const sequence = ++toastSequence;
        toast.id = `${template.id}-${sequence}`;
        toast.setAttribute("data-toast-generated", "true");
        toast.setAttribute("data-toast-stack-sequence", String(sequence));
        toast.setAttribute("data-toast-stack-entering", "");
        container.prepend(toast);
        updateToastStack(container, toast);
        const instance = Toast.getOrCreateInstance(toast, { animation: false });
        bootstrapInstances.add(instance);
        instance.show();
        view.setTimeout(() => {
          view.requestAnimationFrame(() => {
            if (toast.isConnected) {
              toast.removeAttribute("data-toast-stack-entering");
            }
          });
        }, 80);
      } else if (target instanceof view.HTMLElement) {
        const instance = Toast.getOrCreateInstance(target);
        bootstrapInstances.add(instance);
        instance.show();
      }
    });
    listen(root, "show.bs.toast", (event) => {
      const toast = event.target;
      const container = getStackContainer(toast);
      if (container) {
        updateToastStack(container, toast);
      }
    }, true);
    listen(root, "shown.bs.toast", (event) => {
      const toast = event.target;
      const container = getStackContainer(toast);
      if (container) {
        updateToastStack(container, toast);
      }
    }, true);
    listen(root, "hidden.bs.toast", (event) => {
      const toast = event.target;
      if (!(toast instanceof view.HTMLElement) || !toast.classList.contains("toast")) {
        return;
      }
      const container = getStackContainer(toast);
      clearToastStackState(toast);
      if (toast.dataset.toastGenerated === "true") {
        const instance = Toast.getInstance(toast);
        if (instance) {
          bootstrapInstances.delete(instance);
          instance.dispose();
        }
        toast.remove();
      }
      if (container) {
        updateToastStack(container);
      }
    }, true);
    listen(root, "keydown", (event) => {
      const dismiss = event.target instanceof view.Element
        ? event.target.closest('[data-bs-dismiss="toast"]')
        : null;
      if (
        !dismiss ||
        !event.ctrlKey ||
        !event.altKey ||
        (event.key !== " " && event.key !== "Spacebar")
      ) {
        return;
      }
      event.preventDefault();
      hideToastFromDismissControl(dismiss);
    });
  }

  root.querySelectorAll("form.needs-validation").forEach((form) => {
    listen(form, "submit", (event) => {
      event.preventDefault();
      if (!form.checkValidity()) {
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  const dispose = () => {
    listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    modalPortals.forEach((original, modal) => {
      restorePortaledElement(modal, original);
    });
    modalPortals.clear();
    sheetPortals.forEach((original, sheet) => {
      restorePortaledElement(sheet, original);
    });
    sheetPortals.clear();
    sharedToastStacks.forEach((stacks) => {
      stacks.forEach((container) => container.remove());
    });
    sharedToastStacks.clear();
    bootstrapInstances.forEach((instance) => instance.dispose());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

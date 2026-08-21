const states = new WeakMap();

export function initBootstrapPreview(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const listeners = [];
  const modalPlaceholders = new Map();
  const bootstrapInstances = new Set();
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

  const onModalShow = (event) => {
    const modal = event.target;
    if (
      !(modal instanceof view.HTMLElement) ||
      !modal.classList.contains("modal") ||
      !modal.closest(".moo-catalog") ||
      modal.parentElement === root.body
    ) {
      return;
    }
    const placeholder = root.createComment("moo-modal-placeholder");
    modal.parentNode?.insertBefore(placeholder, modal);
    root.body.appendChild(modal);
    modalPlaceholders.set(modal, placeholder);
  };
  const onModalHidden = (event) => {
    const modal = event.target;
    if (!(modal instanceof view.HTMLElement)) {
      return;
    }
    const placeholder = modalPlaceholders.get(modal);
    if (placeholder?.parentNode) {
      placeholder.parentNode.insertBefore(modal, placeholder);
      placeholder.remove();
    }
    modalPlaceholders.delete(modal);
  };
  listen(root, "show.bs.modal", onModalShow, true);
  listen(root, "hidden.bs.modal", onModalHidden, true);

  const portalSheet = (sheet) => {
    if (
      !(sheet instanceof view.HTMLElement) ||
      !sheet.classList.contains("sheet") ||
      sheet.parentElement === root.body
    ) {
      return;
    }
    sheet.dataset.mooCatalogSheet = "true";
    root.body.appendChild(sheet);
  };
  listen(root, "click", (event) => {
    const target = event.target instanceof view.Element
      ? event.target
      : event.target?.parentElement;
    const trigger = target?.closest?.('[data-bs-toggle="offcanvas"][data-bs-target]');
    const selector = trigger?.getAttribute("data-bs-target");
    if (selector?.startsWith("#")) {
      portalSheet(root.querySelector(selector));
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
  root.querySelectorAll(".moo-catalog .offcanvas.sheet").forEach(portalSheet);

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
      bootstrapInstances.add(Tooltip.getOrCreateInstance(trigger, tooltipOptions));
    });
  }
  const Popover = view.bootstrap?.Popover;
  if (Popover) {
    root.querySelectorAll('[data-bs-toggle="popover"]').forEach((trigger) => {
      bootstrapInstances.add(Popover.getOrCreateInstance(trigger));
    });
  }
  const Toast = view.bootstrap?.Toast;
  if (Toast) {
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
    listen(root, "click", (event) => {
      const trigger = event.target instanceof view.Element
        ? event.target.closest("[data-toast-target]")
        : null;
      const selector = trigger?.dataset.mooToastTarget || "";
      const id = selector.startsWith("#") ? selector.slice(1) : selector;
      const target = id ? root.getElementById(id) : null;
      if (target) {
        const instance = Toast.getOrCreateInstance(target);
        bootstrapInstances.add(instance);
        instance.show();
      }
    });
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
    modalPlaceholders.forEach((placeholder, modal) => {
      if (placeholder.parentNode) {
        placeholder.parentNode.insertBefore(modal, placeholder);
        placeholder.remove();
      }
    });
    bootstrapInstances.forEach((instance) => instance.dispose());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

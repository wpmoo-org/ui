const instances = new WeakMap();

export default class Sidebar {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return Sidebar.getInstance(element) || new Sidebar(element, config);
  }

  constructor(element, config = {}) {
    if (element?.nodeType !== 1 || !element.matches('[data-slot="sidebar-wrapper"]')) {
      throw new TypeError("Sidebar requires a [data-slot=sidebar-wrapper] root.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._root = this._document.documentElement;
    this._sidebar = element.querySelector('[data-slot="sidebar"]');
    this._config = {
      breakpoint: "(min-width: 992px)",
      storagePrefix: "moo-sidebar:",
      keyboard: true,
      ...config,
    };
    this._listeners = [];
    this._tooltipAnchors = new Set();
    this._flyout = null;
    this._flyoutOwner = null;
    this._offcanvas = null;
    this._offcanvasTrigger = null;

    instances.set(element, this);
    this._bindEvents();
    this._restoreState();
    this._element.setAttribute("data-sidebar-ready", "");
    this._observeDirection();
  }

  dispose() {
    this._listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._listeners = [];
    this._directionObserver?.disconnect();
    this._closeFlyouts();
    this._element
      .querySelectorAll("[data-sidebar-dropdown-positioned]")
      .forEach((item) => this._clearDropdownPosition(item));
    this._element
      .querySelectorAll("[data-sidebar-tooltip]")
      .forEach((control) => this._disposeTooltip(control));
    this._offcanvas?.dispose();
    this._offcanvas = null;
    this._offcanvasTrigger = null;
    this._element.removeAttribute("data-sidebar-ready");
    instances.delete(this._element);
  }

  _listen(target, type, handler, options) {
    target?.addEventListener(type, handler, options);
    if (target) {
      this._listeners.push({ target, type, handler, options });
    }
  }

  _bootstrap(name) {
    return this._window.bootstrap?.[name] || null;
  }

  _isDesktop() {
    return this._window.matchMedia(this._config.breakpoint).matches;
  }

  _isCollapsed() {
    return this._isDesktop() && this._element.dataset.sidebarState === "collapsed";
  }

  _trigger(name, detail = {}) {
    return this._element.dispatchEvent(
      new this._window.CustomEvent(`${name}.moo.sidebar`, {
        bubbles: true,
        cancelable: name === "show" || name === "hide",
        detail,
      })
    );
  }

  _observeDirection() {
    const Observer = this._window.MutationObserver;
    if (!Observer) {
      return;
    }
    this._directionObserver = new Observer(() => {
      this._closeFlyouts();
      this._syncTooltips();
    });
    this._directionObserver.observe(this._root, {
      attributes: true,
      attributeFilter: ["dir"],
    });
  }

  _restoreState() {
    const key = this._element.dataset.sidebarKey;
    let stored = null;
    if (key) {
      try {
        stored = this._window.localStorage.getItem(this._config.storagePrefix + key);
      } catch (_) {
        stored = null;
      }
    }
    const initial =
      stored === "collapsed" || stored === "expanded"
        ? stored
        : this._element.dataset.sidebarState === "collapsed"
          ? "collapsed"
          : "expanded";
    this._setState(initial, false, false);
  }

  _setState(state, persist = true, emit = true) {
    const next = state === "collapsed" ? "collapsed" : "expanded";
    const previous = this._element.dataset.sidebarState;
    this._element.dataset.sidebarState = next;
    const key = this._element.dataset.sidebarKey;
    if (key === "catalog-shell") {
      this._root.dataset.sidebarCatalogState = next;
    }
    if (persist && key) {
      try {
        this._window.localStorage.setItem(this._config.storagePrefix + key, next);
      } catch (_) {
        /* Storage is best-effort in restricted browsing contexts. */
      }
    }
    this._syncControls();
    if (next === "expanded") {
      this._element
        .querySelectorAll(".sidebar-menu-item")
        .forEach((item) => this._resetFlyoutTrigger(item));
    }
    this._syncTooltips();
    if (emit && previous !== next) {
      this._trigger("change", { state: next, previousState: previous || null });
    }
  }

  _toggle() {
    this._setState(
      this._element.dataset.sidebarState === "collapsed" ? "expanded" : "collapsed"
    );
  }

  _syncControls() {
    const expanded = this._isDesktop()
      ? this._element.dataset.sidebarState === "expanded"
      : this._sidebar?.classList.contains("show") || false;
    this._element
      .querySelectorAll("[data-sidebar-trigger], [data-sidebar-rail]")
      .forEach((control) => control.setAttribute("aria-expanded", String(expanded)));
  }

  _resetFlyoutTrigger(item, expanded = null) {
    const trigger = item?.querySelector(":scope > .sidebar-menu-sub-trigger");
    const submenu = item?.querySelector(":scope > .sidebar-menu-sub");
    if (trigger && submenu) {
      trigger.setAttribute(
        "aria-expanded",
        String(expanded ?? submenu.classList.contains("show"))
      );
    }
  }

  _clearDropdownPosition(control) {
    const item = control?.matches?.(".sidebar-menu-item")
      ? control
      : control?.closest?.(".sidebar-menu-item");
    if (!item) {
      return;
    }
    delete item.dataset.sidebarDropdownPositioned;
    item.style.removeProperty("--moo-sidebar-dropdown-block-start");
    item.style.removeProperty("--moo-sidebar-dropdown-inline-start");
  }

  _closeDropdowns(exceptControl = null) {
    const Dropdown = this._bootstrap("Dropdown");
    this._element
      .querySelectorAll('[data-bs-toggle="dropdown"][aria-expanded="true"]')
      .forEach((control) => {
        if (control === exceptControl) {
          return;
        }
        if (Dropdown) {
          Dropdown.getOrCreateInstance(control).hide();
        } else {
          control.setAttribute("aria-expanded", "false");
          control
            .closest(".dropdown")
            ?.querySelector(".dropdown-menu.show")
            ?.classList.remove("show");
          this._clearDropdownPosition(control);
        }
      });
  }

  _positionDropdown(control) {
    const item = control?.closest?.(".sidebar-menu-item");
    const isHeaderWorkspace =
      control?.classList.contains("sidebar-menu-button--workspace") &&
      control.closest('[data-slot="sidebar-header"]');
    if (!control || !item || !isHeaderWorkspace || !this._isDesktop()) {
      this._clearDropdownPosition(control);
      return;
    }

    this._closeFlyouts();
    const rect = control.getBoundingClientRect();
    const gap = 4;
    const inlineStart =
      this._root.dir === "rtl"
        ? this._window.innerWidth - rect.left + gap
        : rect.right + gap;
    item.style.setProperty(
      "--moo-sidebar-dropdown-block-start",
      `${Math.round(rect.bottom + gap)}px`
    );
    item.style.setProperty(
      "--moo-sidebar-dropdown-inline-start",
      `${Math.round(inlineStart)}px`
    );
    item.dataset.sidebarDropdownPositioned = "";
  }

  _removeFlyoutPortal() {
    this._flyout?.remove();
    if (this._flyoutOwner) {
      this._resetFlyoutTrigger(this._flyoutOwner, false);
    }
    this._flyout = null;
    this._flyoutOwner = null;
  }

  _closeFlyouts() {
    this._removeFlyoutPortal();
    this._element.querySelectorAll(".sidebar-menu-item--flyout-open").forEach((item) => {
      item.classList.remove("sidebar-menu-item--flyout-open");
      item.style.removeProperty("--moo-sidebar-flyout-block-start");
      item.style.removeProperty("--moo-sidebar-flyout-inline-start");
      this._resetFlyoutTrigger(item, false);
    });
  }

  _openFlyout(item) {
    const submenu = item?.querySelector(":scope > .sidebar-menu-sub");
    const trigger = item?.querySelector(":scope > .sidebar-menu-sub-trigger");
    if (!item || !submenu || !this._isCollapsed()) {
      return;
    }
    if (this._flyoutOwner === item && this._flyout) {
      return;
    }

    this._closeDropdowns();
    this._closeFlyouts();
    const rect = item.getBoundingClientRect();
    const gap = 4;
    const inlineStart =
      this._root.dir === "rtl"
        ? this._window.innerWidth - rect.left + gap
        : rect.right + gap;
    const flyout = submenu.cloneNode(true);
    flyout.removeAttribute("id");
    flyout.classList.remove("collapse", "show", "collapsing");
    flyout.classList.add("sidebar-menu-flyout");
    flyout.dataset.sidebarFlyout = "";
    flyout.removeAttribute("style");
    flyout.style.setProperty("--moo-sidebar-flyout-block-start", `${Math.round(rect.top)}px`);
    flyout.style.setProperty(
      "--moo-sidebar-flyout-inline-start",
      `${Math.round(inlineStart)}px`
    );
    const root = this._element.closest(".moo-ui") || this._document.body;
    root.appendChild(flyout);
    this._flyout = flyout;
    this._flyoutOwner = item;
    item.classList.add("sidebar-menu-item--flyout-open");
    trigger?.setAttribute("aria-expanded", "true");
  }

  _tooltipAnchor(control) {
    return control.closest("li") || control;
  }

  _isIdentityTrigger(control) {
    return (
      control.closest(".sidebar-menu-item--account") ||
      control.classList.contains("sidebar-menu-button--workspace")
    );
  }

  _disposeTooltip(control) {
    const Tooltip = this._bootstrap("Tooltip");
    if (!Tooltip || !control) {
      return;
    }
    const anchor = this._tooltipAnchor(control);
    Tooltip.getInstance(anchor)?.dispose();
    this._tooltipAnchors.delete(anchor);
    anchor.removeAttribute("title");
    anchor.removeAttribute("data-bs-title");
    anchor.removeAttribute("data-bs-original-title");
    anchor.removeAttribute("aria-describedby");
  }

  _syncTooltips() {
    const Tooltip = this._bootstrap("Tooltip");
    if (!Tooltip) {
      return;
    }
    const collapsed = this._isCollapsed();
    const placement = this._root.dir === "rtl" ? "left" : "right";
    this._element.querySelectorAll("[data-sidebar-tooltip]").forEach((control) => {
      this._disposeTooltip(control);
      if (
        !collapsed ||
        this._isIdentityTrigger(control) ||
        control.closest(".sidebar-menu-item")?.querySelector(":scope > .sidebar-menu-sub")
      ) {
        return;
      }

      // Bootstrap permits one plugin instance per element. A dropdown or
      // collapse trigger keeps that instance slot; its neutral <li> owns the
      // state-driven Sidebar tooltip instead.
      const anchor = this._tooltipAnchor(control);
      new Tooltip(anchor, {
        title: control.getAttribute("data-sidebar-tooltip"),
        placement,
        container: "body",
        trigger: "hover focus",
      });
      this._tooltipAnchors.add(anchor);
    });
  }

  _bindEvents() {
    this._listen(this._sidebar, "shown.bs.offcanvas", () => this._syncControls());
    this._listen(this._sidebar, "hidden.bs.offcanvas", () => {
      this._syncControls();
      const trigger = this._offcanvasTrigger;
      this._offcanvasTrigger = null;
      if (trigger?.isConnected) {
        trigger.focus();
      }
    });
    this._listen(this._document, "show.bs.dropdown", (event) => {
      const control = this._dropdownControl(event.target);
      if (!control) {
        return;
      }
      this._closeDropdowns(control);
      this._disposeTooltip(control);
      this._positionDropdown(control);
    });
    this._listen(this._document, "hidden.bs.dropdown", (event) => {
      const control = this._dropdownControl(event.target);
      if (!control) {
        return;
      }
      this._clearDropdownPosition(control);
      this._syncTooltips();
    });
    this._listen(this._element, "click", (event) => this._handleControlClick(event));
    this._listen(this._window, "click", (event) => this._handleSubmenuClick(event), true);
    this._listen(this._document, "click", (event) => this._handleOutsideFlyoutClick(event));
    this._listen(this._document, "keydown", (event) => this._handleShortcut(event));
    this._listen(this._window, "resize", () => {
      this._closeFlyouts();
      this._element
        .querySelectorAll("[data-sidebar-dropdown-positioned]")
        .forEach((item) => this._clearDropdownPosition(item));
      this._syncControls();
      this._syncTooltips();
    });
  }

  _dropdownControl(target) {
    if (!(target instanceof this._window.Element) || !this._element.contains(target)) {
      return null;
    }
    if (target.matches('[data-bs-toggle="dropdown"][data-sidebar-tooltip]')) {
      return target;
    }
    return target.querySelector?.(
      '[data-bs-toggle="dropdown"][data-sidebar-tooltip]'
    ) || null;
  }

  _handleControlClick(event) {
    const target = event.target;
    const control = target instanceof this._window.Element
      ? target.closest("[data-sidebar-trigger], [data-sidebar-rail]")
      : null;
    if (!control || !this._element.contains(control)) {
      return;
    }
    if (this._isDesktop()) {
      event.preventDefault();
      this._closeFlyouts();
      this._toggle();
      return;
    }
    if (!control.matches("[data-sidebar-trigger]")) {
      return;
    }
    const sidebar = this._document.getElementById(control.getAttribute("aria-controls"));
    const Offcanvas = this._bootstrap("Offcanvas");
    if (sidebar && Offcanvas) {
      this._offcanvasTrigger = control;
      this._offcanvas = Offcanvas.getOrCreateInstance(sidebar);
      this._offcanvas.toggle();
    }
  }

  _handleSubmenuClick(event) {
    const target = event.target;
    const trigger = target instanceof this._window.Element
      ? target.closest(".sidebar-menu-sub-trigger")
      : null;
    const item = trigger?.closest(".sidebar-menu-item");
    if (!trigger || !item || !this._element.contains(item) || !this._isCollapsed()) {
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    if (this._flyoutOwner === item && this._flyout) {
      this._closeFlyouts();
    } else {
      this._openFlyout(item);
    }
  }

  _handleOutsideFlyoutClick(event) {
    if (!this._flyout) {
      return;
    }
    if (this._flyout.contains(event.target)) {
      this._closeFlyouts();
    } else if (!this._flyoutOwner?.contains(event.target)) {
      this._closeFlyouts();
    }
  }

  _handleShortcut(event) {
    const target = event.target;
    const isEditable =
      target instanceof this._window.Element &&
      (target.matches("input, textarea, select") || target.isContentEditable);
    if (
      event.defaultPrevented ||
      event.isComposing ||
      isEditable ||
      !this._config.keyboard ||
      !(event.metaKey || event.ctrlKey) ||
      event.key.toLowerCase() !== "b" ||
      !this._isDesktop()
    ) {
      return;
    }
    const preferred =
      this._document.querySelector(
        '[data-slot="sidebar-wrapper"][data-sidebar-key]'
      ) || this._document.querySelector('[data-slot="sidebar-wrapper"]');
    if (preferred !== this._element) {
      return;
    }
    event.preventDefault();
    this._closeFlyouts();
    this._toggle();
  }
}

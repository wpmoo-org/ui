/*!
 * Moo UI sidebar.js v1.0.0-rc.7 (https://ui.wpmoo.org/)
 * Copyright 2026 WPMoo (https://wpmoo.org)
 * Licensed under MIT (https://github.com/wpmoo-org/ui/blob/main/LICENSE)
 */
var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// src/js/theme-owner.js
var OWNER_SELECTOR = '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';
var PORTAL_SELECTOR = "[data-moo-overlay-portal-host]";
function documentFor(node) {
  if (node?.nodeType === 9) return node;
  if (node?.ownerDocument) return node.ownerDocument;
  return typeof document === "undefined" ? null : document;
}
__name(documentFor, "documentFor");
function isResolvedOwner(node) {
  return Boolean(node?.matches?.(OWNER_SELECTOR));
}
__name(isResolvedOwner, "isResolvedOwner");
function ownerRootFor(node) {
  const ownerDocument = documentFor(node);
  if (node?.nodeType === 9 || node === ownerDocument?.body) {
    return ownerDocument?.body?.firstElementChild || null;
  }
  return node;
}
__name(ownerRootFor, "ownerRootFor");
function findThemeOwner(node = typeof document === "undefined" ? null : document) {
  const start = ownerRootFor(node);
  if (!start) return null;
  if (isResolvedOwner(start)) return start;
  return start.closest?.(OWNER_SELECTOR) || null;
}
__name(findThemeOwner, "findThemeOwner");
function ownerPortalRoot(owner) {
  if (!owner) return null;
  return Array.from(owner.children || []).find(
    (child) => child.matches?.(PORTAL_SELECTOR)
  ) || owner;
}
__name(ownerPortalRoot, "ownerPortalRoot");

// src/js/components/sidebar.js
var instances = /* @__PURE__ */ new WeakMap();
var _Sidebar = class _Sidebar {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }
  static getOrCreateInstance(element, config = {}) {
    return _Sidebar.getInstance(element) || new _Sidebar(element, config);
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
    this._documentElement = this._document.documentElement;
    this._root = findThemeOwner(element) || this._document.body || this._documentElement;
    this._sidebar = element.querySelector('[data-slot="sidebar"]');
    this._config = {
      breakpoint: "(min-width: 992px)",
      storagePrefix: "moo-sidebar:",
      keyboard: true,
      ...config
    };
    this._listeners = [];
    this._tooltipAnchors = /* @__PURE__ */ new Set();
    this._flyout = null;
    this._flyoutOwner = null;
    this._offcanvas = null;
    this._offcanvasTrigger = null;
    instances.set(element, this);
    this._bindEvents();
    this._restoreState();
    this._scrollActiveItemIntoView();
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
    this._element.querySelectorAll("[data-sidebar-dropdown-positioned]").forEach((item) => this._clearDropdownPosition(item));
    this._element.querySelectorAll("[data-sidebar-tooltip]").forEach((control) => this._disposeTooltip(control));
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
  _portalRoot(trigger = this._element) {
    return ownerPortalRoot(findThemeOwner(trigger)) || this._document.body || this._documentElement;
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
        detail
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
    this._directionObserver.observe(this._documentElement, {
      attributes: true,
      attributeFilter: ["dir"]
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
    const initial = stored === "collapsed" || stored === "expanded" ? stored : this._element.dataset.sidebarState === "collapsed" ? "collapsed" : "expanded";
    this._setState(initial, false, false);
  }
  _scrollActiveItemIntoView() {
    const activeRoute = this._element.querySelector(
      '[data-slot="sidebar-content"] a[data-slot="sidebar-menu-button"][aria-current="page"], [data-slot="sidebar-content"] a.sidebar-menu-button[aria-current="page"], [data-slot="sidebar-content"] a.sidebar-menu-button.active'
    );
    const active = activeRoute || this._element.querySelector(
      '[data-slot="sidebar-content"] [data-slot="sidebar-menu-button"][aria-current="page"], [data-slot="sidebar-content"] .sidebar-menu-button[aria-current="page"], [data-slot="sidebar-content"] .sidebar-menu-button.active'
    );
    const content = active?.closest?.('[data-slot="sidebar-content"]');
    if (!active || !content || content.clientHeight <= 0) {
      return;
    }
    const maxScrollTop = content.scrollHeight - content.clientHeight;
    if (maxScrollTop <= 0) {
      return;
    }
    const contentRect = content.getBoundingClientRect();
    const activeRect = active.getBoundingClientRect();
    if (contentRect.height <= 0 || activeRect.height <= 0) {
      return;
    }
    const targetScrollTop = content.scrollTop + activeRect.top - contentRect.top - (content.clientHeight - activeRect.height) / 2;
    content.scrollTop = Math.round(
      Math.min(Math.max(targetScrollTop, 0), maxScrollTop)
    );
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
      }
    }
    this._syncControls();
    if (next === "expanded") {
      this._element.querySelectorAll(".sidebar-menu-item").forEach((item) => this._resetFlyoutTrigger(item));
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
    const expanded = this._isDesktop() ? this._element.dataset.sidebarState === "expanded" : this._sidebar?.classList.contains("show") || false;
    this._element.querySelectorAll("[data-sidebar-trigger], [data-sidebar-rail]").forEach((control) => control.setAttribute("aria-expanded", String(expanded)));
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
    const item = control?.matches?.(".sidebar-menu-item") ? control : control?.closest?.(".sidebar-menu-item");
    if (!item) {
      return;
    }
    delete item.dataset.sidebarDropdownPositioned;
    item.style.removeProperty("--moo-sidebar-dropdown-block-start");
    item.style.removeProperty("--moo-sidebar-dropdown-block-end");
    item.style.removeProperty("--moo-sidebar-dropdown-left");
    item.style.removeProperty("--moo-sidebar-dropdown-right");
  }
  _closeDropdowns(exceptControl = null) {
    const Dropdown = this._bootstrap("Dropdown");
    this._element.querySelectorAll('[data-bs-toggle="dropdown"][aria-expanded="true"]').forEach((control) => {
      if (control === exceptControl) {
        return;
      }
      if (Dropdown) {
        Dropdown.getOrCreateInstance(control).hide();
      } else {
        control.setAttribute("aria-expanded", "false");
        control.closest(".dropdown")?.querySelector(".dropdown-menu.show")?.classList.remove("show");
        this._clearDropdownPosition(control);
      }
    });
  }
  _positionDropdown(control) {
    const item = control?.closest?.(".sidebar-menu-item");
    const isHeaderWorkspace = control?.classList.contains("sidebar-menu-button--workspace") && control.closest('[data-slot="sidebar-header"]');
    const isFooterAccount = control?.classList.contains("sidebar-menu-button--account") && control.closest('[data-slot="sidebar-footer"]');
    if (!control || !item || !(isHeaderWorkspace || isFooterAccount) || !this._isDesktop()) {
      this._clearDropdownPosition(control);
      return;
    }
    this._closeFlyouts();
    const rect = control.getBoundingClientRect();
    const gap = 4;
    const sidebar = control.closest('[data-slot="sidebar"]');
    const side = sidebar?.dataset.side || "left";
    if (side === "right") {
      const right = this._window.innerWidth - rect.left + gap;
      item.style.setProperty(
        "--moo-sidebar-dropdown-right",
        `${Math.round(right)}px`
      );
      item.style.removeProperty("--moo-sidebar-dropdown-left");
    } else {
      const left = rect.right + gap;
      item.style.setProperty(
        "--moo-sidebar-dropdown-left",
        `${Math.round(left)}px`
      );
      item.style.removeProperty("--moo-sidebar-dropdown-right");
    }
    if (isHeaderWorkspace) {
      item.style.setProperty(
        "--moo-sidebar-dropdown-block-start",
        `${Math.round(rect.bottom + gap)}px`
      );
      item.style.removeProperty("--moo-sidebar-dropdown-block-end");
    } else {
      item.style.setProperty(
        "--moo-sidebar-dropdown-block-end",
        `${Math.round(this._window.innerHeight - rect.top + gap)}px`
      );
      item.style.removeProperty("--moo-sidebar-dropdown-block-start");
    }
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
      item.style.removeProperty("--moo-sidebar-flyout-left");
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
    const sidebar = this._sidebar;
    const sidebarRect = sidebar?.getBoundingClientRect() || rect;
    const gap = 4;
    const flyout = submenu.cloneNode(true);
    flyout.removeAttribute("id");
    flyout.classList.remove("collapse", "show", "collapsing");
    flyout.classList.add("sidebar-menu-flyout");
    flyout.dataset.sidebarFlyout = "";
    flyout.removeAttribute("style");
    flyout.style.setProperty("--moo-sidebar-flyout-block-start", `${Math.round(rect.top)}px`);
    const side = sidebar?.dataset.side || "left";
    this._portalRoot(item).appendChild(flyout);
    const flyoutWidth = flyout.getBoundingClientRect().width;
    const left = side === "right" ? sidebarRect.left - flyoutWidth - gap : sidebarRect.right + gap;
    const boundedLeft = Math.max(0, Math.min(this._window.innerWidth - flyoutWidth, left));
    flyout.style.setProperty("--moo-sidebar-flyout-left", `${Math.round(boundedLeft)}px`);
    this._flyout = flyout;
    this._flyoutOwner = item;
    item.classList.add("sidebar-menu-item--flyout-open");
    trigger?.setAttribute("aria-expanded", "true");
  }
  _tooltipAnchor(control) {
    return control.closest("li") || control;
  }
  _isIdentityTrigger(control) {
    return control.closest(".sidebar-menu-item--account") || control.classList.contains("sidebar-menu-button--workspace");
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
    const side = this._sidebar?.dataset.side || "left";
    const placement = side === "right" ? "left" : "right";
    this._element.querySelectorAll("[data-sidebar-tooltip]").forEach((control) => {
      this._disposeTooltip(control);
      if (!collapsed || this._isIdentityTrigger(control) || control.closest(".sidebar-menu-item")?.querySelector(":scope > .sidebar-menu-sub")) {
        return;
      }
      const anchor = this._tooltipAnchor(control);
      new Tooltip(anchor, {
        title: control.getAttribute("data-sidebar-tooltip"),
        placement,
        // Bootstrap's default tooltip offset is 6px. The icon rail's
        // boundary calculation still lets the tooltip box overlap the
        // physical Sidebar edge at that distance, so keep an explicit 8px
        // separation for both physical placements.
        offset: [0, 8],
        container: this._portalRoot(control),
        trigger: "hover focus"
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
      this._element.querySelectorAll("[data-sidebar-dropdown-positioned]").forEach((item) => this._clearDropdownPosition(item));
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
    const control = target instanceof this._window.Element ? target.closest("[data-sidebar-trigger], [data-sidebar-rail]") : null;
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
    const trigger = target instanceof this._window.Element ? target.closest(".sidebar-menu-sub-trigger") : null;
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
    const isEditable = target instanceof this._window.Element && (target.matches("input, textarea, select") || target.isContentEditable);
    if (event.defaultPrevented || event.isComposing || isEditable || !this._config.keyboard || !(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "b" || !this._isDesktop()) {
      return;
    }
    const preferred = this._document.querySelector(
      '[data-slot="sidebar-wrapper"][data-sidebar-key]'
    ) || this._document.querySelector('[data-slot="sidebar-wrapper"]');
    if (preferred !== this._element) {
      return;
    }
    event.preventDefault();
    this._closeFlyouts();
    this._toggle();
  }
};
__name(_Sidebar, "Sidebar");
var Sidebar = _Sidebar;
export {
  Sidebar as default
};

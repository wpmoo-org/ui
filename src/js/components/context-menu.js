const instances = new WeakMap();

function pointerRect(event) {
  const { clientX: x, clientY: y } = event;
  return { top: y, left: x, right: x, bottom: y, width: 0, height: 0, x, y };
}

function isDisabledTrigger(trigger) {
  return Boolean(trigger?.disabled || trigger?.getAttribute?.("aria-disabled") === "true");
}

function menuItemFromEvent(event) {
  const target = event.target;
  const item = target.closest?.(".dropdown-item");
  if (item) {
    return item;
  }
  return target.closest?.("li")?.querySelector(":scope > .dropdown-item") || null;
}

export default class ContextMenu {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return ContextMenu.getInstance(element) || new ContextMenu(element, config);
  }

  constructor(element, config = {}) {
    if (element?.nodeType !== 1 || !element.matches(".context-menu")) {
      throw new TypeError("ContextMenu requires a .context-menu root element.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._menu = element.querySelector(":scope > .context-menu-menu");
    this._fallback = element.querySelector(":scope > [data-context-menu-fallback]");
    if (!this._menu) {
      throw new TypeError("ContextMenu requires a .context-menu-menu element.");
    }
    if (!this._fallback) {
      throw new TypeError("ContextMenu requires an explicit fallback trigger.");
    }

    const Dropdown = this._bootstrap("Dropdown");
    if (!Dropdown) {
      throw new TypeError("ContextMenu requires bootstrap.Dropdown (bootstrap.bundle.js).");
    }

    this._config = { ...config };
    this._listeners = [];
    this._invoker = null;
    this._pointerRect = null;
    this._openMethod = null;
    this._reference = {
      getBoundingClientRect: () => this._currentRect(),
      contextElement: this._fallback,
    };
    this._dropdown = new Dropdown(this._fallback, {
      reference: this._reference,
      autoClose: "outside",
    });

    instances.set(element, this);
    this._bindEvents();
  }

  dispose() {
    this._listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._listeners = [];
    this._dropdown.dispose();
    this._syncExpanded(false);
    this._invoker = null;
    this._pointerRect = null;
    instances.delete(this._element);
  }

  show(anchor = this._fallback) {
    this._open(anchor, null);
  }

  hide() {
    this._dropdown.hide();
  }

  _listen(target, type, handler, options) {
    target.addEventListener(type, handler, options);
    this._listeners.push({ target, type, handler, options });
  }

  _bootstrap(name) {
    return this._window.bootstrap?.[name] || null;
  }

  _currentRect() {
    if (this._pointerRect) {
      return this._pointerRect;
    }
    return (this._invoker || this._fallback).getBoundingClientRect();
  }

  _trigger(name, cancelable = false) {
    return this._element.dispatchEvent(
      new this._window.CustomEvent(`${name}.moo.context-menu`, {
        bubbles: true,
        cancelable,
      })
    );
  }

  _triggers() {
    return Array.from(this._element.querySelectorAll(":scope > .context-menu-trigger"));
  }

  _syncExpanded(expanded) {
    this._triggers().forEach((trigger) => {
      trigger.setAttribute("aria-expanded", String(expanded));
    });
  }

  _menuItems() {
    return Array.from(this._menu.querySelectorAll(".dropdown-item")).filter(
      (item) => !isDisabledTrigger(item) && !item.classList.contains("disabled")
    );
  }

  _open(trigger, pointerEvent, openMethod) {
    if (isDisabledTrigger(trigger)) {
      return;
    }
    if (this._menu.classList.contains("show")) {
      this._dropdown.hide();
    }
    this._invoker = trigger;
    this._pointerRect = pointerEvent ? pointerRect(pointerEvent) : null;
    this._openMethod = openMethod;
    this._dropdown.show();
  }

  _handleContextMenu(event) {
    const trigger = event.target.closest(".context-menu-trigger");
    if (!trigger || !this._element.contains(trigger)) {
      return;
    }
    event.preventDefault();
    this._open(trigger, event, "pointer");
  }

  _handleKeydown(event) {
    const trigger = event.target.closest(".context-menu-trigger");
    if (!trigger || !this._element.contains(trigger)) {
      return;
    }
    const isShiftF10 = event.shiftKey && event.key === "F10";
    const isContextMenuKey = event.key === "ContextMenu";
    if (!isShiftF10 && !isContextMenuKey) {
      return;
    }
    event.preventDefault();
    this._open(trigger, null, "keyboard");
  }

  _handleFallbackClick() {
    this._invoker = this._fallback;
    this._pointerRect = null;
    this._openMethod = "pointer";
  }

  _handleFallbackKeydown(event) {
    if (event.key !== " " && event.key !== "Spacebar") {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (this._menu.classList.contains("show")) {
      this._dropdown.hide();
      return;
    }
    this._open(this._fallback, null, "fallback-keyboard");
  }

  _handleMenuClick(event) {
    const item = menuItemFromEvent(event);
    if (!item) {
      return;
    }
    const persistentItem = item.matches(".dropdown-item-check, [data-context-menu-persistent]");
    const disabledItem =
      item.matches('.dropdown-item.disabled, .dropdown-item[aria-disabled="true"], .dropdown-item:disabled') ||
      isDisabledTrigger(item);
    if (disabledItem) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    // Radio-grouped toggle buttons reuse the dropdown_toggle_item() button
    // Bootstrap's own roving arrow-key focus already picks up (it only ever
    // matches real .dropdown-item elements); Moo adds only the missing
    // mutual-exclusivity Bootstrap's independent button-toggle plugin does
    // not provide.
    const radioButton = item.matches("[data-context-menu-radio-group]") ? item : null;
    if (radioButton) {
      event.preventDefault();
      event.stopPropagation();
      const group = radioButton.dataset.contextMenuRadioGroup;
      this._menu
        .querySelectorAll(`[data-context-menu-radio-group="${group}"]`)
        .forEach((button) => {
          const checked = button === radioButton;
          button.classList.toggle("active", checked);
          button.setAttribute("aria-pressed", String(checked));
        });
      return;
    }
    if (persistentItem) {
      return;
    }
    this._dropdown.hide();
  }

  _bindEvents() {
    this._listen(this._element, "contextmenu", (event) => this._handleContextMenu(event));
    this._listen(this._element, "keydown", (event) => this._handleKeydown(event));
    this._listen(this._fallback, "click", () => this._handleFallbackClick());
    this._listen(this._fallback, "keydown", (event) => this._handleFallbackKeydown(event));
    this._listen(this._menu, "click", (event) => this._handleMenuClick(event));
    this._listen(this._fallback, "show.bs.dropdown", (event) => {
      if (!this._trigger("show", true)) {
        event.preventDefault();
      }
    });
    this._listen(this._fallback, "shown.bs.dropdown", () => {
      this._syncExpanded(true);
      // Bootstrap's own show() never focuses an item either -- only its
      // Up/Down-key handler does, since a pointer-driven open (right-click,
      // or a click on the fallback trigger) should let :hover carry the
      // highlight instead of a focus ring competing with it. A keyboard-
      // driven open (Shift+F10/ContextMenu key) still lands on the first
      // item, matching that same native arrow-key-open convention.
      if (this._openMethod === "fallback-keyboard") {
        this._fallback.focus();
      } else if (this._openMethod === "keyboard") {
        this._menuItems()[0]?.focus();
      } else {
        this._menu.focus();
      }
      this._trigger("shown");
    });
    this._listen(this._fallback, "hide.bs.dropdown", (event) => {
      if (!this._trigger("hide", true)) {
        event.preventDefault();
      }
    });
    this._listen(this._fallback, "hidden.bs.dropdown", () => {
      this._syncExpanded(false);
      const invoker = this._invoker;
      this._pointerRect = null;
      this._invoker = null;
      // A native Bootstrap click on the fallback trigger bypasses _open()
      // entirely (Bootstrap's own capture-phase click-to-toggle handler
      // calls show() directly), so _handleFallbackClick's bubble-phase
      // "click" listener always runs too late to set _openMethod before
      // shown.bs.dropdown reads it. Resetting it here, back to the neutral
      // pointer default, is what keeps that path correct rather than
      // inheriting whatever a prior keyboard-triggered open last set.
      this._openMethod = null;
      this._trigger("hidden");
      // Bootstrap's own dataApiKeydownHandler (js/src/dropdown.js) intercepts
      // Escape in the document capture phase and hardcodes
      // `getToggleButton.focus()` (our fallback trigger) after hide().
      // Nothing downstream of a capture-phase stopPropagation() can observe
      // that keydown to redirect focus, so correct it in a microtask, which
      // still runs before the next paint: if focus landed on the fallback
      // but a different trigger invoked this menu, return focus there.
      queueMicrotask(() => {
        if (invoker && invoker !== this._fallback && this._document.activeElement === this._fallback) {
          invoker.focus();
        }
      });
    });
  }
}

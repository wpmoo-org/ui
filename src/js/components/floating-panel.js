const instances = new WeakMap();
const memory = new WeakMap();

function canFocus(control) {
  return control.isConnected && !control.matches(":disabled") &&
    control.getClientRects().length > 0 &&
    !control.closest("[hidden], [inert]") &&
    control.ownerDocument.defaultView.getComputedStyle(control).visibility === "visible";
}

export default class FloatingPanel {
  static getInstance(panel) {
    return instances.get(panel) || null;
  }

  static getOrCreateInstance(panel) {
    return instances.get(panel) || new FloatingPanel(panel);
  }

  constructor(panel) {
    if (instances.has(panel)) return instances.get(panel);
    if (!panel?.matches?.("[data-floating-panel]") || !panel.id) {
      throw new TypeError("FloatingPanel requires a named panel");
    }
    this.panel = panel;
    this.document = panel.ownerDocument;
    this.owner = panel.closest(".moo-ui");
    this.initialHidden = panel.hidden;
    this.controls = new Map();
    this.launcher = null;
    this.key = panel.dataset.floatingPanelKey ? `moo-floating-panel:${panel.dataset.floatingPanelKey}` : "";
    const view = this.document.defaultView;
    if (!memory.has(view)) memory.set(view, new Map());
    this.memory = memory.get(view);
    this.onClick = event => this.handleControl(event);
    this.document.addEventListener("click", this.onClick);
    instances.set(panel, this);
    let dismissed = this.memory.get(this.key) || false;
    if (this.key && !this.memory.has(this.key)) {
      try { dismissed = view.localStorage.getItem(this.key) === "dismissed"; } catch { /* Memory-only fallback. */ }
    }
    this.setVisible(!dismissed);
    panel.dataset.floatingPanelReady = "true";
  }

  launchers() {
    return [...this.document.querySelectorAll("[data-floating-panel-open]")].filter(control =>
      control.dataset.floatingPanelOpen === this.panel.id && control.closest(".moo-ui") === this.owner);
  }

  setVisible(visible) {
    this.panel.hidden = !visible;
    this.panel.dataset.floatingPanelState = visible ? "visible" : "dismissed";
    this.launchers().forEach(control => {
      if (!this.controls.has(control)) this.controls.set(control, {
        controls: control.getAttribute("aria-controls"), expanded: control.getAttribute("aria-expanded"),
      });
      control.setAttribute("aria-controls", this.panel.id);
      control.setAttribute("aria-expanded", String(visible));
    });
  }

  handleControl(event) {
    const control = event.target.closest?.("[data-floating-panel-open], [data-floating-panel-dismiss]");
    if (!control || control.matches(":disabled") || control.closest(".moo-ui") !== this.owner) return;
    const opening = control.hasAttribute("data-floating-panel-open");
    if ((opening ? control.dataset.floatingPanelOpen : control.dataset.floatingPanelDismiss) !== this.panel.id) return;
    if (!opening && !this.panel.contains(control)) return;
    event.preventDefault();
    if (opening) this.launcher = control;
    if (this.key) {
      try {
        const storage = this.document.defaultView.localStorage;
        if (opening) storage.removeItem(this.key);
        else storage.setItem(this.key, "dismissed");
        this.memory.delete(this.key);
      } catch {
        // Keep unsaved local intent when storage reads or writes are blocked.
        this.memory.set(this.key, !opening);
      }
    }
    this.setVisible(opening);
    if (opening) {
      [...this.panel.querySelectorAll("button, a[href], input:not([type='hidden']), select, textarea, [tabindex]")]
        .find(control => control.tabIndex >= 0 && canFocus(control))?.focus({ preventScroll: true });
    } else {
      const launchers = this.launchers().filter(canFocus);
      const launcher = launchers.includes(this.launcher) ? this.launcher : launchers[0];
      launcher?.focus({ preventScroll: true });
    }
  }

  dispose() {
    if (instances.get(this.panel) !== this) return;
    this.document.removeEventListener("click", this.onClick);
    this.panel.hidden = this.initialHidden;
    delete this.panel.dataset.floatingPanelReady;
    delete this.panel.dataset.floatingPanelState;
    this.controls.forEach((attrs, control) => {
      for (const [name, value] of [["aria-controls", attrs.controls], ["aria-expanded", attrs.expanded]]) {
        if (value === null) control.removeAttribute(name);
        else control.setAttribute(name, value);
      }
    });
    instances.delete(this.panel);
  }
}

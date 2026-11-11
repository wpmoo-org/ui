// Consent card behaviour. The card, its switches and the policy table are
// server-rendered from one configuration; this module adds what HTML cannot
// do: it reads and writes the visitor's choice in a first-party cookie,
// shows the card when no valid choice exists, reopens it from any
// [data-consent-open] trigger, and activates gated scripts, frames and
// images (data-consent-category) only after their category is granted.
//
// A choice is valid while its revision equals the configuration's and it is
// younger than cookie.days. Optional categories always start unchecked.
// Withdrawing a category removes its declared first-party cookies and
// storage keys and reloads the page, because executed scripts cannot be
// unloaded.
//
// On first visit the card is shown without moving or trapping focus. When a
// trigger opens it, focus moves to its title and stays inside until the
// visitor closes it with Escape or a button; focus then returns to the
// trigger.
const instances = new WeakMap();
const documents = new WeakMap();
const RECORD_VERSION = 1;
const DAY_SECONDS = 86400;
const FOCUSABLE = "button, a[href], input:not([type='hidden']), select, textarea, [tabindex]:not([tabindex='-1'])";

function matches(pattern, name) {
  return pattern.endsWith("*") ? name.startsWith(pattern.slice(0, -1)) : name === pattern;
}

/**
 * Revision of a configuration: the first 12 hex digits of SHA-256 over the
 * sorted "<category>/<service>" lines of every shown category and service,
 * followed by "reask:<n>" when n > 0. Hosts compute it the same way.
 */
export async function consentRevision(categories, reask = 0) {
  const lines = [];
  for (const category of categories || []) {
    for (const service of category.services || []) lines.push(`${category.id}/${service.id}`);
  }
  lines.sort();
  if (reask > 0) lines.push(`reask:${reask}`);
  const bytes = new TextEncoder().encode(lines.join("\n"));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("").slice(0, 12);
}

export default class ConsentManager {
  /** The manager bound to a [data-consent] element or to a document. */
  static getInstance(target) {
    if (target?.nodeType === 9) return documents.get(target) || null;
    return target?.nodeType === 1 ? instances.get(target) || null : null;
  }

  static getOrCreateInstance(element, options) {
    return ConsentManager.getInstance(element) || new ConsentManager(element, options);
  }

  constructor(element, { reload } = {}) {
    if (element?.nodeType !== 1 || !element.matches("[data-consent]") || !element.id) {
      throw new TypeError("ConsentManager requires a named [data-consent] element.");
    }
    const existing = instances.get(element);
    if (existing) return existing;
    this._element = element;
    this._document = element.ownerDocument;
    if (documents.has(this._document)) {
      throw new TypeError("ConsentManager allows one consent card per document.");
    }
    this._window = this._document.defaultView;
    const source = element.querySelector("script[data-consent-config]");
    if (!source) throw new TypeError("ConsentManager requires a [data-consent-config] script.");
    this._config = JSON.parse(source.textContent);
    this._cookie = { name: "moo_consent", days: 365, ...(this._config.cookie || {}) };
    this._categories = this._config.categories || [];
    this._optional = this._categories.filter((category) => !category.required).map((category) => category.id);
    this._reload = reload || (() => this._window.location.reload());
    this._waiting = new Map();
    this._listeners = [];
    this._trapping = false;
    this._returnFocus = null;

    const record = this._read();
    this._valid = Boolean(record);
    this._choices = this._normalize(record ? record.c : {});

    const control = (suffix) => this._document.getElementById(`${element.id}-${suffix}`);
    const actions = [
      [control("accept"), () => this.acceptAll()],
      [control("decline"), () => this.declineAll()],
      [control("save"), () => this.save(this._switchChoices(), "save")],
    ];
    for (const [button, action] of actions) {
      if (button) this._listen(button, "click", action);
    }
    this._listen(this._document, "click", (event) => this._onDocumentClick(event));
    this._listen(element, "keydown", (event) => this._onKeydown(event));

    instances.set(element, this);
    documents.set(this._document, this);
    this.activate(this._document);
    if (!this._valid) this._show();
    this.ready = Promise.resolve(this);
    queueMicrotask(() => this._emit("ready", { choices: this.choices, valid: this._valid, revision: this.revision }));
  }

  get revision() {
    return String(this._config.revision);
  }

  get valid() {
    return this._valid;
  }

  get choices() {
    return { ...this._choices };
  }

  get isOpen() {
    return !this._element.hidden;
  }

  granted(id) {
    const category = this._categories.find((entry) => entry.id === id);
    if (!category) return false;
    return category.required ? true : this._valid && this._choices[id] === true;
  }

  /** Runs callback now if granted, otherwise on grant. Returns an unsubscribe function. */
  whenGranted(id, callback) {
    if (this.granted(id)) {
      callback(this);
      return () => {};
    }
    if (!this._waiting.has(id)) this._waiting.set(id, new Set());
    this._waiting.get(id).add(callback);
    return () => this._waiting.get(id)?.delete(callback);
  }

  acceptAll() {
    return this.save(Object.fromEntries(this._optional.map((id) => [id, true])), "accept-all");
  }

  declineAll() {
    return this.save({}, "decline");
  }

  grant(id) {
    return this.save({ ...this._choices, [id]: true }, "grant");
  }

  deny(id) {
    return this.save({ ...this._choices, [id]: false }, "deny");
  }

  /** Stores the choice; optional categories not named become false. */
  save(choices, source = "save") {
    const previous = this._valid ? this.choices : this._normalize({});
    const wasValid = this._valid;
    const next = this._normalize(choices);
    this._write(next);
    this._valid = true;
    this._choices = next;
    const granted = this._optional.filter((id) => next[id] && !previous[id]);
    const revoked = wasValid ? this._optional.filter((id) => previous[id] && !next[id]) : [];
    this.close();
    this.activate(this._document);
    for (const id of granted) {
      const waiting = this._waiting.get(id);
      this._waiting.delete(id);
      waiting?.forEach((callback) => callback(this));
    }
    this._emit("change", { choices: this.choices, previous, granted, revoked, source });
    if (revoked.length) {
      revoked.forEach((id) => this._forget(id));
      this._reload();
    }
    return this.choices;
  }

  /** Opens the card with the stored choices; traps focus until closed. */
  open(trigger = null) {
    this._returnFocus = trigger;
    this._trapping = true;
    this._show();
    this._document.getElementById(`${this._element.id}-title`)?.focus({ preventScroll: true });
    this._emit("open", {});
  }

  /** Hides the card; it stays open while no valid choice exists. */
  close() {
    if (!this._valid) return false;
    const wasOpen = this.isOpen;
    const returnFocus = this._trapping ? this._returnFocus : null;
    this._element.hidden = true;
    this._trapping = false;
    this._returnFocus = null;
    if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
    if (wasOpen) this._emit("close", {});
    return true;
  }

  /** Activates gated elements under root whose category is granted. */
  activate(root = this._document, only = null) {
    for (const element of root.querySelectorAll("[data-consent-category]")) {
      const id = element.getAttribute("data-consent-category");
      if (only ? id === only : this.granted(id)) this._activateElement(element);
    }
    for (const placeholder of root.querySelectorAll("[data-consent-placeholder]")) {
      const id = placeholder.getAttribute("data-consent-placeholder");
      if (only ? id === only : this.granted(id)) placeholder.hidden = true;
    }
  }

  dispose() {
    if (instances.get(this._element) !== this) return;
    this._listeners.forEach(([target, type, handler]) => target.removeEventListener(type, handler));
    this._listeners = [];
    this._waiting.clear();
    instances.delete(this._element);
    documents.delete(this._document);
  }

  _listen(target, type, handler) {
    target.addEventListener(type, handler);
    this._listeners.push([target, type, handler]);
  }

  _emit(name, detail) {
    this._document.dispatchEvent(new this._window.CustomEvent(`moo:consent:${name}`, { bubbles: true, detail }));
  }

  _normalize(choices) {
    return Object.fromEntries(this._optional.map((id) => [id, choices?.[id] === true || choices?.[id] === 1]));
  }

  _switch(id) {
    return this._document.getElementById(`${this._element.id}-category-${id}`);
  }

  _switchChoices() {
    return Object.fromEntries(this._optional.map((id) => [id, Boolean(this._switch(id)?.checked)]));
  }

  _show() {
    for (const id of this._optional) {
      const input = this._switch(id);
      if (input) input.checked = this.granted(id);
    }
    this._element.hidden = false;
  }

  _read() {
    const prefix = `${this._cookie.name}=`;
    const raw = this._document.cookie.split("; ").find((part) => part.startsWith(prefix));
    if (!raw) return null;
    try {
      const record = JSON.parse(decodeURIComponent(raw.slice(prefix.length)));
      const age = Date.now() / 1000 - Number(record.t);
      if (record.v !== RECORD_VERSION || record.r !== this.revision) return null;
      if (!(age >= 0 && age < this._cookie.days * DAY_SECONDS)) return null;
      return record;
    } catch {
      return null;
    }
  }

  _write(choices) {
    const record = {
      v: RECORD_VERSION,
      r: this.revision,
      t: Math.floor(Date.now() / 1000),
      c: Object.fromEntries(Object.entries(choices).map(([id, value]) => [id, value ? 1 : 0])),
    };
    const secure = this._window.location.protocol === "https:" ? "; Secure" : "";
    this._document.cookie = `${this._cookie.name}=${encodeURIComponent(JSON.stringify(record))}; Path=/; Max-Age=${this._cookie.days * DAY_SECONDS}; SameSite=Lax${secure}`;
  }

  _forget(id) {
    const category = this._categories.find((entry) => entry.id === id);
    const host = this._window.location.hostname;
    const parts = host.split(".");
    const domains = [""];
    for (let index = 0; index < parts.length - 1; index += 1) domains.push(`; Domain=${parts.slice(index).join(".")}`);
    const cookieNames = this._document.cookie.split("; ").map((part) => part.split("=")[0]).filter(Boolean);
    for (const item of category?.storage || []) {
      if (item.type === "cookie") {
        for (const name of cookieNames.filter((candidate) => matches(item.name, candidate))) {
          for (const domain of domains) this._document.cookie = `${name}=; Path=/; Max-Age=0${domain}`;
        }
      } else {
        try {
          const storage = item.type === "local" ? this._window.localStorage : this._window.sessionStorage;
          Object.keys(storage).filter((key) => matches(item.name, key)).forEach((key) => storage.removeItem(key));
        } catch {
          // Storage is blocked; there is nothing to remove.
        }
      }
    }
  }

  _activateElement(element) {
    if (element.hasAttribute("data-consent-active")) return;
    const src = element.getAttribute("data-consent-src");
    if (element.localName === "script") {
      const script = this._document.createElement("script");
      for (const { name, value } of element.attributes) {
        if (name !== "type" && !name.startsWith("data-consent-")) script.setAttribute(name, value);
      }
      const type = element.getAttribute("data-consent-type");
      if (type) script.type = type;
      if (src) script.src = src;
      else script.textContent = element.textContent;
      script.setAttribute("data-consent-category", element.getAttribute("data-consent-category"));
      script.setAttribute("data-consent-active", "");
      element.replaceWith(script);
      return;
    }
    element.setAttribute("data-consent-active", "");
    if (src) element.setAttribute("src", src);
    element.hidden = false;
  }

  _onDocumentClick(event) {
    const control = event.target.closest?.("[data-consent-open], [data-consent-grant]");
    if (!control || control.matches(":disabled")) return;
    if (control.hasAttribute("data-consent-open")) {
      if (control.getAttribute("data-consent-open") !== this._element.id) return;
      event.preventDefault();
      this.open(control);
      return;
    }
    const id = control.getAttribute("data-consent-grant");
    if (!this._categories.some((category) => category.id === id)) return;
    event.preventDefault();
    const placeholder = control.closest("[data-consent-placeholder]");
    const scope = control.closest("[data-consent-embed]") || placeholder?.parentElement;
    if (placeholder?.querySelector("[data-consent-remember]")?.checked || !scope) {
      this.grant(id);
    } else {
      this.activate(scope, id);
    }
  }

  _onKeydown(event) {
    if (!this._trapping) return;
    if (event.key === "Escape") {
      if (this.close()) event.preventDefault();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(this._element.querySelectorAll(FOCUSABLE))
      .filter((control) => !control.matches(":disabled") && control.getClientRects().length > 0);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = this._document.activeElement;
    if (event.shiftKey && (active === first || !this._element.contains(active) || active.id === `${this._element.id}-title`)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }
}

/** Binds the consent card under root; returns the manager or null. */
export function initConsent(root = document, options) {
  const element = root.querySelector?.("[data-consent]");
  return element ? ConsentManager.getOrCreateInstance(element, options) : null;
}

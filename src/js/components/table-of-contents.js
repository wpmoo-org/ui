const instances = new WeakMap();
const ownerSelector = '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';

function activationOffset(options, previous = 0) {
  if (!options || typeof options !== "object" || Array.isArray(options)) {
    throw new TypeError("TableOfContents options must be an object.");
  }
  const value = options.activationOffset === undefined ? previous : options.activationOffset;
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) {
    throw new TypeError("TableOfContents activationOffset must be a finite nonnegative number.");
  }
  return value;
}

function fragmentId(href) {
  if (!href?.startsWith("#") || href.length === 1) return null;
  try {
    return decodeURIComponent(href.slice(1));
  } catch {
    return null;
  }
}

export default class TableOfContents {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, options = {}) {
    return TableOfContents.getInstance(element) || new TableOfContents(element, options);
  }

  constructor(element, options = {}) {
    if (element?.nodeType !== 1 || !element.matches("[data-toc]")) {
      throw new TypeError("TableOfContents requires a [data-toc] root element.");
    }
    const existing = instances.get(element);
    if (existing) return existing;
    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._offset = activationOffset(options);
    this._listeners = [];
    this._originalLinks = new Map();
    this._originalStatus = new Map();
    this._links = [];
    this._targets = [];
    this._frame = 0;
    this._disposed = false;
    instances.set(element, this);
    this.refresh();
  }

  refresh(options = {}) {
    if (this._disposed) return this;
    const offset = activationOffset(options, this._offset);
    this._clearListeners();
    this._offset = offset;
    const owner = this._element.closest(ownerSelector);
    const contentId = this._element.getAttribute("data-toc-content");
    const scope = contentId ? this._document.getElementById(contentId) : owner;
    const rootId = this._element.getAttribute("data-toc-scroll-root");
    this._scrollElement = rootId ? this._document.getElementById(rootId) : null;
    this._status = Array.from(this._element.querySelectorAll("[data-toc-current]"))
      .find((node) => node.closest("[data-toc]") === this._element) || null;
    if (this._status && !this._originalStatus.has(this._status)) {
      this._originalStatus.set(this._status, this._status.textContent);
    }
    this._overview = this._status ? this._originalStatus.get(this._status) : "";
    this._links = Array.from(this._element.querySelectorAll('a[href^="#"]'))
      .filter((link) => link.closest("[data-toc]") === this._element)
      .map((link) => ({ link, id: fragmentId(link.getAttribute("href")) }));
    this._links.forEach(({ link }) => {
      if (!this._originalLinks.has(link)) {
        this._originalLinks.set(link, {
          active: link.classList.contains("active"),
          current: link.getAttribute("aria-current"),
        });
      }
    });
    this._targets = [];
    this._activate(null);
    if (!owner || !scope || scope.closest(ownerSelector) !== owner ||
        (rootId && (!this._scrollElement || !this._scrollElement.contains(scope)))) {
      return this;
    }
    const seen = new Set();
    this._links.forEach(({ id, link }) => {
      const target = id ? this._document.getElementById(id) : null;
      if (!target || seen.has(id) || !scope.contains(target) || target.closest(ownerSelector) !== owner) return;
      seen.add(id);
      this._targets.push({ id, target, label: link.textContent.trim() });
    });
    if (!this._targets.length) return this;
    const queue = () => this._requestUpdate();
    this._listen(this._scrollElement || this._window, "scroll", queue, { passive: true });
    this._listen(this._window, "resize", queue);
    this._listen(this._window, "hashchange", queue);
    this._listen(this._element, "click", queue);
    this._update();
    return this;
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    this._clearListeners();
    this._originalLinks.forEach(({ active, current }, link) => {
      link.classList.toggle("active", active);
      if (current === null) link.removeAttribute("aria-current");
      else link.setAttribute("aria-current", current);
    });
    this._originalStatus.forEach((text, node) => { node.textContent = text; });
    this._originalLinks.clear();
    this._originalStatus.clear();
    this._targets = [];
    this._links = [];
    if (instances.get(this._element) === this) instances.delete(this._element);
  }

  _listen(target, type, handler, options) {
    target.addEventListener(type, handler, options);
    this._listeners.push({ target, type, handler, options });
  }

  _clearListeners() {
    this._listeners.forEach(({ target, type, handler, options }) => target.removeEventListener(type, handler, options));
    this._listeners = [];
    if (this._frame) this._window.cancelAnimationFrame(this._frame);
    this._frame = 0;
  }

  _requestUpdate() {
    if (this._disposed || this._frame) return;
    this._frame = this._window.requestAnimationFrame(() => {
      this._frame = 0;
      this._update();
    });
  }

  _update() {
    if (this._disposed) return;
    const targets = this._targets.filter(({ target }) => target.isConnected && target.getClientRects().length > 0);
    const scroller = this._scrollElement || this._document.scrollingElement;
    const line = (this._scrollElement ? this._scrollElement.getBoundingClientRect().top + this._scrollElement.clientTop : 0) + this._offset;
    let active = null;
    targets.forEach((entry) => {
      if (entry.target.getBoundingClientRect().top <= line + 1) active = entry;
    });
    const canScroll = scroller && scroller.scrollHeight > scroller.clientHeight + 1;
    if (!canScroll) {
      const hashId = fragmentId(this._window.location.hash);
      active = targets.find(({ id }) => id === hashId) || active;
    }
    if (targets.length && canScroll &&
        scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1) {
      active = targets[targets.length - 1];
    }
    this._activate(active);
  }

  _activate(active) {
    this._links.forEach(({ link, id }) => {
      const current = active !== null && id === active.id;
      link.classList.toggle("active", current);
      if (current) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
    if (this._status) this._status.textContent = active ? active.label : this._overview;
  }
}

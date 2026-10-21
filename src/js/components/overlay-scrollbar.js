const instances = new WeakMap();
let nextId = 0;

/** Opt-in scrollbar; the document or supplied element remains the native scroll owner. */
export default class OverlayScrollbar {
  static getInstance(owner, scrollElement = owner?.ownerDocument?.scrollingElement) {
    const instance = scrollElement && instances.get(scrollElement);
    return instance?._owner === owner ? instance : null;
  }

  static getOrCreateInstance(owner, options = {}) {
    return OverlayScrollbar.getInstance(owner, options.scrollElement) || new OverlayScrollbar(owner, options);
  }

  constructor(owner, { scrollElement = null, hideDelay = 900, label = "Page scroll position" } = {}) {
    if (!owner?.matches?.('.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]') || !owner.isConnected) {
      throw new TypeError("OverlayScrollbar requires a connected, resolved .moo-ui theme owner.");
    }
    if (!Number.isFinite(hideDelay) || hideDelay < 0 || typeof label !== "string" || !label.trim()) {
      throw new TypeError("OverlayScrollbar requires a nonnegative hideDelay and a nonempty label.");
    }
    const document = owner.ownerDocument;
    const root = scrollElement ?? document.scrollingElement;
    const isDocument = root === document.scrollingElement;
    if (root?.nodeType !== 1 || !root.isConnected || root.ownerDocument !== document ||
        (!isDocument && (!owner.contains(root) || root.closest('.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]') !== owner))) {
      throw new TypeError("OverlayScrollbar scrollElement must belong to the same resolved theme owner.");
    }
    const existing = instances.get(root);
    if (existing) {
      if (existing._owner === owner) return existing;
      throw new Error("Only one OverlayScrollbar theme owner may control a scroll element.");
    }
    this._owner = owner;
    this._document = document;
    this._window = document.defaultView;
    this._root = root;
    this._isDocument = isDocument;
    if (isDocument && root !== document.documentElement) {
      throw new TypeError("OverlayScrollbar requires a standards-mode document scroll root.");
    }
    this._hideDelay = hideDelay;
    this._listeners = [];
    this._frame = 0;
    this._timer = 0;
    this._disposed = false;
    this._originalNativeClass = this._root.classList.contains("scrollbar-overlay-native");
    this._originalId = this._root.getAttribute("id");
    this._forcedColors = this._window.matchMedia("(forced-colors: active)");
    this._bar = document.createElement("div");
    this._bar.className = "scrollbar-overlay";
    this._bar.tabIndex = 0;
    this._bar.setAttribute("role", "scrollbar");
    this._bar.setAttribute("aria-label", label);
    this._bar.setAttribute("aria-orientation", "vertical");
    this._bar.setAttribute("aria-valuemin", "0");
    this._thumb = document.createElement("div");
    this._thumb.className = "scrollbar-overlay-thumb";
    this._thumb.setAttribute("aria-hidden", "true");
    this._bar.append(this._thumb);
    owner.append(this._bar);
    // Do not hide the native scrollbar if the public stylesheet is missing.
    if (this._window.getComputedStyle(this._bar).position !== "fixed") {
      this._bar.remove();
      throw new Error("OverlayScrollbar requires the Moo UI overlay scrollbar stylesheet.");
    }
    if (!this._originalId) {
      do { this._generatedId = `scrollbar-overlay-page-${++nextId}`; }
      while (document.getElementById(this._generatedId));
      this._root.id = this._generatedId;
    }
    this._bar.setAttribute("aria-controls", this._root.id);
    instances.set(root, this);
    try {
      this._listen(isDocument ? this._window : root, "scroll", () => {
        this._reveal();
        this._queue();
      }, { passive: true });
      if (!isDocument) {
        this._listen(document, "scroll", () => this._queue(), { passive: true, capture: true });
      }
      this._listen(this._window, "resize", () => this._queue());
      this._listen(document, "pointermove", (event) => this._onPointerMove(event), { passive: true });
      this._listen(document, "pointerout", (event) => {
        if (event.pointerType === "mouse" && !event.relatedTarget) {
          this._nearEdge = false;
          if (!this._drag) delete this._bar.dataset.scrollbarInteractive;
          this._hideLater();
        }
      });
      this._listen(this._bar, "pointerdown", (event) => this._onPointerDown(event));
      this._listen(this._bar, "pointerup", () => this._finishDrag());
      this._listen(this._bar, "pointercancel", () => this._finishDrag());
      this._listen(this._bar, "lostpointercapture", () => this._finishDrag());
      this._listen(this._bar, "focus", () => this._reveal());
      this._listen(this._bar, "blur", () => this._hideLater());
      this._listen(this._bar, "keydown", (event) => this._onKeyDown(event));
      this._listen(this._forcedColors, "change", () => this.refresh());
      this._listen(this._window, "beforeprint", () => {
        this._printing = true;
        this.refresh();
      });
      this._listen(this._window, "afterprint", () => {
        this._printing = false;
        this.refresh();
      });
      this._resize = new this._window.ResizeObserver(() => this._queue());
      this._resize.observe(this._root);
      this._resize.observe(document.body);
      this._mutations = new this._window.MutationObserver(() => this._queue());
      this._mutations.observe(this._root, { attributes: true, attributeFilter: ["class", "style", "dir"] });
      if (!isDocument) {
        this._mutations.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "style", "dir"] });
      }
      this._mutations.observe(document.body, {
        attributes: true, attributeFilter: ["class", "style"],
      });
      this._mutations.observe(owner, { attributes: true, attributeFilter: ["class", "style", "dir", "data-bs-theme"] });
      this._contentMutations = new this._window.MutationObserver((records) => {
        if (records.some(record => record.target !== this._bar && !this._bar.contains(record.target))) this._queue();
      });
      this._contentMutations.observe(isDocument ? document.body : root, {
        childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style", "hidden"],
      });
      this._listen(root, "load", () => this._queue(), { capture: true });
      if (document.fonts) this._listen(document.fonts, "loadingdone", () => this._queue());
      this.refresh();
    } catch (error) {
      this.dispose();
      throw error;
    }
  }

  refresh() {
    if (this._disposed) return this;
    const window = this._window;
    const root = this._root;
    // Measure without the native gutter: viewport-width content can overflow
    // only because of that gutter. Genuine horizontal overflow stays native.
    const eligible = !this._forcedColors.matches && !this._printing;
    if (eligible) root.classList.add("scrollbar-overlay-native");
    const enabled = eligible && root.scrollWidth <= root.clientWidth + 1;
    root.classList.toggle("scrollbar-overlay-native", this._originalNativeClass || enabled);
    // The class probe is our own mutation, not new content to refresh again.
    this._mutations?.takeRecords();
    this._contentMutations?.takeRecords();
    const locked = (this._isDocument ? [root, this._document.body] : [root])
      .some(element => ["hidden", "clip"].includes(window.getComputedStyle(element).overflowY));
    this._maximum = Math.max(0, root.scrollHeight - root.clientHeight);
    const visible = this._position();
    this._bar.hidden = !enabled || locked || !visible || this._maximum <= 0;
    if (this._bar.hidden) {
      if (this._document.activeElement === this._bar) this._bar.blur();
      delete this._bar.dataset.scrollbarVisible;
      delete this._bar.dataset.scrollbarInteractive;
      return this;
    }
    const minimum = this._bar.clientWidth;
    const height = this._bar.clientHeight;
    const thumbHeight = Math.min(height, Math.max(minimum, height * root.clientHeight / root.scrollHeight));
    this._travel = Math.max(0, height - thumbHeight);
    const position = Math.min(this._maximum, Math.max(0, root.scrollTop));
    this._thumb.style.height = `${thumbHeight}px`;
    this._thumb.style.transform = `translateY(${this._travel * position / this._maximum}px)`;
    this._bar.setAttribute("aria-valuemax", String(Math.round(this._maximum)));
    this._bar.setAttribute("aria-valuenow", String(Math.round(position)));
    return this;
  }

  _position() {
    if (this._isDocument) return true;
    const root = this._root;
    const bounds = root.getBoundingClientRect();
    const top = Math.max(0, bounds.top + root.clientTop);
    const bottom = Math.min(this._window.innerHeight, bounds.top + root.clientTop + root.clientHeight);
    const width = parseFloat(this._window.getComputedStyle(this._bar).inlineSize);
    const rtl = this._window.getComputedStyle(root).direction === "rtl";
    const left = bounds.left + root.clientLeft + (rtl ? 0 : root.clientWidth - width);
    Object.assign(this._bar.style, {
      insetInlineEnd: "auto", bottom: "auto", top: `${top}px`, height: `${Math.max(0, bottom - top)}px`,
      left: `${Math.max(0, Math.min(this._window.innerWidth - width, left))}px`,
      direction: rtl ? "rtl" : "ltr",
    });
    return bounds.width > 0 && bottom > top && left < this._window.innerWidth && left + width > 0;
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    for (const [target, type, handler, options] of this._listeners) {
      target.removeEventListener(type, handler, options);
    }
    this._listeners = [];
    this._resize?.disconnect();
    this._mutations?.disconnect();
    this._contentMutations?.disconnect();
    this._window.cancelAnimationFrame(this._frame);
    this._window.clearTimeout(this._timer);
    if (this._drag && this._bar.hasPointerCapture(this._drag.id)) this._bar.releasePointerCapture(this._drag.id);
    this._drag = null;
    this._bar.remove();
    this._root.classList.toggle("scrollbar-overlay-native", this._originalNativeClass);
    if (this._generatedId && this._root.id === this._generatedId) {
      if (this._originalId === null) this._root.removeAttribute("id");
      else this._root.setAttribute("id", this._originalId);
    }
    if (instances.get(this._root) === this) instances.delete(this._root);
  }

  _listen(target, type, handler, options) {
    target.addEventListener(type, handler, options);
    this._listeners.push([target, type, handler, options]);
  }

  _queue() {
    if (this._disposed || this._frame) return;
    this._frame = this._window.requestAnimationFrame(() => {
      this._frame = 0;
      this.refresh();
    });
  }

  _reveal() {
    if (this._disposed || this._bar.hidden) return;
    this._bar.dataset.scrollbarVisible = "true";
    this._hideLater();
  }

  _hideLater() {
    this._window.clearTimeout(this._timer);
    this._timer = 0;
    if (this._disposed) return;
    if (!this._bar.hasAttribute("data-scrollbar-visible")) return;
    this._timer = this._window.setTimeout(() => {
      this._timer = 0;
      if (this._disposed || this._nearEdge || this._drag || this._bar.matches(":focus-visible")) return;
      delete this._bar.dataset.scrollbarVisible;
    }, this._hideDelay);
  }

  _onPointerMove(event) {
    if (this._disposed) return;
    if (this._drag?.id === event.pointerId) {
      if (this._travel) this._scroll(this._drag.top + (event.clientY - this._drag.y) * this._maximum / this._travel);
      return;
    }
    if (event.pointerType !== "mouse") {
      this._nearEdge = false;
      if (!this._drag) delete this._bar.dataset.scrollbarInteractive;
      return;
    }
    const bounds = this._bar.getBoundingClientRect();
    const nearEdge = !this._bar.hidden && event.clientX >= bounds.left && event.clientX <= bounds.right
      && event.clientY >= bounds.top && event.clientY <= bounds.bottom;
    if (nearEdge) {
      this._nearEdge = true;
      this._bar.dataset.scrollbarInteractive = "true";
      this._reveal();
    } else if (this._nearEdge) {
      this._nearEdge = false;
      if (!this._drag) delete this._bar.dataset.scrollbarInteractive;
      this._hideLater();
    }
  }

  _onPointerDown(event) {
    if (event.button !== 0 || this._bar.hidden || event.pointerType === "touch") return;
    event.preventDefault();
    // Like a native scrollbar, pointer scrolling preserves the page's focus.
    // Keyboard users reach the scrollbar through its normal Tab stop.
    this._reveal();
    const thumb = this._thumb.getBoundingClientRect();
    if (event.clientY >= thumb.top && event.clientY <= thumb.bottom) {
      this._drag = { id: event.pointerId, y: event.clientY, top: this._root.scrollTop };
      this._bar.setPointerCapture(event.pointerId);
    } else {
      const direction = event.clientY < this._thumb.getBoundingClientRect().top ? -1 : 1;
      this._scroll(this._root.scrollTop + direction * this._root.clientHeight);
    }
  }

  _finishDrag() {
    if (!this._drag || this._disposed) return;
    const id = this._drag.id;
    this._drag = null;
    if (!this._nearEdge) delete this._bar.dataset.scrollbarInteractive;
    if (this._bar.hasPointerCapture(id)) this._bar.releasePointerCapture(id);
    this._hideLater();
  }

  _onKeyDown(event) {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    this.refresh();
    const step = parseFloat(this._window.getComputedStyle(this._root).lineHeight) || 16;
    const page = this._root.clientHeight;
    const targets = {
      ArrowUp: this._root.scrollTop - step, ArrowDown: this._root.scrollTop + step,
      PageUp: this._root.scrollTop - page, PageDown: this._root.scrollTop + page,
      Home: 0, End: this._maximum,
      " ": this._root.scrollTop + (event.shiftKey ? -page : page),
    };
    if (!Object.hasOwn(targets, event.key)) return;
    event.preventDefault();
    this._scroll(targets[event.key]);
    this._reveal();
  }

  _scroll(top) {
    const target = this._isDocument ? this._window : this._root;
    target.scrollTo({ top: Math.min(this._maximum, Math.max(0, top)), behavior: "instant" });
    this._queue();
  }
}

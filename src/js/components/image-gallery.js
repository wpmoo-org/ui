// Image Gallery lightbox behaviour. Bootstrap opens the Dialog from each
// thumbnail link (Modal data API) and returns focus to it on close; the
// Carousel already slides, wraps and swipes. Bootstrap has no lightbox, so
// this module adds what the Carousel lacks: it shows the clicked photo,
// keeps the counter, caption and credit current, wires the previous, next,
// play, pause and full-screen buttons, lets the arrow keys work anywhere in
// the dialog and loads only the current photo and its neighbours. Lightbox
// images keep their address in data-gallery-src until then, so nothing is
// requested before the visitor opens a photo.
const instances = new WeakMap();
const SLIDESHOW_INTERVAL = 5000;

export default class ImageGallery {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element) {
    return ImageGallery.getInstance(element) || new ImageGallery(element);
  }

  constructor(element) {
    if (element?.nodeType !== 1 || !element.matches("[data-image-gallery]")) {
      throw new TypeError("ImageGallery requires a [data-image-gallery] root element.");
    }
    const existing = instances.get(element);
    if (existing) return existing;
    this._element = element;
    this._window = element.ownerDocument.defaultView;
    this._dialog = element.querySelector(".modal");
    this._carousel = this._dialog?.querySelector(".carousel");
    if (!this._dialog || !this._carousel) {
      throw new TypeError("ImageGallery requires a lightbox Dialog with a Carousel.");
    }
    this._slides = Array.from(this._carousel.querySelectorAll(".carousel-item"));
    this._counter = this._dialog.querySelector("[data-gallery-counter]");
    this._caption = this._dialog.querySelector("[data-gallery-caption]");
    this._credit = this._dialog.querySelector("[data-gallery-credit]");
    this._stage = this._dialog.querySelector("[data-gallery-stage]");
    this._frame = this._dialog.querySelector(".modal-dialog");
    const controls = (suffix) => (this._dialog.id
      ? element.ownerDocument.getElementById(`${this._dialog.id}-${suffix}`)
      : null);
    this._enterButton = controls("fullscreen");
    this._exitButton = controls("windowed");
    this._playButton = controls("play");
    this._pauseButton = controls("pause");
    this._listeners = [];
    this._listen(this._dialog, "show.bs.modal", (event) => this._onShow(event));
    this._listen(this._window, "resize", () => this._layoutStage());
    this._listen(this._dialog, "shown.bs.modal", () => this._carouselInstance());
    this._listen(this._carousel, "slide.bs.carousel", (event) => this.show(event.to, false));
    this._listen(this._dialog, "keydown", (event) => this._onKeydown(event));
    this._listen(this._dialog, "hidden.bs.modal", () => {
      this.play(false);
      this.fullscreen(false);
    });
    const actions = [
      [controls("previous"), () => this._step(false)],
      [controls("next"), () => this._step(true)],
      [this._playButton, () => this.play(true, true)],
      [this._pauseButton, () => this.play(false, true)],
      [this._enterButton, () => this.fullscreen(true, true)],
      [this._exitButton, () => this.fullscreen(false, true)],
    ];
    for (const [button, action] of actions) {
      if (button) this._listen(button, "click", action);
    }
    instances.set(element, this);
  }

  get index() {
    const active = this._slides.findIndex((slide) => slide.classList.contains("active"));
    return Math.max(active, 0);
  }

  /** Marks photo `index` current, loads it and its neighbours. */
  show(index, activate = true) {
    const count = this._slides.length;
    if (!count) return this;
    const current = ((Number(index) % count) + count) % count;
    if (activate) {
      this._slides.forEach((slide, position) => {
        slide.classList.toggle("active", position === current);
      });
    }
    for (const offset of [0, 1, -1]) {
      this._load(this._slides[(current + offset + count) % count]);
    }
    const slide = this._slides[current];
    if (this._caption) {
      this._caption.textContent = slide.getAttribute("data-gallery-slide-title")
        || slide.querySelector("img")?.alt || "";
    }
    if (this._credit) {
      const credit = slide.getAttribute("data-gallery-slide-credit") || "";
      this._credit.textContent = credit;
      this._credit.classList.toggle("d-none", !credit);
    }
    if (this._counter) {
      const template = this._counter.getAttribute("data-gallery-counter") || "{current} / {total}";
      this._counter.textContent = template
        .replaceAll("{current}", String(current + 1))
        .replaceAll("{total}", String(count));
    }
    return this;
  }

  /** Starts or stops the slideshow. */
  play(on = true, moveFocus = false) {
    const value = Boolean(on);
    const carousel = value ? this._carouselInstance() : this._carouselInstance(false);
    if (value) carousel?.cycle();
    else carousel?.pause();
    this._playing = value && Boolean(carousel);
    this._playButton?.classList.toggle("d-none", this._playing);
    this._pauseButton?.classList.toggle("d-none", !this._playing);
    // A running slideshow would announce every photo; stay quiet meanwhile.
    this._counter?.setAttribute("aria-live", this._playing ? "off" : "polite");
    if (moveFocus) (this._playing ? this._pauseButton : this._playButton)?.focus();
    return this;
  }

  get isFullscreen() {
    return Boolean(this._frame?.classList.contains("modal-fullscreen"));
  }

  /** Switches between the large dialog and full screen. */
  fullscreen(on = true, moveFocus = false) {
    if (!this._frame) return this;
    const value = Boolean(on);
    this._frame.classList.toggle("modal-fullscreen", value);
    this._layoutStage();
    if (moveFocus) (value ? this._exitButton : this._enterButton)?.focus();
    return this;
  }

  dispose() {
    for (const [target, type, listener] of this._listeners) {
      target.removeEventListener(type, listener);
    }
    this._listeners = [];
    instances.delete(this._element);
  }

  _listen(target, type, listener) {
    target.addEventListener(type, listener);
    this._listeners.push([target, type, listener]);
  }

  // The dialog fills the screen after the full-screen button, or below the
  // breakpoint of Bootstrap's .modal-fullscreen-{breakpoint}-down.
  _fillsScreen() {
    if (this.isFullscreen) return true;
    const breakpoint = this._frame?.className.match(/\bmodal-fullscreen-(\w+)-down\b/)?.[1];
    if (!breakpoint) return false;
    const width = Number.parseFloat(this._window.getComputedStyle(this._element.ownerDocument.documentElement)
      .getPropertyValue(`--bs-breakpoint-${breakpoint}`));
    return Number.isFinite(width) && this._window.matchMedia(`(max-width: ${width - 0.02}px)`).matches;
  }

  _layoutStage() {
    // gallery-stage gives the stage its one height inside the dialog; a
    // dialog that fills the screen lets the stage take the remaining height.
    const fill = this._fillsScreen();
    this._stage?.classList.toggle("gallery-stage", !fill);
    // One button enters and the other leaves full screen; a dialog that
    // already fills a small screen needs neither.
    this._enterButton?.classList.toggle("d-none", fill);
    this._exitButton?.classList.toggle("d-none", !this.isFullscreen);
  }

  _onShow(event) {
    this._layoutStage();
    const trigger = event.relatedTarget;
    const value = trigger?.closest?.("[data-gallery-index]")?.getAttribute("data-gallery-index");
    this.show(value === null || value === undefined ? 0 : Number.parseInt(value, 10) || 0);
  }

  _onKeydown(event) {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    // The Carousel handles keys pressed while the focus is inside it.
    if (this._carousel.contains(event.target)) return;
    event.preventDefault();
    // Match Bootstrap's Carousel: in a right-to-left document the left
    // arrow moves forward.
    const rtl = this._element.ownerDocument.documentElement.dir === "rtl";
    this._step((event.key === "ArrowRight") !== rtl);
  }

  _step(forward) {
    const carousel = this._carouselInstance();
    if (!carousel) return;
    if (forward) carousel.next();
    else carousel.prev();
  }

  _carouselInstance(create = true) {
    const Carousel = this._window.bootstrap?.Carousel;
    if (!Carousel) return null;
    if (!create) return Carousel.getInstance(this._carousel);
    // The slideshow runs only after Play: ride stays off, and hovering does
    // not pause or restart it.
    return Carousel.getOrCreateInstance(this._carousel, {
      interval: SLIDESHOW_INTERVAL,
      pause: false,
      ride: false,
      keyboard: true,
      touch: true,
      wrap: true,
    });
  }

  _load(slide) {
    const image = slide?.querySelector("img[data-gallery-src]");
    if (!image || image.hasAttribute("src")) return;
    const srcset = image.getAttribute("data-gallery-srcset");
    if (srcset) image.setAttribute("srcset", srcset);
    image.setAttribute("src", image.getAttribute("data-gallery-src"));
  }
}

/** Binds every gallery under `root`; returns a function that unbinds them. */
export function initImageGalleries(root = document) {
  const galleries = Array.from(root.querySelectorAll("[data-image-gallery]"))
    .map((element) => ImageGallery.getOrCreateInstance(element));
  return () => galleries.forEach((gallery) => gallery.dispose());
}

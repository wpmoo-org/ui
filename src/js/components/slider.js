const instances = new WeakMap();

function asNumber(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function inputMinimum(input) {
  return asNumber(input.min, 0);
}

function inputMaximum(input) {
  return asNumber(input.max, 100);
}

function inputStep(input) {
  if (!input.step || input.step === "any") {
    return 1;
  }
  const step = Number(input.step);
  return Number.isFinite(step) && step > 0 ? step : 1;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function decimalPlaces(value) {
  const text = String(value);
  if (!text.includes(".")) {
    return 0;
  }
  return text.split(".").at(-1).length;
}

function snapToStep(value, input) {
  const min = inputMinimum(input);
  const max = inputMaximum(input);
  if (input.step === "any") {
    return Number(clamp(value, min, max).toFixed(4));
  }
  const step = inputStep(input);
  const snapped = min + Math.round((value - min) / step) * step;
  const precision = Math.max(decimalPlaces(step), decimalPlaces(min));
  return clamp(Number(snapped.toFixed(precision)), min, max);
}

function valuePercent(input) {
  const min = inputMinimum(input);
  const max = inputMaximum(input);
  if (max <= min) {
    return 0;
  }
  return ((asNumber(input.value, min) - min) / (max - min)) * 100;
}

function displayValue(input) {
  return input.value || String(inputMinimum(input));
}

export default class MooSlider {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return MooSlider.getInstance(element) || new MooSlider(element, config);
  }

  constructor(element, config = {}) {
    if (element?.nodeType !== 1 || !element.matches("[data-slider]")) {
      throw new TypeError("MooSlider requires a [data-slider] root element.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._config = { ...config };
    this._listeners = [];
    this._dragListeners = [];
    this._draggingInput = null;
    this._disposed = false;
    this._inputs = Array.from(
      element.querySelectorAll(':scope input[type="range"][data-slider-input]')
    );
    this._track = element.querySelector("[data-slider-track]");
    this._output = element.querySelector("[data-slider-output]");

    if (this._inputs.length < 1 || this._inputs.length > 2) {
      throw new TypeError("MooSlider requires one or two native range inputs.");
    }
    if (!this._track) {
      throw new TypeError("MooSlider requires a [data-slider-track] element.");
    }

    instances.set(element, this);
    this._bindEvents();
    this._sync();
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    this._clearDragListeners();
    this._clearPointerFocus();
    this._listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._listeners = [];
    if (instances.get(this._element) === this) {
      instances.delete(this._element);
    }
  }

  _listen(target, type, handler, options) {
    if (!target) {
      return;
    }
    target.addEventListener(type, handler, options);
    this._listeners.push({ target, type, handler, options });
  }

  _listenDuringDrag(target, type, handler, options) {
    if (!target) {
      return;
    }
    target.addEventListener(type, handler, options);
    this._dragListeners.push({ target, type, handler, options });
  }

  _clearDragListeners() {
    this._dragListeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._dragListeners = [];
    this._draggingInput = null;
    this._element.removeAttribute("data-slider-dragging");
  }

  _bindEvents() {
    this._inputs.forEach((input) => {
      this._listen(input, "input", () => this._sync(input));
      this._listen(input, "change", () => {
        this._sync(input);
        this._trigger("change");
      });
      this._listen(input, "keydown", () => this._clearPointerFocus());
      this._listen(input, "focusout", () => this._clearPointerFocus());
    });
    const forms = new Set(
      this._inputs
        .map((input) => input.form || input.closest?.("form"))
        .filter(Boolean),
    );
    forms.forEach((form) => {
      this._listen(form, "reset", () => {
        this._window.setTimeout(() => this._sync(), 0);
      });
    });
    this._listen(this._track, "pointerdown", (event) => this._handleTrackPointer(event));
  }

  _trigger(name) {
    this._element.dispatchEvent(
      new this._window.CustomEvent(`${name}.moo.slider`, {
        bubbles: true,
      })
    );
  }

  _isRange() {
    return this._inputs.length === 2;
  }

  _sync(changedInput = null) {
    if (this._isRange()) {
      const [startInput, endInput] = this._inputs;
      const start = asNumber(startInput.value, inputMinimum(startInput));
      const end = asNumber(endInput.value, inputMaximum(endInput));
      if (start > end) {
        if (changedInput === endInput) {
          endInput.value = startInput.value;
        } else {
          startInput.value = endInput.value;
        }
      }
      this._writeFill(valuePercent(startInput), valuePercent(endInput));
      this._writeOutput(`${displayValue(startInput)} - ${displayValue(endInput)}`);
      this._syncAria(startInput);
      this._syncAria(endInput);
      return;
    }

    const input = this._inputs[0];
    this._writeFill(0, valuePercent(input));
    this._writeOutput(displayValue(input));
    this._syncAria(input);
  }

  _syncAria(input) {
    input.setAttribute("aria-valuemin", String(inputMinimum(input)));
    input.setAttribute("aria-valuemax", String(inputMaximum(input)));
    input.setAttribute("aria-valuenow", displayValue(input));
  }

  _writeFill(start, end) {
    const clampedStart = clamp(start, 0, 100);
    const clampedEnd = clamp(end, 0, 100);
    this._element.style.setProperty("--moo-slider-start", `${Math.min(clampedStart, clampedEnd)}%`);
    this._element.style.setProperty("--moo-slider-end", `${Math.max(clampedStart, clampedEnd)}%`);
  }

  _writeOutput(value) {
    if (this._output) {
      this._output.textContent = value;
    }
  }

  _handleTrackPointer(event) {
    if (event.button !== undefined && event.button !== 0) {
      return;
    }
    const enabledInputs = this._inputs.filter((input) => !input.disabled);
    if (!enabledInputs.length) {
      return;
    }
    event.preventDefault?.();
    const percent = this._pointerPercent(event);
    const target = this._nearestInput(percent * 100, enabledInputs);
    this._setPointerFocus();
    this._startDrag(target, event);
    this._setInputFromPointer(target, event);
  }

  _setPointerFocus() {
    this._element.setAttribute("data-slider-pointer-focus", "true");
  }

  _clearPointerFocus() {
    this._element.removeAttribute("data-slider-pointer-focus");
  }

  _startDrag(input, event) {
    this._clearDragListeners();
    this._draggingInput = input;
    this._element.setAttribute("data-slider-dragging", "true");
    this._track.setPointerCapture?.(event.pointerId);

    const pointerId = event.pointerId;
    const samePointer = (nextEvent) => pointerId === undefined || nextEvent.pointerId === pointerId;
    const onMove = (moveEvent) => {
      if (!samePointer(moveEvent) || this._draggingInput !== input) {
        return;
      }
      moveEvent.preventDefault?.();
      this._setInputFromPointer(input, moveEvent);
    };
    const onEnd = (endEvent) => {
      if (!samePointer(endEvent) || this._draggingInput !== input) {
        return;
      }
      endEvent.preventDefault?.();
      this._setInputFromPointer(input, endEvent, false);
      input.dispatchEvent(new this._window.Event("change", { bubbles: true }));
      this._track.releasePointerCapture?.(pointerId);
      this._clearDragListeners();
    };

    this._listenDuringDrag(this._document, "pointermove", onMove);
    this._listenDuringDrag(this._document, "pointerup", onEnd);
    this._listenDuringDrag(this._document, "pointercancel", onEnd);
  }

  _setInputFromPointer(input, event, emitInput = true) {
    const percent = this._pointerPercent(event);
    const min = inputMinimum(input);
    const max = inputMaximum(input);
    input.value = String(snapToStep(min + percent * (max - min), input));
    input.focus({ preventScroll: true });
    this._sync(input);
    if (emitInput) {
      input.dispatchEvent(new this._window.Event("input", { bubbles: true }));
    }
  }

  _pointerPercent(event) {
    const rect = this._track.getBoundingClientRect();
    const orientation = this._element.dataset.sliderOrientation || "horizontal";
    if (orientation === "vertical") {
      return clamp((rect.bottom - event.clientY) / (rect.height || 1), 0, 1);
    }
    return this._horizontalPointerPercent(event, rect);
  }

  _horizontalPointerPercent(event, rect) {
    const direction = this._window.getComputedStyle?.(this._element).direction;
    const offset = direction === "rtl" ? rect.right - event.clientX : event.clientX - rect.left;
    return clamp(offset / (rect.width || 1), 0, 1);
  }

  _nearestInput(percent, inputs) {
    if (inputs.length === 1) {
      return inputs[0];
    }
    const [startInput, endInput] = inputs;
    const startPercent = valuePercent(startInput);
    const endPercent = valuePercent(endInput);
    const startDistance = Math.abs(startPercent - percent);
    const endDistance = Math.abs(endPercent - percent);
    if (startDistance === endDistance) {
      return percent >= startPercent ? endInput : startInput;
    }
    return endDistance < startDistance ? endInput : startInput;
  }
}

const instances = new WeakMap();
const normalize = (value) => value.trim().toLowerCase();

export default class Combobox {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return Combobox.getInstance(element) || new Combobox(element, config);
  }

  constructor(element, config = {}) {
    if (element?.nodeType !== 1 || !element.matches(".combobox")) {
      throw new TypeError("Combobox requires a .combobox root element.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._config = { noResultsText: "No results found.", ...config };
    this._input = element.querySelector(".combobox-input");
    this._menu = element.querySelector(".combobox-menu");
    this._options = Array.from(element.querySelectorAll(".combobox-option"));
    if (!this._input || !this._menu || this._options.length === 0) {
      throw new TypeError("Combobox requires an input, menu, and at least one option.");
    }

    this._isMultiple = element.dataset.comboboxMultiple === "true";
    this._hidden = this._isMultiple ? null : element.querySelector('input[type="hidden"]');
    this._chipValue = element.querySelector(".combobox-value");
    this._valueStore = element.querySelector("[data-combobox-value-store]");
    this._chipIconTemplate = element.querySelector("[data-combobox-chip-icon]");
    this._clearTrigger = element.querySelector("[data-combobox-clear]");
    this._indicator = element.querySelector(".combobox-indicator");
    this._groups = Array.from(element.querySelectorAll("[data-combobox-group]"));
    this._separators = Array.from(element.querySelectorAll("[data-combobox-separator]"));
    this._listeners = [];
    this._generated = [];
    this._startsOpen = this._menu.classList.contains("show");

    this._empty = this._menu.querySelector("[data-combobox-empty]");
    if (!this._empty) {
      this._empty = this._document.createElement("li");
      this._empty.className = "combobox-empty";
      this._empty.hidden = true;
      this._empty.dataset.comboboxEmpty = "true";
      this._empty.textContent = this._config.noResultsText;
      this._menu.appendChild(this._empty);
      this._generated.push(this._empty);
    }

    this._liveRegion = element.querySelector("[data-combobox-live]");
    if (!this._liveRegion) {
      this._liveRegion = this._document.createElement("span");
      this._liveRegion.className = "visually-hidden";
      this._liveRegion.setAttribute("aria-live", "polite");
      this._liveRegion.dataset.comboboxLive = "true";
      element.appendChild(this._liveRegion);
      this._generated.push(this._liveRegion);
    }

    instances.set(element, this);
    this._bindEvents();
    this._toggleClear(
      this._input.dataset.comboboxSelected === "true" ||
        element.dataset.comboboxSelected === "true"
    );
    this._syncMultipleValue();
    this._filterOptions({ open: this._startsOpen, activate: this._startsOpen });
    if (!this._startsOpen) {
      this._closeMenu(false);
    }
  }

  dispose() {
    this._listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._listeners = [];
    this._closeMenu(false);
    this._generated.forEach((element) => element.remove());
    this._generated = [];
    this._chipValue?.querySelectorAll("[data-combobox-generated]").forEach((item) => item.remove());
    this._valueStore?.querySelectorAll("[data-combobox-generated]").forEach((item) => item.remove());
    instances.delete(this._element);
  }

  _listen(target, type, handler, options) {
    target?.addEventListener(type, handler, options);
    if (target) {
      this._listeners.push({ target, type, handler, options });
    }
  }

  _trigger(name, detail = {}) {
    return this._element.dispatchEvent(
      new this._window.CustomEvent(`${name}.moo.combobox`, {
        bubbles: true,
        cancelable: name === "show" || name === "hide",
        detail,
      })
    );
  }

  _optionGroupIsHidden(option) {
    return option.closest("[data-combobox-group]")?.hidden || false;
  }

  _visibleOptions() {
    return this._options.filter(
      (option) => !option.hidden && !option.disabled && !this._optionGroupIsHidden(option)
    );
  }

  _syncGroupVisibility() {
    if (this._groups.length === 0) {
      return;
    }
    let visibleGroupCount = 0;
    this._groups.forEach((group) => {
      const visible = Array.from(group.querySelectorAll(".combobox-option")).some(
        (option) => !option.hidden
      );
      group.hidden = !visible;
      visibleGroupCount += visible ? 1 : 0;
    });
    this._separators.forEach((separator) => {
      separator.hidden = visibleGroupCount < 2;
    });
  }

  _openMenu(emit = true) {
    if (this._menu.classList.contains("show")) {
      this._input.setAttribute("aria-expanded", "true");
      return;
    }
    if (emit && !this._trigger("show")) {
      return;
    }
    this._menu.classList.add("show");
    this._input.setAttribute("aria-expanded", "true");
    if (emit) {
      this._trigger("shown");
    }
  }

  _closeMenu(emit = true) {
    const wasOpen = this._menu.classList.contains("show");
    if (wasOpen && emit && !this._trigger("hide")) {
      return;
    }
    this._menu.classList.remove("show");
    this._input.setAttribute("aria-expanded", "false");
    this._input.removeAttribute("aria-activedescendant");
    this._options.forEach((option) => option.removeAttribute("aria-current"));
    if (wasOpen && emit) {
      this._trigger("hidden");
    }
  }

  _optionLabel(option) {
    return option?.querySelector(".combobox-option__label")?.textContent?.trim() || "";
  }

  _selectedOptions() {
    return this._options.filter((option) => option.getAttribute("aria-selected") === "true");
  }

  _toggleClear(selected) {
    const value = selected ? "true" : "false";
    this._element.dataset.comboboxSelected = value;
    this._input.dataset.comboboxSelected = value;
    if (this._clearTrigger) {
      this._clearTrigger.hidden = !selected;
      if (this._indicator) {
        this._indicator.hidden = selected;
      }
    }
  }

  _createChip(option) {
    const value = option.dataset.value || "";
    const label = this._optionLabel(option);
    const chip = this._document.createElement("span");
    chip.className = "badge text-bg-secondary combobox-chip";
    chip.dataset.value = value;
    chip.dataset.comboboxGenerated = "true";
    const labelElement = this._document.createElement("span");
    labelElement.className = "combobox-chip__label";
    labelElement.textContent = label;
    chip.appendChild(labelElement);
    const remove = this._document.createElement("button");
    remove.className = "combobox-chip__remove";
    remove.type = "button";
    remove.dataset.value = value;
    remove.dataset.comboboxChipRemove = "true";
    remove.setAttribute("aria-label", `Remove ${label}`);
    remove.append(this._chipIconTemplate?.content.cloneNode(true) || "x");
    chip.appendChild(remove);
    return chip;
  }

  _syncMultipleValue() {
    if (!this._isMultiple) {
      return;
    }
    const selected = this._selectedOptions();
    if (this._chipValue) {
      this._chipValue.replaceChildren(...selected.map((option) => this._createChip(option)));
    }
    if (this._valueStore) {
      this._valueStore.replaceChildren();
      const name = this._valueStore.dataset.comboboxName || "";
      selected.forEach((option) => {
        const field = this._document.createElement("input");
        field.type = "hidden";
        field.name = name;
        field.value = option.dataset.value || "";
        field.dataset.comboboxGenerated = "true";
        this._valueStore.appendChild(field);
      });
    }
    this._toggleClear(selected.length > 0);
  }

  _emitChange() {
    const selected = this._selectedOptions();
    this._trigger("change", {
      values: selected.map((option) => option.dataset.value || ""),
    });
  }

  _removeChip(value) {
    const option = this._options.find((candidate) => candidate.dataset.value === value);
    if (!option) {
      return;
    }
    option.setAttribute("aria-selected", "false");
    this._syncMultipleValue();
    this._emitChange();
  }

  _clearSelection(emit = true) {
    if (this._hidden) {
      this._hidden.value = "";
    }
    this._options.forEach((option) => option.setAttribute("aria-selected", "false"));
    if (this._isMultiple) {
      this._syncMultipleValue();
    } else {
      this._toggleClear(false);
    }
    if (emit) {
      this._emitChange();
    }
  }

  _clearStaleSelection() {
    if (this._isMultiple) {
      this._input.value = "";
      this._options.forEach((option) => {
        option.hidden = false;
      });
      this._syncGroupVisibility();
      this._empty.hidden = true;
      return;
    }
    const selected = this._selectedOptions()[0] || null;
    const label = this._optionLabel(selected);
    if (!this._input.value || (label && normalize(this._input.value) === normalize(label))) {
      return;
    }
    this._clearSelection();
    this._input.value = "";
  }

  _setActiveOption(option) {
    this._options.forEach((candidate) => candidate.toggleAttribute("aria-current", candidate === option));
    if (!option) {
      this._input.removeAttribute("aria-activedescendant");
      return;
    }
    this._input.setAttribute("aria-activedescendant", option.id);
    const optionRect = option.getBoundingClientRect();
    const menuRect = this._menu.getBoundingClientRect();
    if (optionRect.top < menuRect.top) {
      this._menu.scrollTop -= menuRect.top - optionRect.top;
    } else if (optionRect.bottom > menuRect.bottom) {
      this._menu.scrollTop += optionRect.bottom - menuRect.bottom;
    }
  }

  _chooseOption(option) {
    if (!option || option.disabled) {
      return;
    }
    if (this._isMultiple) {
      option.setAttribute(
        "aria-selected",
        option.getAttribute("aria-selected") === "true" ? "false" : "true"
      );
      this._input.value = "";
      this._syncMultipleValue();
      this._filterOptions();
      this._setActiveOption(option);
      this._emitChange();
      return;
    }
    this._options.forEach((candidate) => {
      candidate.setAttribute("aria-selected", candidate === option ? "true" : "false");
    });
    this._input.value = this._optionLabel(option);
    if (this._hidden) {
      this._hidden.value = option.dataset.value || "";
    }
    this._toggleClear(true);
    this._setActiveOption(option);
    this._emitChange();
  }

  _filterOptions({ open = true, activate = true } = {}) {
    if (open) {
      this._openMenu();
    }
    const needle = normalize(this._input.value);
    let count = 0;
    this._options.forEach((option) => {
      const matches = !needle || normalize(option.textContent).includes(needle);
      option.hidden = !matches;
      count += matches ? 1 : 0;
    });
    this._syncGroupVisibility();
    this._empty.hidden = count !== 0;
    this._liveRegion.textContent = count === 0 ? "No results" : `${count} result${count === 1 ? "" : "s"}`;
    if (activate) {
      this._setActiveOption(this._visibleOptions()[0] || null);
    }
  }

  _bindEvents() {
    this._listen(this._input, "focus", () => {
      this._openMenu();
      if (!this._isMultiple && this._input.dataset.comboboxSelected === "true") {
        this._input.select();
      }
      this._setActiveOption(this._visibleOptions()[0] || null);
    });
    this._listen(this._input, "input", () => {
      if (!this._isMultiple) {
        this._clearSelection();
      }
      this._filterOptions();
    });
    this._listen(this._input, "blur", () => this._clearStaleSelection());
    this._listen(this._input, "click", () => this._openMenu());
    this._listen(this._input, "keydown", (event) => this._handleKeydown(event));
    this._options.forEach((option) => {
      this._listen(option, "click", () => {
        this._chooseOption(option);
        if (this._isMultiple) {
          this._input.focus();
        } else {
          this._closeMenu();
        }
      });
    });
    this._listen(this._clearTrigger, "click", (event) => {
      event.preventDefault();
      this._clearSelection();
      this._input.value = "";
      this._input.focus();
      this._filterOptions();
    });
    this._listen(this._element, "click", (event) => this._handleRootClick(event));
    this._listen(this._document, "click", (event) => {
      if (event.target instanceof this._window.Node && !this._element.contains(event.target)) {
        this._closeMenu();
      }
    });
  }

  _handleRootClick(event) {
    const target = event.target;
    const trigger = target instanceof this._window.Element
      ? target.closest("[data-combobox-chip-remove]")
      : null;
    if (trigger) {
      event.preventDefault();
      this._removeChip(trigger.dataset.value || "");
      this._input.focus();
    } else if (
      this._isMultiple &&
      target instanceof this._window.Element &&
      target.closest(".combobox-chips")
    ) {
      this._input.focus();
    }
  }

  _handleKeydown(event) {
    const available = this._visibleOptions();
    const current = available.findIndex(
      (option) => option.id === this._input.getAttribute("aria-activedescendant")
    );
    if (this._isMultiple && event.key === "Backspace" && this._input.value === "") {
      const selected = this._selectedOptions();
      const last = selected[selected.length - 1];
      if (last) {
        event.preventDefault();
        this._removeChip(last.dataset.value || "");
      }
    } else if ((event.key === "ArrowDown" || event.key === "ArrowUp") && available.length) {
      event.preventDefault();
      this._openMenu();
      const offset = event.key === "ArrowDown" ? 1 : -1;
      const next = current === -1 ? 0 : (current + offset + available.length) % available.length;
      this._setActiveOption(available[next]);
    } else if (event.key === "Enter") {
      const option = available[current];
      if (option) {
        event.preventDefault();
        this._chooseOption(option);
        if (!this._isMultiple) {
          this._closeMenu();
        }
      }
    } else if (event.key === "Escape") {
      this._closeMenu();
      this._input.blur();
    } else if (event.key === "Tab") {
      this._closeMenu();
    }
  }
}

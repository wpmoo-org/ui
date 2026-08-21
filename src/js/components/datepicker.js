// MooDatepicker - a reference-style trigger/popover/calendar wrapper. The public
// UI, date math, keyboard handling, locale, and selection behavior are all
// owned by Moo UI and require no third-party runtime.

const datepickerInstances = new WeakMap();
const calendarInstances = new WeakMap();
const rangePickerInstances = new WeakMap();

const DEFAULT_LOCALE = "en";
const DAY_MS = 24 * 60 * 60 * 1000;
const WEEKDAY_BASE_SUNDAY = new Date(2026, 7, 16);
const POPOVER_VIEWPORT_PADDING = 8;

function isElement(element, selector) {
  return element?.nodeType === 1 && Boolean(element.matches?.(selector));
}

function addListener(listeners, target, type, handler, options) {
  if (!target) return;
  target.addEventListener(type, handler, options);
  listeners.push({ target, type, handler, options });
}

function removeListeners(listeners) {
  listeners.forEach(({ target, type, handler, options }) => {
    target.removeEventListener(type, handler, options);
  });
  listeners.length = 0;
}

function parseDate(value) {
  if (!value) return null;
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) return null;
    return new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }
  if (typeof value === "number") {
    return parseDate(new Date(value));
  }
  const text = String(value).trim();
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
  if (iso) {
    const date = new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
    if (
      date.getFullYear() === Number(iso[1]) &&
      date.getMonth() === Number(iso[2]) - 1 &&
      date.getDate() === Number(iso[3])
    ) {
      return date;
    }
    return null;
  }
  return null;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function toIso(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function compareDates(left, right) {
  if (!left || !right) return 0;
  return left.getTime() - right.getTime();
}

function sameDate(left, right) {
  return Boolean(left && right && toIso(left) === toIso(right));
}

function addDays(date, amount) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount);
}

function addMonths(date, amount) {
  return new Date(date.getFullYear(), date.getMonth() + amount, date.getDate());
}

function firstDayOfWeek(locale = DEFAULT_LOCALE) {
  try {
    if (typeof Intl !== "undefined" && typeof Intl.Locale === "function") {
      const intlLocale = new Intl.Locale(locale || DEFAULT_LOCALE);
      const weekInfo = intlLocale.weekInfo || intlLocale.getWeekInfo?.();
      if (Number.isInteger(weekInfo?.firstDay)) {
        return weekInfo.firstDay % 7;
      }
    }
  } catch {
    // Fall back to the long-standing US/Sunday calendar grid.
  }
  return 0;
}

function weekdayDates(locale = DEFAULT_LOCALE) {
  const firstDay = firstDayOfWeek(locale);
  return Array.from({ length: 7 }, (_, offset) => (
    addDays(WEEKDAY_BASE_SUNDAY, (firstDay + offset) % 7)
  ));
}

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function daysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function limitToRange(date, minDate, maxDate) {
  if (minDate && compareDates(date, minDate) < 0) return new Date(minDate);
  if (maxDate && compareDates(date, maxDate) > 0) return new Date(maxDate);
  return date;
}

function parseDateList(value) {
  if (Array.isArray(value)) {
    return value.map(parseDate).filter(Boolean).map(toIso);
  }
  if (!value) return [];
  const text = String(value).trim();
  if (!text) return [];
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) {
      return parsed.map(parseDate).filter(Boolean).map(toIso);
    }
  } catch {
    // Fall through to comma-delimited parsing.
  }
  return text.split(",").map(parseDate).filter(Boolean).map(toIso);
}

function formatDisplay(date, locale = DEFAULT_LOCALE) {
  if (!date) return "";
  return new Intl.DateTimeFormat(locale || DEFAULT_LOCALE, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function formatMonthYear(date, locale = DEFAULT_LOCALE) {
  return new Intl.DateTimeFormat(locale || DEFAULT_LOCALE, {
    month: "long",
    year: "numeric",
  }).format(date);
}

function formatReturn(date, format, locale = DEFAULT_LOCALE) {
  if (!date) return undefined;
  if (format === "yyyy-mm-dd") return toIso(date);
  if (format) return formatDisplay(date, locale);
  return new Date(date);
}

function readDataConfig(element, config = {}) {
  const dataset = element.dataset || {};
  const locale =
    config.locale ||
    dataset.datepickerLocale ||
    dataset.calendarLocale ||
    DEFAULT_LOCALE;
  const minDate = parseDate(config.minDate || dataset.calendarMinDate || dataset.datepickerMinDate);
  const maxDate = parseDate(config.maxDate || dataset.calendarMaxDate || dataset.datepickerMaxDate);
  return {
    locale,
    mode: config.mode || dataset.calendarMode || dataset.datepickerMode || "single",
    placeholder: config.placeholder || dataset.datepickerPlaceholder || "Pick a date",
    value: config.value || dataset.calendarValue || dataset.datepickerValue || "",
    startValue: config.startValue || dataset.calendarStartValue || dataset.datepickerStartValue || "",
    endValue: config.endValue || dataset.calendarEndValue || dataset.datepickerEndValue || "",
    minDate,
    maxDate,
    disabledDates: parseDateList(config.disabledDates || dataset.calendarDisabledDates || dataset.datepickerDisabledDates),
    captionLayout: config.captionLayout || dataset.calendarCaptionLayout || "",
    showPresets:
      config.showPresets ??
      (dataset.calendarShowPresets === "true" ||
        dataset.datepickerShowPresets === "true"),
  };
}

function dispatch(element, window, name, detail = {}, cancelable = false) {
  return element.dispatchEvent(
    new window.CustomEvent(name, {
      bubbles: true,
      cancelable,
      detail,
    }),
  );
}

function setHiddenValue(input, value) {
  if (!input) return;
  input.value = value || "";
}

function clamp(value, min, max) {
  if (max < min) return min;
  return Math.min(Math.max(value, min), max);
}

function cssPixelValue(element, property, fallback) {
  const value = element ? getComputedStyle(element).getPropertyValue(property).trim() : "";
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) return fallback;
  if (value.endsWith("rem")) {
    const root = element.ownerDocument.documentElement;
    const fontSize = Number.parseFloat(getComputedStyle(root).fontSize);
    return Number.isFinite(fontSize) ? parsed * fontSize : fallback;
  }
  if (value.endsWith("em")) {
    const fontSize = Number.parseFloat(getComputedStyle(element).fontSize);
    return Number.isFinite(fontSize) ? parsed * fontSize : fallback;
  }
  return Number.isFinite(parsed) ? parsed : fallback;
}

function datepickerContains(instance, target) {
  return Boolean(
    target &&
    (instance._element.contains(target) || instance._popover.contains(target))
  );
}

function syncPortaledPopoverContext(instance) {
  const theme =
    instance._element.closest("[data-bs-theme]")?.getAttribute("data-bs-theme") ||
    instance._document.documentElement.getAttribute("data-bs-theme");
  const direction = getComputedStyle(instance._trigger).direction;

  if (theme) {
    instance._popover.setAttribute("data-bs-theme", theme);
  }
  if (direction === "rtl") {
    instance._popover.setAttribute("dir", "rtl");
  }
}

function portalDatepickerPopover(instance) {
  const popover = instance._popover;
  if (instance._popoverPortal?.host?.parentElement === instance._document.body) {
    syncPortaledPopoverContext(instance);
    return;
  }
  const host = instance._document.createElement("div");
  host.className = "moo-ui";
  host.dataset.datepickerPortalHost = "";
  instance._popoverPortal = {
    parent: popover.parentNode,
    nextSibling: popover.nextSibling,
    host,
    hadTheme: popover.hasAttribute("data-bs-theme"),
    theme: popover.getAttribute("data-bs-theme"),
    hadDirection: popover.hasAttribute("dir"),
    direction: popover.getAttribute("dir"),
  };
  host.appendChild(popover);
  instance._document.body.appendChild(host);
  syncPortaledPopoverContext(instance);
}

function restoreDatepickerPopover(instance) {
  const portal = instance._popoverPortal;
  if (!portal) return;

  const popover = instance._popover;
  if (portal.parent?.isConnected) {
    if (portal.nextSibling?.parentNode === portal.parent) {
      portal.parent.insertBefore(popover, portal.nextSibling);
    } else {
      portal.parent.appendChild(popover);
    }
  } else {
    popover.remove();
  }
  portal.host?.remove();

  if (portal.hadTheme) {
    popover.setAttribute("data-bs-theme", portal.theme);
  } else {
    popover.removeAttribute("data-bs-theme");
  }
  if (portal.hadDirection) {
    popover.setAttribute("dir", portal.direction);
  } else {
    popover.removeAttribute("dir");
  }
  instance._popoverPortal = null;
}

function positionDatepickerPopover(trigger, popover, root, window) {
  const offset = cssPixelValue(root, "--moo-datepicker-popover-offset", 6);
  const direction = getComputedStyle(trigger).direction;

  popover.style.position = "fixed";
  popover.style.inset = "auto";
  popover.style.right = "auto";
  popover.style.bottom = "auto";
  popover.style.maxHeight = "";
  popover.style.overflowY = "";

  const triggerRect = trigger.getBoundingClientRect();
  const popoverRect = popover.getBoundingClientRect();
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const preferredLeft = direction === "rtl"
    ? triggerRect.right - popoverRect.width
    : triggerRect.left;
  const left = clamp(
    preferredLeft,
    POPOVER_VIEWPORT_PADDING,
    viewportWidth - popoverRect.width - POPOVER_VIEWPORT_PADDING,
  );
  const spaceBelow = triggerRect.bottom + offset <= viewportHeight
    ? viewportHeight - triggerRect.bottom - offset - POPOVER_VIEWPORT_PADDING
    : 0;
  const spaceAbove = triggerRect.top - offset - POPOVER_VIEWPORT_PADDING;
  const placeAbove = popoverRect.height > spaceBelow && spaceAbove > spaceBelow;
  const placement = placeAbove ? "top" : "bottom";
  const availableHeight = Math.max(
    0,
    placeAbove ? spaceAbove : spaceBelow,
  );
  const renderedHeight = Math.min(popoverRect.height, availableHeight);
  const top = placeAbove
    ? triggerRect.top - offset - renderedHeight
    : triggerRect.bottom + offset;

  popover.style.left = `${Math.round(left)}px`;
  popover.style.top = `${Math.round(clamp(
    top,
    POPOVER_VIEWPORT_PADDING,
    viewportHeight - renderedHeight - POPOVER_VIEWPORT_PADDING,
  ))}px`;
  if (availableHeight > 0) {
    popover.style.maxHeight = `${Math.floor(availableHeight)}px`;
    popover.style.overflowY = "auto";
  }
  popover.dataset.datepickerPlacement = placement;
}

function clearDatepickerPopoverPosition(popover) {
  popover.style.position = "";
  popover.style.inset = "";
  popover.style.right = "";
  popover.style.bottom = "";
  popover.style.left = "";
  popover.style.top = "";
  popover.style.maxHeight = "";
  popover.style.overflowY = "";
  delete popover.dataset.datepickerPlacement;
}

function startDatepickerPopoverPositioning(instance) {
  removeListeners(instance._floatingListeners);
  portalDatepickerPopover(instance);
  const update = () => {
    if (instance.isOpen()) {
      positionDatepickerPopover(
        instance._trigger,
        instance._popover,
        instance._element,
        instance._window,
      );
    }
  };
  instance._positionPopover = update;
  update();
  addListener(instance._floatingListeners, instance._window, "resize", update);
  addListener(instance._floatingListeners, instance._window, "scroll", update, true);
  addListener(instance._floatingListeners, instance._document, "scroll", update, true);
}

function stopDatepickerPopoverPositioning(instance) {
  removeListeners(instance._floatingListeners);
  instance._positionPopover = null;
  clearDatepickerPopoverPosition(instance._popover);
  restoreDatepickerPopover(instance);
}

function monthName(monthIndex, locale) {
  return new Intl.DateTimeFormat(locale || DEFAULT_LOCALE, { month: "short" })
    .format(new Date(2026, monthIndex, 1));
}

function yearOptions(minDate, maxDate, viewDate) {
  const min = minDate ? minDate.getFullYear() : viewDate.getFullYear() - 100;
  const max = maxDate ? maxDate.getFullYear() : viewDate.getFullYear() + 20;
  const years = [];
  for (let year = min; year <= max; year += 1) {
    years.push(year);
  }
  return years;
}

function createIcon(document, glyph, className = "") {
  const span = document.createElement("span");
  span.className = className;
  span.setAttribute("aria-hidden", "true");
  span.textContent = glyph;
  return span;
}

export class MooCalendar {
  static getInstance(element) {
    return element?.nodeType === 1 ? calendarInstances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return MooCalendar.getInstance(element) || new MooCalendar(element, config);
  }

  constructor(element, config = {}) {
    if (!isElement(element, "[data-calendar]")) {
      throw new TypeError("MooCalendar requires a [data-calendar] root element.");
    }
    const existing = calendarInstances.get(element);
    if (existing) return existing;

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView || window;
    this._listeners = [];
    this._disposed = false;
    this._config = readDataConfig(element, config);
    this._mode = this._config.mode === "range" ? "range" : "single";
    this._disabledDates = new Set(this._config.disabledDates);
    this._selectedDate = parseDate(this._config.value);
    this._rangeStart = parseDate(this._config.startValue);
    this._rangeEnd = parseDate(this._config.endValue);
    this._activeDate = this._nearestEnabledDate(
      this._rangeStart || this._selectedDate || new Date(),
    );
    this._viewDate = startOfMonth(this._activeDate);
    this._captionId =
      this._element.id ? `${this._element.id}-caption` : `moo-calendar-caption-${Math.random().toString(36).slice(2)}`;
    this._labelId =
      this._element.id ? `${this._element.id}-label` : `moo-calendar-label-${Math.random().toString(36).slice(2)}`;

    calendarInstances.set(element, this);
    this._bindEvents();
    this._render();
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    removeListeners(this._listeners);
    this._element.replaceChildren();
    if (calendarInstances.get(this._element) === this) {
      calendarInstances.delete(this._element);
    }
  }

  getDate(format = undefined) {
    if (this._mode === "range") {
      return this.getDates(format);
    }
    return formatReturn(this._selectedDate, format, this._config.locale);
  }

  getDates(format = undefined) {
    return [
      formatReturn(this._rangeStart, format, this._config.locale),
      formatReturn(this._rangeEnd, format, this._config.locale),
    ];
  }

  setDate(date, options = {}) {
    if (this._mode !== "single") return false;
    const parsed = parseDate(date);
    if (!parsed || this._isDisabled(parsed)) return false;
    this._selectedDate = parsed;
    this._activeDate = parsed;
    this._viewDate = startOfMonth(parsed);
    this._render();
    if (options.emit !== false) {
      this._emitChange(true);
    }
    return true;
  }

  setDates(startDate, endDate, options = {}) {
    if (this._mode !== "range") return false;
    const start = parseDate(startDate);
    const end = parseDate(endDate);
    if (start && this._isDisabled(start)) return false;
    if (end && this._isDisabled(end)) return false;
    this._rangeStart = start;
    this._rangeEnd = end;
    if (this._rangeStart && this._rangeEnd && compareDates(this._rangeStart, this._rangeEnd) > 0) {
      [this._rangeStart, this._rangeEnd] = [this._rangeEnd, this._rangeStart];
    }
    this._activeDate = this._rangeEnd || this._rangeStart || this._activeDate;
    this._viewDate = startOfMonth(this._activeDate);
    this._render();
    if (options.emit !== false) {
      this._emitChange(Boolean(this._rangeStart && this._rangeEnd));
    }
    return true;
  }

  clear(options = {}) {
    this._selectedDate = null;
    this._rangeStart = null;
    this._rangeEnd = null;
    this._render();
    if (options.emit !== false) {
      this._emitChange(false);
    }
  }

  focusActiveDay() {
    this._dayButton(this._activeDate)?.focus();
  }

  _bindEvents() {
    addListener(this._listeners, this._element, "click", (event) => {
      const target = event.target;
      const day = target.closest?.("[data-calendar-day]");
      const prev = target.closest?.("[data-calendar-prev]");
      const next = target.closest?.("[data-calendar-next]");
      const preset = target.closest?.("[data-calendar-preset]");

      if (prev) {
        this._changeMonth(-1, true);
      } else if (next) {
        this._changeMonth(1, true);
      } else if (preset) {
        this._selectPreset(preset.dataset.calendarPreset);
      } else if (day) {
        this._selectDate(parseDate(day.dataset.calendarDay), true);
      }
    });

    addListener(this._listeners, this._element, "keydown", (event) => {
      const day = event.target.closest?.("[data-calendar-day]");
      if (!day) return;
      this._handleDayKeydown(event);
    });

    addListener(this._listeners, this._element, "change", (event) => {
      if (event.target.matches?.("[data-calendar-month]")) {
        this._setActiveMonth(
          this._viewDate.getFullYear(),
          Number(event.target.value),
          true,
        );
      }
      if (event.target.matches?.("[data-calendar-year]")) {
        this._setActiveMonth(
          Number(event.target.value),
          this._viewDate.getMonth(),
          true,
        );
      }
    });
  }

  _emitChange(complete) {
    dispatch(this._element, this._window, "change.moo.calendar", {
      date: this._selectedDate ? new Date(this._selectedDate) : undefined,
      value: this._selectedDate ? toIso(this._selectedDate) : "",
      startDate: this._rangeStart ? new Date(this._rangeStart) : undefined,
      endDate: this._rangeEnd ? new Date(this._rangeEnd) : undefined,
      startValue: this._rangeStart ? toIso(this._rangeStart) : "",
      endValue: this._rangeEnd ? toIso(this._rangeEnd) : "",
      complete,
    });
  }

  _changeMonth(amount, focus) {
    const nextView = startOfMonth(addMonths(this._viewDate, amount));
    this._setActiveMonth(nextView.getFullYear(), nextView.getMonth(), focus);
  }

  _setActiveMonth(year, month, focus = false) {
    const activeDay = Math.min(
      this._activeDate.getDate(),
      daysInMonth(year, month),
    );
    this._activeDate = this._nearestEnabledDate(new Date(year, month, activeDay));
    this._viewDate = startOfMonth(this._activeDate);
    this._render();
    if (focus) this.focusActiveDay();
  }

  _selectPreset(name) {
    if (!name) return;
    const today = new Date();
    const offsets = {
      today: 0,
      tomorrow: 1,
      "in-3-days": 3,
      "in-a-week": 7,
      "in-2-weeks": 14,
    };
    if (!(name in offsets)) return;
    this._selectDate(addDays(today, offsets[name]), true);
  }

  _handleDayKeydown(event) {
    // Sync active date from the focused day element so keyboard navigation
    // always starts from the currently focused day.
    const focusedDay = event.target.closest?.("[data-calendar-day]");
    const focusedDate = parseDate(focusedDay?.dataset?.calendarDay);
    if (focusedDate && compareDates(focusedDate, this._activeDate) !== 0) {
      this._activeDate = focusedDate;
    }
    const keyMap = {
      ArrowRight: 1,
      ArrowLeft: -1,
      ArrowDown: 7,
      ArrowUp: -7,
    };
    let nextDate = null;
    if (event.key in keyMap) {
      nextDate = addDays(this._activeDate, keyMap[event.key]);
    } else if (event.key === "Home") {
      nextDate = addDays(this._activeDate, -this._activeDate.getDay());
    } else if (event.key === "End") {
      nextDate = addDays(this._activeDate, 6 - this._activeDate.getDay());
    } else if (event.key === "PageUp") {
      nextDate = addMonths(this._activeDate, -1);
    } else if (event.key === "PageDown") {
      nextDate = addMonths(this._activeDate, 1);
    } else if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
      event.preventDefault();
      this._selectDate(this._activeDate, true);
      return;
    } else {
      return;
    }
    event.preventDefault();
    this._setActiveDate(nextDate, true, compareDates(nextDate, this._activeDate) < 0 ? -1 : 1);
  }

  _setActiveDate(date, focus = false, step = 0) {
    const nextDate = step === 0
      ? this._nearestEnabledDate(date)
      : this._nextEnabledDate(date, step);
    this._activeDate = nextDate;
    this._viewDate = startOfMonth(nextDate);
    this._render();
    if (focus) this.focusActiveDay();
  }

  _nextEnabledDate(date, step) {
    let candidate = parseDate(date);
    if (!candidate) return this._activeDate;
    const dayStep = step < 0 ? -1 : 1;
    for (let guard = 0; guard < 366; guard += 1) {
      if (this._config.minDate && compareDates(candidate, this._config.minDate) < 0) break;
      if (this._config.maxDate && compareDates(candidate, this._config.maxDate) > 0) break;
      if (!this._isDisabled(candidate)) return candidate;
      candidate = addDays(candidate, dayStep);
    }
    return this._activeDate;
  }

  _nearestEnabledDate(date) {
    const preferred = limitToRange(
      parseDate(date) || new Date(),
      this._config.minDate,
      this._config.maxDate,
    );
    if (!this._isDisabled(preferred)) return preferred;

    const monthStart = startOfMonth(preferred);
    const monthLength = daysInMonth(monthStart.getFullYear(), monthStart.getMonth());
    for (let day = 1; day <= monthLength; day += 1) {
      const candidate = new Date(monthStart.getFullYear(), monthStart.getMonth(), day);
      if (!this._isDisabled(candidate)) return candidate;
    }
    return preferred;
  }

  _selectDate(date, emit) {
    if (!date || this._isDisabled(date)) return;
    this._activeDate = date;
    this._viewDate = startOfMonth(date);
    if (this._mode === "range") {
      if (!this._rangeStart || this._rangeEnd || compareDates(date, this._rangeStart) < 0) {
        this._rangeStart = date;
        this._rangeEnd = null;
      } else {
        this._rangeEnd = date;
      }
      this._render();
      if (emit) this._emitChange(Boolean(this._rangeStart && this._rangeEnd));
      return;
    }
    this._selectedDate = date;
    this._render();
    if (emit) this._emitChange(true);
  }

  _isDisabled(date) {
    if (!date) return true;
    if (this._config.minDate && compareDates(date, this._config.minDate) < 0) return true;
    if (this._config.maxDate && compareDates(date, this._config.maxDate) > 0) return true;
    return this._disabledDates.has(toIso(date));
  }

  _isSelected(date) {
    if (this._mode === "range") {
      return sameDate(date, this._rangeStart) || sameDate(date, this._rangeEnd);
    }
    return sameDate(date, this._selectedDate);
  }

  _rangeState(date) {
    if (this._mode !== "range" || !this._rangeStart) return "";
    if (sameDate(date, this._rangeStart)) return "start";
    if (sameDate(date, this._rangeEnd)) return "end";
    if (this._rangeStart && this._rangeEnd && compareDates(date, this._rangeStart) > 0 && compareDates(date, this._rangeEnd) < 0) {
      return "middle";
    }
    return "";
  }

  _dayButton(date) {
    return this._element.querySelector(`[data-calendar-day="${toIso(date)}"]`);
  }

  _render() {
    const document = this._document;
    const fragment = document.createDocumentFragment();
    const header = document.createElement("div");
    header.className = "moo-calendar__header";

    const prev = document.createElement("button");
    prev.className = "btn btn-ghost btn-icon-sm moo-calendar__nav";
    prev.type = "button";
    prev.dataset.calendarPrev = "true";
    prev.setAttribute("aria-label", "Previous month");
    prev.appendChild(createIcon(document, "‹", "moo-calendar__nav-icon"));

    const next = document.createElement("button");
    next.className = "btn btn-ghost btn-icon-sm moo-calendar__nav";
    next.type = "button";
    next.dataset.calendarNext = "true";
    next.setAttribute("aria-label", "Next month");
    next.appendChild(createIcon(document, "›", "moo-calendar__nav-icon"));

    const caption = document.createElement("div");
    caption.className = "moo-calendar__caption";
    caption.id = this._captionId;
    caption.setAttribute("aria-live", "polite");

    if (this._config.captionLayout === "dropdown") {
      const month = document.createElement("select");
      month.className = "moo-calendar__select";
      month.dataset.calendarMonth = "true";
      month.setAttribute("aria-label", "Month");
      for (let index = 0; index < 12; index += 1) {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = monthName(index, this._config.locale);
        option.selected = index === this._viewDate.getMonth();
        month.appendChild(option);
      }
      const year = document.createElement("select");
      year.className = "moo-calendar__select";
      year.dataset.calendarYear = "true";
      year.setAttribute("aria-label", "Year");
      yearOptions(this._config.minDate, this._config.maxDate, this._viewDate).forEach((value) => {
        const option = document.createElement("option");
        option.value = String(value);
        option.textContent = String(value);
        option.selected = value === this._viewDate.getFullYear();
        year.appendChild(option);
      });
      caption.append(month, year);
    } else {
      caption.textContent = formatMonthYear(this._viewDate, this._config.locale);
    }

    header.append(prev, caption, next);
    fragment.appendChild(header);

    // The caller-provided calendar name (the root aria-label) must label the
    // actual role="grid" element, not just the root wrapper. A dedicated,
    // visually hidden label carries that name and the grid references it by id,
    // so the grid resolves an accessible name without fighting the caption's
    // aria-labelledby. The label lives OUTSIDE the grid so the grid's children
    // stay rows-only per its ARIA role.
    const gridLabel = document.createElement("div");
    gridLabel.id = this._labelId;
    gridLabel.className = "visually-hidden";
    gridLabel.textContent =
      this._element.getAttribute("aria-label") || formatMonthYear(this._viewDate, this._config.locale);
    fragment.appendChild(gridLabel);

    const weekdays = document.createElement("div");
    weekdays.className = "moo-calendar__weekdays";
    weekdays.setAttribute("role", "row");
    weekdayDates(this._config.locale).forEach((date) => {
      const label = document.createElement("span");
      label.className = "moo-calendar__weekday";
      label.setAttribute("role", "columnheader");
      label.textContent = new Intl.DateTimeFormat(this._config.locale, { weekday: "narrow" })
        .format(date);
      weekdays.appendChild(label);
    });

    const grid = document.createElement("div");
    grid.className = "moo-calendar__grid";
    grid.setAttribute("role", "grid");
    grid.setAttribute("aria-labelledby", this._labelId);
    grid.appendChild(weekdays);
    const first = startOfMonth(this._viewDate);
    const weekStart = firstDayOfWeek(this._config.locale);
    const start = addDays(first, -((first.getDay() - weekStart + 7) % 7));
    for (let week = 0; week < 6; week += 1) {
      const row = document.createElement("div");
      row.className = "moo-calendar__week";
      row.setAttribute("role", "row");
      for (let day = 0; day < 7; day += 1) {
        const date = addDays(start, week * 7 + day);
        const iso = toIso(date);
        const cell = document.createElement("div");
        cell.className = "moo-calendar__cell";
        cell.setAttribute("role", "gridcell");
        const button = document.createElement("button");
        button.className = "moo-calendar__day";
        button.type = "button";
        button.dataset.calendarDay = iso;
        button.textContent = String(date.getDate());
        button.tabIndex = sameDate(date, this._activeDate) ? 0 : -1;
        button.setAttribute("aria-label", formatDisplay(date, this._config.locale));
        button.dataset.calendarSelected = String(this._isSelected(date));
        if (date.getMonth() !== this._viewDate.getMonth()) {
          button.dataset.calendarOutside = "true";
        }
        if (sameDate(date, new Date())) {
          button.dataset.calendarToday = "true";
        }
        const rangeState = this._rangeState(date);
        if (rangeState) {
          button.dataset.calendarRange = rangeState;
        }
        if (this._isDisabled(date)) {
          button.disabled = true;
          button.setAttribute("aria-disabled", "true");
        }
        cell.appendChild(button);
        row.appendChild(cell);
      }
      grid.appendChild(row);
    }
    fragment.appendChild(grid);

    if (this._config.showPresets) {
      const presets = document.createElement("div");
      presets.className = "moo-calendar__presets";
      [
        ["today", "Today"],
        ["tomorrow", "Tomorrow"],
        ["in-3-days", "In 3 days"],
        ["in-a-week", "In a week"],
        ["in-2-weeks", "In 2 weeks"],
      ].forEach(([value, label]) => {
        const button = document.createElement("button");
        button.className = "btn btn-outline-secondary btn-sm moo-calendar__preset";
        button.type = "button";
        button.dataset.calendarPreset = value;
        button.textContent = label;
        presets.appendChild(button);
      });
      fragment.appendChild(presets);
    }

    this._element.classList.add("moo-calendar");
    this._element.dataset.calendar = this._element.dataset.calendar || "";
    this._element.dataset.calendarMode = this._mode;
    this._element.dataset.calendarActiveDate = toIso(this._activeDate);
    if (this._mode === "single" && this._selectedDate) {
      this._element.dataset.calendarValue = toIso(this._selectedDate);
    } else {
      delete this._element.dataset.calendarValue;
    }
    if (this._mode === "range") {
      this._element.dataset.calendarStartValue = this._rangeStart ? toIso(this._rangeStart) : "";
      this._element.dataset.calendarEndValue = this._rangeEnd ? toIso(this._rangeEnd) : "";
    } else {
      delete this._element.dataset.calendarStartValue;
      delete this._element.dataset.calendarEndValue;
    }
    this._element.replaceChildren(fragment);
  }
}

export default class MooDatepicker {
  static getInstance(element) {
    return element?.nodeType === 1 ? datepickerInstances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return MooDatepicker.getInstance(element) || new MooDatepicker(element, config);
  }

  constructor(element, config = {}) {
    if (!isElement(element, "[data-datepicker]")) {
      throw new TypeError("MooDatepicker requires a [data-datepicker] root element.");
    }
    const existing = datepickerInstances.get(element);
    if (existing) return existing;

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView || window;
    this._listeners = [];
    this._floatingListeners = [];
    this._disposed = false;
    this._positionPopover = null;
    this._popoverPortal = null;
    this._trigger = element.querySelector("[data-datepicker-trigger]");
    this._popover = element.querySelector("[data-datepicker-popover]");
    this._label = element.querySelector("[data-datepicker-label]");
    this._input =
      element.querySelector("[data-datepicker-input]") ||
      element.querySelector('input[type="hidden"]');
    this._calendarRoot = element.querySelector("[data-calendar]");
    if (!this._trigger || !this._popover || !this._label || !this._input || !this._calendarRoot) {
      throw new TypeError("MooDatepicker requires a trigger, popover, calendar, and hidden input.");
    }

    this._config = readDataConfig(element, {
      ...config,
      value: config.value || this._input.value || element.dataset.datepickerValue,
    });
    this._placeholder = this._config.placeholder;
    this._defaultValue = this._input.defaultValue || this._input.getAttribute("value") || "";
    this.calendar = MooCalendar.getOrCreateInstance(this._calendarRoot, {
      ...this._config,
      mode: "single",
      value: this._input.value || this._config.value,
    });

    datepickerInstances.set(element, this);
    this._syncFromCalendar();
    this._bindEvents();
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    removeListeners(this._listeners);
    this.hide(false);
    stopDatepickerPopoverPositioning(this);
    restoreDatepickerPopover(this);
    removeListeners(this._floatingListeners);
    this.calendar?.dispose();
    if (datepickerInstances.get(this._element) === this) {
      datepickerInstances.delete(this._element);
    }
  }

  show() {
    if (this._trigger.disabled || this._element.dataset.datepickerDisabled === "true") return;
    if (this.isOpen()) return;
    if (!dispatch(this._element, this._window, "show.moo.datepicker", {}, true)) return;
    this._popover.hidden = false;
    this._popover.classList.add("show");
    startDatepickerPopoverPositioning(this);
    this._trigger.setAttribute("aria-expanded", "true");
    this.calendar.focusActiveDay();
    dispatch(this._element, this._window, "shown.moo.datepicker");
  }

  hide(returnFocus = true) {
    const wasOpen = this.isOpen();
    if (!wasOpen) return;
    if (!dispatch(this._element, this._window, "hide.moo.datepicker", {}, true)) return;
    this._popover.hidden = true;
    this._popover.classList.remove("show");
    stopDatepickerPopoverPositioning(this);
    this._trigger.setAttribute("aria-expanded", "false");
    if (returnFocus) this._trigger.focus();
    dispatch(this._element, this._window, "hidden.moo.datepicker");
  }

  toggle() {
    if (this.isOpen()) {
      this.hide();
    } else {
      this.show();
    }
  }

  isOpen() {
    return !this._popover.hidden;
  }

  getDate(format = undefined) {
    return this.calendar.getDate(format);
  }

  setDate(date, options = {}) {
    const changed = this.calendar.setDate(date, { emit: false });
    if (changed) {
      this._syncFromCalendar();
      if (options.emit !== false) this._emitChange();
    }
    return changed;
  }

  clear(options = {}) {
    this.calendar.clear({ emit: false });
    this._syncFromCalendar();
    if (options.emit !== false) this._emitChange();
  }

  _bindEvents() {
    addListener(this._listeners, this._trigger, "click", () => this.toggle());
    addListener(this._listeners, this._popover, "keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        this.hide();
      }
    });
    addListener(this._listeners, this._document, "pointerdown", (event) => {
      if (this.isOpen() && !datepickerContains(this, event.target)) {
        // Defer dismissal so the browser can first move focus to the clicked
        // target; the deferred hide() then returns focus to the trigger per the
        // frozen "outside click returns focus to the trigger" contract.
        this._window.setTimeout(() => {
          if (this.isOpen() && !datepickerContains(this, event.target)) {
            this.hide();
          }
        }, 0);
      }
    });
    addListener(this._listeners, this._calendarRoot, "change.moo.calendar", (event) => {
      this._syncFromCalendar();
      this._emitChange();
      if (event.detail.complete) {
        this.hide();
      }
    });
    const form = this._input.form || this._element.closest("form");
    addListener(this._listeners, form, "reset", () => {
      this._window.setTimeout(() => {
        if (this._defaultValue) {
          this.setDate(this._defaultValue, { emit: false });
        } else {
          this.clear({ emit: false });
        }
      }, 0);
    });
  }

  _syncFromCalendar() {
    const value = this.calendar.getDate("yyyy-mm-dd") || "";
    setHiddenValue(this._input, value);
    this._element.dataset.datepickerValue = value;
    this._label.textContent = value
      ? formatDisplay(parseDate(value), this._config.locale)
      : this._placeholder;
  }

  _emitChange() {
    dispatch(this._element, this._window, "change.moo.datepicker", {
      date: this.getDate(),
      value: this.getDate("yyyy-mm-dd") || "",
    });
  }
}

export class MooDateRangePicker {
  static getInstance(element) {
    return element?.nodeType === 1 ? rangePickerInstances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return MooDateRangePicker.getInstance(element) || new MooDateRangePicker(element, config);
  }

  constructor(element, config = {}) {
    if (!isElement(element, "[data-datepicker-range]")) {
      throw new TypeError("MooDateRangePicker requires a [data-datepicker-range] root element.");
    }
    const existing = rangePickerInstances.get(element);
    if (existing) return existing;

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView || window;
    this._listeners = [];
    this._floatingListeners = [];
    this._disposed = false;
    this._positionPopover = null;
    this._popoverPortal = null;
    this._trigger = element.querySelector("[data-datepicker-trigger]");
    this._popover = element.querySelector("[data-datepicker-popover]");
    this._label = element.querySelector("[data-datepicker-label]");
    this._startInput = element.querySelector("[data-datepicker-range-start]");
    this._endInput = element.querySelector("[data-datepicker-range-end]");
    this._calendarRoot = element.querySelector("[data-calendar]");
    if (!this._trigger || !this._popover || !this._label || !this._startInput || !this._endInput || !this._calendarRoot) {
      throw new TypeError("MooDateRangePicker requires a trigger, popover, calendar, and start/end hidden inputs.");
    }

    this._config = readDataConfig(element, {
      ...config,
      mode: "range",
      startValue: config.startValue || this._startInput.value || element.dataset.datepickerStartValue,
      endValue: config.endValue || this._endInput.value || element.dataset.datepickerEndValue,
    });
    this._placeholder = this._config.placeholder;
    this._defaultStartValue = this._startInput.defaultValue || this._startInput.getAttribute("value") || "";
    this._defaultEndValue = this._endInput.defaultValue || this._endInput.getAttribute("value") || "";
    this.calendar = MooCalendar.getOrCreateInstance(this._calendarRoot, this._config);

    rangePickerInstances.set(element, this);
    this._syncFromCalendar();
    this._bindEvents();
  }

  dispose() {
    if (this._disposed) return;
    this._disposed = true;
    removeListeners(this._listeners);
    this.hide(false);
    stopDatepickerPopoverPositioning(this);
    restoreDatepickerPopover(this);
    removeListeners(this._floatingListeners);
    this.calendar?.dispose();
    if (rangePickerInstances.get(this._element) === this) {
      rangePickerInstances.delete(this._element);
    }
  }

  show() {
    if (this._trigger.disabled || this._element.dataset.datepickerDisabled === "true") return;
    if (this.isOpen()) return;
    if (!dispatch(this._element, this._window, "show.moo.datepicker", {}, true)) return;
    this._popover.hidden = false;
    this._popover.classList.add("show");
    startDatepickerPopoverPositioning(this);
    this._trigger.setAttribute("aria-expanded", "true");
    this.calendar.focusActiveDay();
    dispatch(this._element, this._window, "shown.moo.datepicker");
  }

  hide(returnFocus = true) {
    const wasOpen = this.isOpen();
    if (!wasOpen) return;
    if (!dispatch(this._element, this._window, "hide.moo.datepicker", {}, true)) return;
    this._popover.hidden = true;
    this._popover.classList.remove("show");
    stopDatepickerPopoverPositioning(this);
    this._trigger.setAttribute("aria-expanded", "false");
    if (returnFocus) this._trigger.focus();
    dispatch(this._element, this._window, "hidden.moo.datepicker");
  }

  toggle() {
    if (this.isOpen()) {
      this.hide();
    } else {
      this.show();
    }
  }

  isOpen() {
    return !this._popover.hidden;
  }

  getDates(format = undefined) {
    return this.calendar.getDates(format);
  }

  setDates(startDate, endDate, options = {}) {
    const changed = this.calendar.setDates(startDate, endDate, { emit: false });
    if (changed) {
      this._syncFromCalendar();
      if (options.emit !== false) this._emitChange();
    }
    return changed;
  }

  clear(options = {}) {
    this.calendar.clear({ emit: false });
    this._syncFromCalendar();
    if (options.emit !== false) this._emitChange();
  }

  _bindEvents() {
    addListener(this._listeners, this._trigger, "click", () => this.toggle());
    addListener(this._listeners, this._popover, "keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        this.hide();
      }
    });
    addListener(this._listeners, this._document, "pointerdown", (event) => {
      if (this.isOpen() && !datepickerContains(this, event.target)) {
        // Deferred dismissal; see MooDatepicker for the focus contract.
        this._window.setTimeout(() => {
          if (this.isOpen() && !datepickerContains(this, event.target)) {
            this.hide();
          }
        }, 0);
      }
    });
    const closeWhenFocusLeaves = () => {
      this._window.setTimeout(() => {
        if (this.isOpen() && !datepickerContains(this, this._document.activeElement)) {
          this.hide(false);
        }
      }, 0);
    };
    addListener(this._listeners, this._element, "focusout", closeWhenFocusLeaves);
    addListener(this._listeners, this._popover, "focusout", closeWhenFocusLeaves);
    addListener(this._listeners, this._calendarRoot, "change.moo.calendar", (event) => {
      this._syncFromCalendar();
      this._emitChange();
      if (event.detail.complete) {
        // Selection finished; close and return focus to the trigger. Do not
        // focus a day inside the now-hidden calendar.
        this.hide();
      } else {
        // Start selected only; keep the calendar open and keep roving focus on
        // the newly selected day.
        this.calendar.focusActiveDay();
      }
    });
    const form = this._startInput.form || this._element.closest("form");
    addListener(this._listeners, form, "reset", () => {
      this._window.setTimeout(() => {
        this.setDates(this._defaultStartValue, this._defaultEndValue, { emit: false });
      }, 0);
    });
  }

  _syncFromCalendar() {
    const [startValue = "", endValue = ""] = this.calendar.getDates("yyyy-mm-dd");
    setHiddenValue(this._startInput, startValue || "");
    setHiddenValue(this._endInput, endValue || "");
    this._element.dataset.datepickerStartValue = startValue || "";
    this._element.dataset.datepickerEndValue = endValue || "";
    if (startValue && endValue) {
      this._label.textContent = `${formatDisplay(parseDate(startValue), this._config.locale)} - ${formatDisplay(parseDate(endValue), this._config.locale)}`;
    } else if (startValue) {
      this._label.textContent = formatDisplay(parseDate(startValue), this._config.locale);
    } else {
      this._label.textContent = this._placeholder;
    }
  }

  _emitChange() {
    const [startDate, endDate] = this.getDates();
    const [startValue = "", endValue = ""] = this.getDates("yyyy-mm-dd");
    dispatch(this._element, this._window, "change.moo.datepicker", {
      startDate,
      endDate,
      startValue,
      endValue,
    });
  }
}

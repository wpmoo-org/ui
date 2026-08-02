const instances = new WeakMap();

function normalize(value) {
  return (value ?? "").toString().trim().toLowerCase();
}

export default class DataTable {
  static getInstance(element) {
    return element?.nodeType === 1 ? instances.get(element) || null : null;
  }

  static getOrCreateInstance(element, config = {}) {
    return DataTable.getInstance(element) || new DataTable(element, config);
  }

  constructor(element, config = {}) {
    if (element?.nodeType !== 1 || !element.matches(".datatable")) {
      throw new TypeError("DataTable requires a .datatable root element.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._table = element.querySelector(":scope .datatable-table");
    this._tbody = this._table?.querySelector(":scope > tbody");
    if (!this._table || !this._tbody) {
      throw new TypeError("DataTable requires a .datatable-table with a tbody.");
    }
    this._cards = element.querySelector("[data-datatable-cards]");
    const cardById = new Map(
      Array.from(element.querySelectorAll("[data-datatable-card]")).map((card) => [card.dataset.datatableCardFor, card])
    );

    this._config = { ...config };
    this._listeners = [];
    this._pageSize = Number(element.dataset.datatablePageSize) || 10;
    this._currentPage = 1;
    this._sortKey = null;
    this._sortDirection = null;
    this._selectedIds = new Set();
    this._facetSelections = new Map();
    this._searchTerm = "";
    this._tooltips = [];

    this._rows = Array.from(this._tbody.querySelectorAll(":scope > tr[data-datatable-row]")).map((tr, index) => ({
      element: tr,
      cardElement: cardById.get(tr.id) || null,
      index,
      search: normalize(tr.dataset.datatableSearch),
      facets: this._readFacets(tr),
    }));
    this._readInitialSort();

    instances.set(element, this);
    this._bindEvents();
    this._render();
    this._initBulkTooltips();
    this._initViewToggle();
  }

  dispose() {
    this._listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._listeners = [];
    this._tooltips.forEach((tooltip) => tooltip.dispose());
    this._tooltips = [];
    instances.delete(this._element);
  }

  getSelectedIds() {
    return Array.from(this._selectedIds);
  }

  _listen(target, type, handler, options) {
    if (!target) {
      return;
    }
    target.addEventListener(type, handler, options);
    this._listeners.push({ target, type, handler, options });
  }

  _bootstrap(name) {
    return this._window.bootstrap?.[name] || null;
  }

  // The bulk-actions bar's icon-only buttons carry data-bs-title instead of
  // a bare title attribute so Bootstrap's own Tooltip owns the hover/focus
  // affordance (matching the rest of Moo's icon-button contracts) rather
  // than the browser's unstyled, delayed native tooltip. Tooltip has no
  // Data API auto-init the way Dropdown does, so it needs this explicit,
  // one-time setup; the bar's markup is static, so it never needs re-init.
  // animation: false keeps show()/hide() synchronous -- with the default
  // CSS fade, a click on a tooltip's own dropdown-toggle button fires
  // "show.bs.dropdown" while the hover-triggered tooltip is still mid-fade,
  // so the hide() below (see show.bs.dropdown in _bindEvents) would find
  // it not yet fully shown and no-op, leaving it stuck open over the menu.
  _initBulkTooltips() {
    const Tooltip = this._bootstrap("Tooltip");
    if (!Tooltip) {
      return;
    }
    this._element.querySelectorAll("[data-datatable-bulk-actions] [data-bs-title]").forEach((trigger) => {
      this._tooltips.push(Tooltip.getOrCreateInstance(trigger, { animation: false }));
    });
  }

  // responsive_mode="toggle" renders both the table and the card list and
  // lets the reader pick between them (Odoo's List/Kanban switcher, not a
  // developer-chosen breakpoint), so the choice belongs to the reader across
  // visits, not just the current render.
  _initViewToggle() {
    const toggles = Array.from(this._element.querySelectorAll(".datatable-view-toggle"));
    if (!toggles.length) {
      return;
    }
    const inputs = toggles.flatMap((toggle) => Array.from(toggle.querySelectorAll("input")));
    const storageKey = `moo-datatable-view:${this._element.id}`;
    const setView = (value, { persist = false } = {}) => {
      this._element.dataset.datatableView = value;
      inputs.forEach((input) => {
        input.checked = input.value === value;
      });
      if (persist) {
        try {
          this._window.localStorage.setItem(storageKey, value);
        } catch {
          // Storage may be unavailable (private browsing); the toggle still works for this session.
        }
      }
    };
    let stored = null;
    try {
      stored = this._window.localStorage.getItem(storageKey);
    } catch {
      stored = null;
    }
    if (stored === "table" || stored === "cards") {
      setView(stored);
    }
    toggles.forEach((toggle) => {
      this._listen(toggle, "change", (event) => {
        const value = event.target.value;
        if (value !== "table" && value !== "cards") {
          return;
        }
        setView(value, { persist: true });
      });
    });
  }

  _readFacets(tr) {
    const facets = {};
    Array.from(tr.attributes).forEach((attr) => {
      const match = /^data-datatable-facet-(.+)$/.exec(attr.name);
      if (match) {
        facets[match[1]] = attr.value;
      }
    });
    return facets;
  }

  _readInitialSort() {
    const th = this._element.querySelector("th[data-datatable-initial-sort][data-datatable-column]");
    const direction = th?.dataset.datatableInitialSort;
    if (direction !== "asc" && direction !== "desc") {
      return;
    }
    this._sortKey = th.dataset.datatableColumn || null;
    this._sortDirection = this._sortKey ? direction : null;
  }

  _trigger(name, detail = {}) {
    this._element.dispatchEvent(
      new this._window.CustomEvent(`${name}.moo.datatable`, {
        bubbles: true,
        detail,
      })
    );
  }

  _sortValue(row, key) {
    const cell = row.element.querySelector(`:scope > [data-datatable-column="${key}"]`);
    if (!cell) {
      return "";
    }
    return normalize(cell.dataset.datatableSortValue ?? cell.textContent);
  }

  _matchesFilters(row) {
    if (this._searchTerm && !row.search.includes(this._searchTerm)) {
      return false;
    }
    for (const [facetKey, selected] of this._facetSelections) {
      if (selected.size === 0) {
        continue;
      }
      if (!selected.has(row.facets[facetKey])) {
        return false;
      }
    }
    return true;
  }

  _visibleRows() {
    const filtered = this._rows.filter((row) => this._matchesFilters(row));
    if (this._sortKey) {
      const direction = this._sortDirection === "desc" ? -1 : 1;
      filtered.sort((a, b) => {
        const aValue = this._sortValue(a, this._sortKey);
        const bValue = this._sortValue(b, this._sortKey);
        if (aValue === bValue) {
          return a.index - b.index;
        }
        return aValue > bValue ? direction : -direction;
      });
    } else {
      filtered.sort((a, b) => a.index - b.index);
    }
    return filtered;
  }

  _pageCount(rowCount) {
    return Math.max(1, Math.ceil(rowCount / this._pageSize));
  }

  _render() {
    const filtered = this._visibleRows();
    const pageCount = this._pageCount(filtered.length);
    this._currentPage = Math.min(Math.max(1, this._currentPage), pageCount);
    const start = (this._currentPage - 1) * this._pageSize;
    const pageRows = filtered.slice(start, start + this._pageSize);
    const pageRowIds = new Set(pageRows.map((row) => row.element.id));

    this._rows.forEach((row) => {
      const isVisible = pageRowIds.has(row.element.id);
      row.element.hidden = !isVisible;
      if (row.cardElement) {
        row.cardElement.hidden = !isVisible;
      }
    });
    pageRows.forEach((row) => {
      this._tbody.appendChild(row.element);
      if (this._cards && row.cardElement) {
        this._cards.appendChild(row.cardElement);
      }
    });

    this._renderToolbarState();
    this._renderSortHeaders();
    this._renderSelection(pageRows);
    this._renderEmptyState(filtered.length);
    this._renderPagination(filtered.length, pageCount);
    this._renderBulkActions();
  }

  _renderToolbarState() {
    const hasSearch = Boolean(this._searchTerm);
    const hasFacets = Array.from(this._facetSelections.values()).some((set) => set.size > 0);
    const resetButton = this._element.querySelector("[data-datatable-reset]");
    if (resetButton) {
      resetButton.hidden = !(hasSearch || hasFacets);
    }

    this._element.querySelectorAll("[data-datatable-facet]").forEach((facetRoot) => {
      const key = facetRoot.dataset.datatableFacet;
      const selected = this._facetSelections.get(key) || new Set();
      const trigger = facetRoot.querySelector(".datatable-facet-trigger");
      trigger?.classList.toggle("datatable-facet-trigger-active", selected.size > 0);
      const summary = facetRoot.querySelector("[data-datatable-facet-summary]");
      if (summary) {
        summary.hidden = selected.size === 0;
        summary.replaceChildren();
        if (selected.size > 2) {
          summary.appendChild(this._createFacetBadge(`${selected.size} selected`));
        } else {
          selected.forEach((value) => {
            const option = facetRoot.querySelector(`[data-datatable-facet-option="${value}"]`);
            const label = option?.querySelector("[data-datatable-facet-option-label]")?.textContent ?? value;
            summary.appendChild(this._createFacetBadge(label));
          });
        }
      }
      facetRoot.querySelectorAll("[data-datatable-facet-option]").forEach((option) => {
        const isSelected = selected.has(option.dataset.datatableFacetOption);
        option.classList.toggle("active", isSelected);
        option.setAttribute("aria-pressed", String(isSelected));
      });
    });
  }

  _createFacetBadge(text) {
    const badge = this._document.createElement("span");
    badge.className = "badge text-bg-secondary datatable-facet-badge";
    badge.textContent = text;
    return badge;
  }

  _renderSelection(pageRows) {
    const selectAllControls = Array.from(this._element.querySelectorAll("[data-datatable-select-all]"));
    pageRows.forEach((row) => {
      [row.element, row.cardElement].forEach((container) => {
        const checkbox = container?.querySelector("[data-datatable-select-row]");
        if (checkbox) {
          checkbox.checked = this._selectedIds.has(row.element.id);
        }
        container?.classList.toggle("datatable-row-selected", this._selectedIds.has(row.element.id));
      });
    });
    const total = pageRows.length;
    const checked = pageRows.filter((row) => this._selectedIds.has(row.element.id)).length;
    selectAllControls.forEach((control) => {
      control.checked = total > 0 && checked === total;
      control.indeterminate = checked > 0 && checked < total;
    });
  }

  _renderBulkActions() {
    const bar = this._element.querySelector("[data-datatable-bulk-actions]");
    if (!bar) {
      return;
    }
    bar.hidden = this._selectedIds.size === 0;
    const count = bar.querySelector("[data-datatable-bulk-count]");
    if (count) {
      count.textContent = String(this._selectedIds.size);
    }
  }

  _renderEmptyState(totalRows) {
    const empty = this._element.querySelector("[data-datatable-empty]");
    if (!empty) {
      return;
    }
    const hasRows = this._rows.length > 0;
    empty.hidden = totalRows !== 0;
    empty.querySelector(".datatable-empty-title")?.replaceChildren(
      this._document.createTextNode(hasRows ? "No matching results" : "No rows to display")
    );
    const copy = empty.querySelector(".datatable-empty-copy");
    if (copy) {
      copy.hidden = !hasRows;
    }
    const reset = empty.querySelector("[data-datatable-empty-reset]");
    if (reset) {
      reset.hidden = !hasRows;
    }
  }

  _sortAriaValue(direction) {
    if (direction === "asc") {
      return "ascending";
    }
    if (direction === "desc") {
      return "descending";
    }
    return "none";
  }

  _renderSortHeaders() {
    this._element.querySelectorAll("th[data-datatable-column]").forEach((th) => {
      const trigger = th.querySelector("[data-datatable-sort-key]");
      if (!trigger) {
        delete th.dataset.datatableSortState;
        delete th.dataset.datatableSortDirection;
        th.removeAttribute("aria-sort");
        return;
      }
      const key = th.dataset.datatableColumn;
      const direction = key && key === this._sortKey ? this._sortDirection : "none";
      th.dataset.datatableSortState = direction || "none";
      th.setAttribute("aria-sort", this._sortAriaValue(direction));
      if (direction === "asc" || direction === "desc") {
        th.dataset.datatableSortDirection = direction;
      } else {
        delete th.dataset.datatableSortDirection;
      }
    });
  }

  _renderPagination(totalRows, pageCount) {
    const first = this._element.querySelector("[data-datatable-page-first]");
    const prev = this._element.querySelector("[data-datatable-page-prev]");
    const next = this._element.querySelector("[data-datatable-page-next]");
    const last = this._element.querySelector("[data-datatable-page-last]");
    const atStart = this._currentPage <= 1;
    const atEnd = this._currentPage >= pageCount;
    [first, prev].forEach((button) => this._setPageItemDisabled(button, atStart));
    [next, last].forEach((button) => this._setPageItemDisabled(button, atEnd));

    const summary = this._element.querySelector("[data-datatable-results-summary]");
    if (summary) {
      if (totalRows === 0) {
        summary.textContent = "No results";
      } else {
        const start = (this._currentPage - 1) * this._pageSize + 1;
        const end = Math.min(this._currentPage * this._pageSize, totalRows);
        summary.textContent = `Showing ${start}-${end} of ${totalRows}`;
      }
    }

    const template = this._element.querySelector("template[data-datatable-page-numbers]");
    if (!template) {
      return;
    }
    template.parentNode
      .querySelectorAll("[data-datatable-page-number], [data-datatable-page-ellipsis]")
      .forEach((node) => node.remove());

    const pages = this._pageWindow(this._currentPage, pageCount);
    const fragment = this._document.createDocumentFragment();
    pages.forEach((page) => {
      const li = this._document.createElement("li");
      li.className = "page-item";
      if (page === "…") {
        li.dataset.datatablePageEllipsis = "";
        li.innerHTML = '<span class="page-link">…</span>';
      } else {
        li.dataset.datatablePageNumber = String(page);
        if (page === this._currentPage) {
          li.classList.add("active");
          li.setAttribute("aria-current", "page");
        }
        const button = this._document.createElement("button");
        button.type = "button";
        button.className = "page-link";
        button.textContent = String(page);
        button.setAttribute("aria-label", `Go to page ${page}`);
        button.dataset.datatablePageGo = String(page);
        li.appendChild(button);
      }
      fragment.appendChild(li);
    });
    template.parentNode.insertBefore(fragment, template);
  }

  _setPageItemDisabled(button, disabled) {
    if (!button) {
      return;
    }
    button.disabled = disabled;
    button.closest(".page-item")?.classList.toggle("disabled", disabled);
  }

  _pageWindow(current, total) {
    if (total <= 7) {
      return Array.from({ length: total }, (_, index) => index + 1);
    }
    const pages = new Set([1, total, current - 1, current, current + 1]);
    const sorted = Array.from(pages)
      .filter((page) => page >= 1 && page <= total)
      .sort((a, b) => a - b);
    const withEllipsis = [];
    sorted.forEach((page, index) => {
      if (index > 0 && page - sorted[index - 1] > 1) {
        withEllipsis.push("…");
      }
      withEllipsis.push(page);
    });
    return withEllipsis;
  }

  _setColumnVisible(key, visible, { syncViewToggle = true } = {}) {
    this._element.querySelectorAll(`[data-datatable-column="${key}"], [data-datatable-detail-column="${key}"]`).forEach((cell) => {
      cell.classList.toggle("datatable-col-hidden", !visible);
    });
    if (syncViewToggle) {
      this._element.querySelectorAll(`[data-datatable-column-toggle="${key}"]`).forEach((toggle) => {
        toggle.classList.toggle("active", visible);
        toggle.setAttribute("aria-pressed", String(visible));
      });
    }
  }

  _setSort(key, direction) {
    const validDirection = direction === "asc" || direction === "desc" ? direction : null;
    this._sortKey = validDirection ? key : null;
    this._sortDirection = validDirection;
    this._render();
    this._trigger("sort", { key: this._sortKey, direction: this._sortDirection });
  }

  _handleSortAction(event) {
    const trigger = event.target.closest("[data-datatable-sort-action]");
    if (!trigger) {
      return;
    }
    const menu = trigger.closest(".dropdown-menu");
    const key = menu
      ?.closest(".datatable-sort")
      ?.querySelector("[data-datatable-sort-key]")?.dataset.datatableSortKey;
    if (!key) {
      return;
    }
    const action = trigger.dataset.datatableSortAction;
    if (action === "hide") {
      this._setColumnVisible(key, false);
      return;
    }
    this._setSort(key, action);
  }

  _handleFacetClick(event) {
    const option = event.target.closest("[data-datatable-facet-option]");
    const clear = event.target.closest("[data-datatable-facet-clear]");
    if (!option && !clear) {
      return;
    }
    const facetRoot = event.target.closest("[data-datatable-facet]");
    const key = facetRoot?.dataset.datatableFacet;
    if (!key) {
      return;
    }
    const selected = this._facetSelections.get(key) || new Set();
    if (clear) {
      selected.clear();
    } else {
      const value = option.dataset.datatableFacetOption;
      if (selected.has(value)) {
        selected.delete(value);
      } else {
        selected.add(value);
      }
    }
    this._facetSelections.set(key, selected);
    this._currentPage = 1;
    this._render();
    this._trigger("filter");
  }

  _handleColumnToggleClick(event) {
    const toggle = event.target.closest("[data-datatable-column-toggle]");
    if (!toggle) {
      return;
    }
    const key = toggle.dataset.datatableColumnToggle;
    const visible = toggle.getAttribute("aria-pressed") === "true";
    this._setColumnVisible(key, visible, { syncViewToggle: false });
  }

  _handleReset() {
    const search = this._element.querySelector("[data-datatable-search]");
    if (search) {
      search.value = "";
    }
    this._searchTerm = "";
    this._facetSelections.forEach((selected) => selected.clear());
    this._currentPage = 1;
    this._render();
    this._trigger("filter");
  }

  _handleSelectAll(event) {
    const checked = event.target.checked;
    const filtered = this._visibleRows();
    const start = (this._currentPage - 1) * this._pageSize;
    const pageRows = filtered.slice(start, start + this._pageSize);
    pageRows.forEach((row) => {
      if (checked) {
        this._selectedIds.add(row.element.id);
      } else {
        this._selectedIds.delete(row.element.id);
      }
    });
    this._render();
    this._trigger("select");
  }

  _handleSelectRow(event) {
    const checkbox = event.target.closest("[data-datatable-select-row]");
    if (!checkbox) {
      return;
    }
    const row = checkbox.closest("[data-datatable-row]");
    const card = checkbox.closest("[data-datatable-card]");
    const rowId = row?.id || card?.dataset.datatableCardFor;
    if (!rowId) {
      return;
    }
    if (checkbox.checked) {
      this._selectedIds.add(rowId);
    } else {
      this._selectedIds.delete(rowId);
    }
    this._render();
    this._trigger("select");
  }

  _handleBulkClick(event) {
    if (event.target.closest("[data-datatable-bulk-clear]")) {
      this._clearSelection();
      return;
    }
    const updateTrigger = event.target.closest("[data-datatable-bulk-update]");
    if (updateTrigger) {
      const key = updateTrigger.dataset.datatableBulkUpdate;
      const value = updateTrigger.dataset.datatableBulkUpdateValue;
      this._applyBulkUpdate(key, value, updateTrigger);
      return;
    }
    const actionTrigger = event.target.closest("[data-datatable-bulk-action]");
    if (actionTrigger) {
      const action = actionTrigger.dataset.datatableBulkAction;
      if (action === "delete") {
        this._applyBulkDelete();
        return;
      }
      this._trigger(`bulk-${action}`, { ids: this.getSelectedIds() });
    }
  }

  _clearSelection() {
    this._selectedIds.clear();
    this._render();
    this._trigger("select");
  }

  _applyBulkUpdate(key, value, trigger) {
    const icon = trigger.querySelector("svg")?.cloneNode(true);
    const label = trigger.querySelector("span")?.textContent?.trim() ?? value;
    this._selectedIds.forEach((id) => {
      const row = this._rows.find((candidate) => candidate.element.id === id);
      if (!row) {
        return;
      }
      row.element.setAttribute(`data-datatable-facet-${key}`, value);
      row.facets[key] = value;
      const cell = row.element.querySelector(`[data-datatable-column="${key}"]`);
      if (!cell) {
        return;
      }
      const labelTarget = cell.querySelector("[data-datatable-cell-label]");
      if (labelTarget) {
        labelTarget.textContent = label;
      } else {
        cell.textContent = label;
      }
      const currentIcon = cell.querySelector("svg");
      if (currentIcon && icon) {
        currentIcon.replaceWith(icon.cloneNode(true));
      }
      const cardValue = row.cardElement?.querySelector(`[data-datatable-detail-column="${key}"] .datatable-card-value`);
      if (cardValue) {
        cardValue.innerHTML = cell.innerHTML;
      }
    });
    this._render();
    this._trigger("bulk-update", { key, value, ids: this.getSelectedIds() });
  }

  _applyBulkDelete() {
    const ids = this.getSelectedIds();
    ids.forEach((id) => {
      const index = this._rows.findIndex((row) => row.element.id === id);
      if (index !== -1) {
        this._rows[index].element.remove();
        this._rows[index].cardElement?.remove();
        this._rows.splice(index, 1);
      }
    });
    this._selectedIds.clear();
    this._render();
    this._trigger("bulk-delete", { ids });
  }

  _handlePageClick(event) {
    const goButton = event.target.closest("[data-datatable-page-go]");
    if (goButton) {
      this._currentPage = Number(goButton.dataset.datatablePageGo);
      this._render();
      return;
    }
    if (event.target.closest("[data-datatable-page-first]")) {
      this._currentPage = 1;
      this._render();
      return;
    }
    if (event.target.closest("[data-datatable-page-prev]")) {
      this._currentPage -= 1;
      this._render();
      return;
    }
    if (event.target.closest("[data-datatable-page-next]")) {
      this._currentPage += 1;
      this._render();
      return;
    }
    if (event.target.closest("[data-datatable-page-last]")) {
      this._currentPage = this._pageCount(this._visibleRows().length);
      this._render();
    }
  }

  _bindEvents() {
    const search = this._element.querySelector("[data-datatable-search]");
    this._listen(search, "input", (event) => {
      this._searchTerm = normalize(event.target.value);
      this._currentPage = 1;
      this._render();
      this._trigger("filter");
    });

    this._listen(this._element, "click", (event) => {
      this._handleSortAction(event);
      this._handleFacetClick(event);
      this._handleColumnToggleClick(event);
      this._handlePageClick(event);
      this._handleBulkClick(event);
      if (event.target.closest("[data-datatable-empty-reset]")) {
        this._handleReset();
      }
      if (event.target.closest("[data-datatable-select-row]")) {
        this._handleSelectRow(event);
      }
    });

    // Bound to the document, not this._element: a checkbox click does not
    // reliably move focus into the table (WebKit never focuses form
    // controls on click, and even where it does the bulk-actions bar itself
    // sits outside the table's DOM flow), so a listener scoped to the table
    // would miss Escape whenever focus is elsewhere on the page.
    this._listen(this._document, "keydown", (event) => {
      if (event.key === "Escape" && this._selectedIds.size > 0) {
        this._clearSelection();
      }
    });

    // A hover-triggered tooltip does not hide itself when a click opens the
    // same button's dropdown (Bootstrap Tooltip only listens for
    // mouseleave/blur), so it would otherwise sit on top of the open menu.
    // hide() alone is not enough: opening the dropdown shifts layout under
    // the still-hovered cursor, which makes the browser refire mouseenter
    // and the tooltip re-show a moment later. disable()/enable() -- not
    // hide() -- is Bootstrap's own way to suppress that: it makes show() a
    // no-op for as long as the dropdown stays open, however it gets
    // re-triggered.
    this._listen(this._element, "show.bs.dropdown", (event) => {
      const tooltip = this._bootstrap("Tooltip")?.getInstance(event.target);
      tooltip?.hide();
      tooltip?.disable();
    });
    this._listen(this._element, "hidden.bs.dropdown", (event) => {
      this._bootstrap("Tooltip")?.getInstance(event.target)?.enable();
    });

    const resetButton = this._element.querySelector("[data-datatable-reset]");
    this._listen(resetButton, "click", () => this._handleReset());

    this._element.querySelectorAll("[data-datatable-select-all]").forEach((selectAll) => {
      this._listen(selectAll, "change", (event) => this._handleSelectAll(event));
    });

    const pageSizeSelect = this._element.querySelector("[data-datatable-page-size-select]");
    this._listen(pageSizeSelect, "change", (event) => {
      this._pageSize = Number(event.target.value) || this._pageSize;
      this._currentPage = 1;
      this._render();
    });
  }
}

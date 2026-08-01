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
    if (element?.nodeType !== 1 || !element.matches(".data-table")) {
      throw new TypeError("DataTable requires a .data-table root element.");
    }
    const existing = instances.get(element);
    if (existing) {
      return existing;
    }

    this._element = element;
    this._document = element.ownerDocument;
    this._window = this._document.defaultView;
    this._table = element.querySelector(":scope .data-table-table");
    this._tbody = this._table?.querySelector(":scope > tbody");
    if (!this._table || !this._tbody) {
      throw new TypeError("DataTable requires a .data-table-table with a tbody.");
    }

    this._config = { ...config };
    this._listeners = [];
    this._pageSize = Number(element.dataset.dataTablePageSize) || 10;
    this._currentPage = 1;
    this._sortKey = null;
    this._sortDirection = null;
    this._selectedIds = new Set();
    this._facetSelections = new Map();
    this._searchTerm = "";

    this._rows = Array.from(this._tbody.querySelectorAll(":scope > tr")).map((tr, index) => ({
      element: tr,
      index,
      search: normalize(tr.dataset.dataTableSearch),
      facets: this._readFacets(tr),
    }));

    instances.set(element, this);
    this._bindEvents();
    this._render();
  }

  dispose() {
    this._listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    this._listeners = [];
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

  _readFacets(tr) {
    const facets = {};
    Array.from(tr.attributes).forEach((attr) => {
      const match = /^data-data-table-facet-(.+)$/.exec(attr.name);
      if (match) {
        facets[match[1]] = attr.value;
      }
    });
    return facets;
  }

  _trigger(name, detail = {}) {
    this._element.dispatchEvent(
      new this._window.CustomEvent(`${name}.moo.data-table`, {
        bubbles: true,
        detail,
      })
    );
  }

  _sortValue(row, key) {
    const cell = row.element.querySelector(`:scope > [data-data-table-column="${key}"]`);
    if (!cell) {
      return "";
    }
    return normalize(cell.dataset.dataTableSortValue ?? cell.textContent);
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
      row.element.hidden = !pageRowIds.has(row.element.id);
    });
    pageRows.forEach((row) => {
      this._tbody.appendChild(row.element);
    });

    this._renderToolbarState();
    this._renderSelection(pageRows);
    this._renderPagination(filtered.length, pageCount);
  }

  _renderToolbarState() {
    const hasSearch = Boolean(this._searchTerm);
    const hasFacets = Array.from(this._facetSelections.values()).some((set) => set.size > 0);
    const resetButton = this._element.querySelector("[data-data-table-reset]");
    if (resetButton) {
      resetButton.hidden = !(hasSearch || hasFacets);
    }

    this._element.querySelectorAll("[data-data-table-facet]").forEach((facetRoot) => {
      const key = facetRoot.dataset.dataTableFacet;
      const selected = this._facetSelections.get(key) || new Set();
      const trigger = facetRoot.querySelector(".data-table-facet-trigger");
      trigger?.classList.toggle("data-table-facet-trigger-active", selected.size > 0);
      const summary = facetRoot.querySelector("[data-data-table-facet-summary]");
      if (summary) {
        summary.hidden = selected.size === 0;
        summary.replaceChildren();
        if (selected.size > 2) {
          summary.appendChild(this._createFacetBadge(`${selected.size} selected`));
        } else {
          selected.forEach((value) => {
            const option = facetRoot.querySelector(`[data-data-table-facet-option="${value}"]`);
            const label = option?.querySelector("[data-data-table-facet-option-label]")?.textContent ?? value;
            summary.appendChild(this._createFacetBadge(label));
          });
        }
      }
      facetRoot.querySelectorAll("[data-data-table-facet-option]").forEach((option) => {
        const isSelected = selected.has(option.dataset.dataTableFacetOption);
        option.classList.toggle("active", isSelected);
        option.setAttribute("aria-pressed", String(isSelected));
      });
    });
  }

  _createFacetBadge(text) {
    const badge = this._document.createElement("span");
    badge.className = "badge text-bg-secondary data-table-facet-badge";
    badge.textContent = text;
    return badge;
  }

  _renderSelection(pageRows) {
    const selectAll = this._element.querySelector("[data-data-table-select-all]");
    pageRows.forEach((row) => {
      const checkbox = row.element.querySelector("[data-data-table-select-row]");
      if (checkbox) {
        checkbox.checked = this._selectedIds.has(row.element.id);
      }
    });
    if (selectAll) {
      const total = pageRows.length;
      const checked = pageRows.filter((row) => this._selectedIds.has(row.element.id)).length;
      selectAll.checked = total > 0 && checked === total;
      selectAll.indeterminate = checked > 0 && checked < total;
    }
    const countLabel = this._element.querySelector("[data-data-table-selection-count]");
    if (countLabel) {
      const totalFiltered = this._visibleRows().length;
      countLabel.textContent = `${this._selectedIds.size} of ${totalFiltered} row(s) selected.`;
    }
  }

  _renderPagination(totalRows, pageCount) {
    const status = this._element.querySelector("[data-data-table-page-status]");
    if (status) {
      status.textContent = `Page ${this._currentPage} of ${pageCount}`;
    }

    const first = this._element.querySelector("[data-data-table-page-first]");
    const prev = this._element.querySelector("[data-data-table-page-prev]");
    const next = this._element.querySelector("[data-data-table-page-next]");
    const last = this._element.querySelector("[data-data-table-page-last]");
    const atStart = this._currentPage <= 1;
    const atEnd = this._currentPage >= pageCount;
    [first, prev].forEach((button) => this._setPageItemDisabled(button, atStart));
    [next, last].forEach((button) => this._setPageItemDisabled(button, atEnd));

    const template = this._element.querySelector("template[data-data-table-page-numbers]");
    if (!template) {
      return;
    }
    template.parentNode
      .querySelectorAll("[data-data-table-page-number], [data-data-table-page-ellipsis]")
      .forEach((node) => node.remove());

    const pages = this._pageWindow(this._currentPage, pageCount);
    const fragment = this._document.createDocumentFragment();
    pages.forEach((page) => {
      const li = this._document.createElement("li");
      li.className = "page-item";
      if (page === "…") {
        li.dataset.dataTablePageEllipsis = "";
        li.innerHTML = '<span class="page-link">…</span>';
      } else {
        li.dataset.dataTablePageNumber = String(page);
        if (page === this._currentPage) {
          li.classList.add("active");
          li.setAttribute("aria-current", "page");
        }
        const button = this._document.createElement("button");
        button.type = "button";
        button.className = "page-link";
        button.textContent = String(page);
        button.setAttribute("aria-label", `Go to page ${page}`);
        button.dataset.dataTablePageGo = String(page);
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
    this._element.querySelectorAll(`[data-data-table-column="${key}"]`).forEach((cell) => {
      cell.classList.toggle("data-table-col-hidden", !visible);
    });
    if (syncViewToggle) {
      const toggle = this._element.querySelector(`[data-data-table-column-toggle="${key}"]`);
      if (toggle) {
        toggle.classList.toggle("active", visible);
        toggle.setAttribute("aria-pressed", String(visible));
      }
    }
  }

  _setSort(key, direction) {
    this._element.querySelectorAll("[data-data-table-column]").forEach((th) => {
      if (th.tagName === "TH") {
        delete th.dataset.dataTableSortDirection;
      }
    });
    this._sortKey = direction ? key : null;
    this._sortDirection = direction;
    if (direction) {
      const th = this._element.querySelector(`th[data-data-table-column="${key}"]`);
      if (th) {
        th.dataset.dataTableSortDirection = direction;
      }
    }
    this._render();
    this._trigger("sort", { key: this._sortKey, direction: this._sortDirection });
  }

  _handleSortAction(event) {
    const trigger = event.target.closest("[data-data-table-sort-action]");
    if (!trigger) {
      return;
    }
    const menu = trigger.closest(".dropdown-menu");
    const key = menu
      ?.closest(".data-table-sort")
      ?.querySelector("[data-data-table-sort-key]")?.dataset.dataTableSortKey;
    if (!key) {
      return;
    }
    const action = trigger.dataset.dataTableSortAction;
    if (action === "hide") {
      this._setColumnVisible(key, false);
      return;
    }
    this._setSort(key, action);
  }

  _handleFacetClick(event) {
    const option = event.target.closest("[data-data-table-facet-option]");
    const clear = event.target.closest("[data-data-table-facet-clear]");
    if (!option && !clear) {
      return;
    }
    const facetRoot = event.target.closest("[data-data-table-facet]");
    const key = facetRoot?.dataset.dataTableFacet;
    if (!key) {
      return;
    }
    const selected = this._facetSelections.get(key) || new Set();
    if (clear) {
      selected.clear();
    } else {
      const value = option.dataset.dataTableFacetOption;
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
    const toggle = event.target.closest("[data-data-table-column-toggle]");
    if (!toggle) {
      return;
    }
    const key = toggle.dataset.dataTableColumnToggle;
    const visible = toggle.getAttribute("aria-pressed") === "true";
    this._setColumnVisible(key, visible, { syncViewToggle: false });
  }

  _handleReset() {
    const search = this._element.querySelector("[data-data-table-search]");
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
    const checkbox = event.target.closest("[data-data-table-select-row]");
    if (!checkbox) {
      return;
    }
    const row = checkbox.closest("[data-data-table-row]");
    if (!row) {
      return;
    }
    if (checkbox.checked) {
      this._selectedIds.add(row.id);
    } else {
      this._selectedIds.delete(row.id);
    }
    this._render();
    this._trigger("select");
  }

  _handlePageClick(event) {
    const goButton = event.target.closest("[data-data-table-page-go]");
    if (goButton) {
      this._currentPage = Number(goButton.dataset.dataTablePageGo);
      this._render();
      return;
    }
    if (event.target.closest("[data-data-table-page-first]")) {
      this._currentPage = 1;
      this._render();
      return;
    }
    if (event.target.closest("[data-data-table-page-prev]")) {
      this._currentPage -= 1;
      this._render();
      return;
    }
    if (event.target.closest("[data-data-table-page-next]")) {
      this._currentPage += 1;
      this._render();
      return;
    }
    if (event.target.closest("[data-data-table-page-last]")) {
      this._currentPage = this._pageCount(this._visibleRows().length);
      this._render();
    }
  }

  _bindEvents() {
    const search = this._element.querySelector("[data-data-table-search]");
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
      if (event.target.closest("[data-data-table-select-row]")) {
        this._handleSelectRow(event);
      }
    });

    const resetButton = this._element.querySelector("[data-data-table-reset]");
    this._listen(resetButton, "click", () => this._handleReset());

    const selectAll = this._element.querySelector("[data-data-table-select-all]");
    this._listen(selectAll, "change", (event) => this._handleSelectAll(event));

    const pageSizeSelect = this._element.querySelector("[data-data-table-page-size-select]");
    this._listen(pageSizeSelect, "change", (event) => {
      this._pageSize = Number(event.target.value) || this._pageSize;
      this._currentPage = 1;
      this._render();
    });
  }
}

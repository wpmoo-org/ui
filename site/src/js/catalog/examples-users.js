import DataTable from "../../../../src/js/components/datatable.js";

const states = new WeakMap();

// Users example interactivity: one Sheet form for create + edit, plus
// Edit / Copy email / Delete user row actions, plus a bulk "Update
// status" action. Every mutation stays in the browser; the table is
// re-read through the Data Table's frozen public API (dispose +
// getOrCreateInstance) after each DOM change. JS fills the
// server-rendered row skeleton instead of fabricating markup.

const STATUS_RANKS = { active: 0, invited: 1, suspended: 2 };

const CREATE_COPY =
  "Fill in the details and add the user — it appears in the table right away. This is a live demo, so nothing is stored.";
const EDIT_COPY =
  "Change what you need and save — the row updates in the table right away. This is a live demo, so nothing is stored.";

function initialsOf(name) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase() || "—";
}

// Status badges are cloned from the server-rendered fixture rows (one
// per status value), so the module never hard-codes badge variant
// classes -- mirrors examples-tasks.js's collectIcons() for the same
// reason: the Data Table's own generic bulk-update (datatable.js
// _applyBulkUpdate) only knows how to swap plain text/icon pairs via
// data-datatable-cell-label, so it collapses a badge cell to bare text.
// This module re-renders the correct badge afterward, both here and in
// applyValues() below, listening to the bulk-update.moo.datatable event
// datatable.js already dispatches once its own (destructive) update
// finishes.
function collectStatusBadges(tableRoot, values) {
  const badges = {};
  for (const value of values) {
    const cell = tableRoot.querySelector(`tr[data-datatable-facet-status="${value}"] [data-datatable-column="status"] .badge`);
    if (cell) {
      badges[value] = cell.cloneNode(true);
    }
  }
  return badges;
}

export function initExamplesUsers(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const page = root.querySelector("[data-moo-example-users]");
  const tableRoot = page?.querySelector(".datatable");
  const tbody = tableRoot?.querySelector("tbody");
  const cards = tableRoot?.querySelector("[data-datatable-cards]");
  const skeleton = page?.querySelector("[data-moo-user-skeleton]");
  const sheet = page?.querySelector("#users-new-sheet");
  const form = sheet?.querySelector("form");
  const sheetTitle = sheet?.querySelector(".offcanvas-title");
  const sheetCopy = sheet?.querySelector("[data-moo-user-sheet-copy]");
  const submitButton = sheet?.querySelector(".moo-user-sheet-submit");
  const deleteDialog = page?.querySelector("#users-delete-dialog");
  const deleteDialogTitle = deleteDialog?.querySelector(".modal-title");
  const deleteDialogDescription = deleteDialog?.querySelector(".modal-description");
  const deleteConfirm = deleteDialog?.querySelector(".moo-user-delete-confirm");
  const fields = {
    name: sheet?.querySelector("#users-new-name"),
    email: sheet?.querySelector("#users-new-email"),
    role: sheet?.querySelector("#users-new-role"),
    team: sheet?.querySelector("#users-new-team"),
    status: sheet?.querySelector("#users-new-status"),
  };

  if (!page || !tableRoot || !tbody || !skeleton || !sheet || !form || !deleteDialog || !deleteConfirm || Object.values(fields).some((field) => !field)) {
    const dispose = () => states.delete(root);
    states.set(root, dispose);
    return dispose;
  }

  const statusBadges = collectStatusBadges(tableRoot, ["active", "invited", "suspended"]);
  let added = 0;
  let editRow = null;
  let deleteRow = null;

  const documentRoot = root.ownerDocument || root;
  const windowRoot = documentRoot.defaultView;
  const bootstrap = windowRoot?.bootstrap;
  const reinitTable = () => {
    DataTable.getOrCreateInstance(tableRoot).dispose();
    DataTable.getOrCreateInstance(tableRoot);
  };
  const hideSheet = () => bootstrap?.Offcanvas.getInstance(sheet)?.hide();
  const selectedLabel = (select) => select?.selectedOptions[0]?.textContent ?? select?.value ?? "";
  const optionLabel = (select, value) =>
    Array.from(select?.options ?? []).find((option) => option.value === value)?.textContent.trim() ?? value;

  const setSheetMode = (editing) => {
    if (!sheetTitle || !submitButton || !sheetCopy) {
      return;
    }
    sheetTitle.textContent = editing ? "Edit user" : "New user";
    submitButton.textContent = editing ? "Save changes" : "Add user";
    sheetCopy.textContent = editing ? EDIT_COPY : CREATE_COPY;
  };

  const rowById = (id) => tbody.querySelector(`tr[data-datatable-row]#${CSS.escape(id)}`);
  const cardById = (id) => cards?.querySelector(`[data-datatable-card-for="${CSS.escape(id)}"]`) ?? null;

  const setStatusBadge = (scope, status) => {
    const host = scope?.querySelector('[data-moo-badge="status"], [data-datatable-column="status"], [data-datatable-detail-column="status"] .datatable-card-value');
    const clone = statusBadges[status]?.cloneNode(true);
    if (host && clone) {
      host.replaceChildren(clone);
    }
  };

  const setActiveDot = (avatarEl, active) => {
    if (!avatarEl) {
      return;
    }
    let dot = avatarEl.querySelector(".avatar-badge");
    if (active) {
      if (!dot) {
        dot = documentRoot.createElement("span");
        dot.className = "avatar-badge avatar-badge--dot bg-success";
        dot.setAttribute("role", "status");
        dot.setAttribute("aria-label", "Active");
        avatarEl.appendChild(dot);
      }
    } else if (dot) {
      dot.remove();
    }
  };

  const setTeamLabel = (scope, label) => {
    const rowCell = scope?.matches?.('[data-datatable-column="team"]')
      ? scope
      : scope?.querySelector('[data-datatable-column="team"]');
    if (rowCell) {
      const labelNode = documentRoot.createElement("span");
      labelNode.setAttribute("data-moo-fill", "team");
      labelNode.textContent = label;
      rowCell.replaceChildren(labelNode);
      return;
    }

    const cardValue = scope?.querySelector('[data-datatable-detail-column="team"] .datatable-card-value');
    if (cardValue) {
      cardValue.setAttribute("data-moo-fill", "team");
      cardValue.textContent = label;
    }
  };

  const syncBulkMetadata = (row, values) => {
    const name = row.querySelector('[data-moo-fill="name"]')?.textContent.trim() ?? "";
    const email = row.querySelector('[data-moo-fill="email"]')?.textContent.trim() ?? "";
    const roleLabel = row.querySelector('[data-datatable-column="role"]')?.textContent.trim() ?? "";
    const team = values.team ?? row.getAttribute("data-datatable-facet-team") ?? "";
    const teamLabel = values.teamLabel ?? row.querySelector('[data-datatable-column="team"]')?.textContent.trim() ?? "";
    const status = values.status ?? row.getAttribute("data-datatable-facet-status") ?? "";
    const statusLabel = values.statusLabel ?? optionLabel(fields.status, status);

    row.setAttribute(
      "data-datatable-search",
      [name, email, roleLabel, teamLabel, statusLabel].join(" "),
    );
    row.setAttribute("data-datatable-facet-status", status);
    row.setAttribute("data-datatable-facet-team", team);
    row.querySelector('[data-datatable-column="team"]')?.setAttribute("data-datatable-sort-value", teamLabel.toLowerCase());
    row.querySelector('[data-datatable-column="status"]')?.setAttribute("data-datatable-sort-value", String(STATUS_RANKS[status] ?? 99));
  };

  const applyValues = (row, card, values) => {
    const scopes = [row, card];
    const fillAll = (key, text) => {
      for (const scope of scopes) {
        scope?.querySelectorAll(`[data-moo-fill="${key}"]`).forEach((node) => {
          node.textContent = text;
        });
      }
    };
    fillAll("name", values.name);
    fillAll("email", values.email);
    fillAll("role", values.roleLabel);
    fillAll("team", values.teamLabel);

    for (const scope of scopes) {
      setStatusBadge(scope, values.status);
      const avatarEl = scope?.querySelector(".avatar");
      if (avatarEl) {
        avatarEl.classList.remove("invisible");
        avatarEl.setAttribute("aria-label", values.name);
        const fallback = avatarEl.querySelector(".avatar-fallback");
        if (fallback) {
          fallback.textContent = initialsOf(values.name);
        }
        setActiveDot(avatarEl, values.status === "active");
      }
    }

    // Server rows lead the search payload with the name, matching how
    // the fixture rows themselves are searched (name, email, role,
    // team, status label).
    row.setAttribute(
      "data-datatable-search",
      [values.name, values.email, values.roleLabel, values.teamLabel, values.statusLabel].join(" "),
    );
    row.setAttribute("data-datatable-facet-status", values.status);
    row.setAttribute("data-datatable-facet-team", values.team);
    const userCell = row.querySelector('[data-datatable-column="user"]');
    userCell?.setAttribute("data-datatable-sort-value", values.name.toLowerCase());
    row.querySelector('[data-datatable-column="role"]')?.setAttribute("data-datatable-sort-value", values.roleLabel.toLowerCase());
    row.querySelector('[data-datatable-column="team"]')?.setAttribute("data-datatable-sort-value", values.teamLabel.toLowerCase());
    row.querySelector('[data-datatable-column="status"]')?.setAttribute("data-datatable-sort-value", String(STATUS_RANKS[values.status] ?? 99));

    if (card) {
      card.setAttribute("data-datatable-card-for", row.id);
    }
  };

  const readFormValues = () => ({
    name: fields.name.value.trim(),
    email: fields.email.value.trim(),
    role: fields.role.value,
    roleLabel: selectedLabel(fields.role),
    team: fields.team.value,
    teamLabel: selectedLabel(fields.team),
    status: fields.status.value,
    statusLabel: selectedLabel(fields.status),
  });

  const onSubmit = (event) => {
    event.preventDefault();
    const values = readFormValues();
    if (!values.name || !values.email) {
      return;
    }

    if (editRow) {
      const row = editRow;
      const card = cardById(row.id);
      applyValues(row, card, values);
    } else {
      const clone = skeleton.content.querySelector("[data-moo-user-skeleton-item]").cloneNode(true);
      const row = clone.querySelector("tr[data-datatable-row]");
      const card = clone.querySelector("article[data-datatable-card]");
      added += 1;
      row.id = `usr-new-${added}`;
      const syncSelect = (scope, suffix) => {
        const input = scope?.querySelector("input[data-datatable-select-row]");
        if (input) {
          input.id = `${tableRoot.id}-${row.id}-${suffix}`;
          input.setAttribute("aria-label", `Select ${values.name}`);
        }
      };
      syncSelect(row, "table-select");
      syncSelect(card, "card-select");
      applyValues(row, card, values);
      row.querySelector('[data-datatable-column="last_active"] span')?.replaceChildren("Just now");
      row.querySelector('[data-datatable-column="last_active"]')?.setAttribute("data-datatable-sort-value", "0");
      card.querySelector('[data-datatable-detail-column="last_active"] .datatable-card-value span')?.replaceChildren("Just now");
      tbody.prepend(row);
      cards?.prepend(card);
    }

    editRow = null;
    form.reset();
    setSheetMode(false);
    reinitTable();
    hideSheet();
  };

  // Row actions fire from both the table row and its card; resolve the
  // owning tr either way, then apply the action.
  const findRowFromAction = (target) => {
    const row = target.closest("tr[data-datatable-row]");
    if (row) {
      return row;
    }
    const card = target.closest("[data-datatable-card]");
    if (card) {
      return rowById(card.getAttribute("data-datatable-card-for"));
    }
    const menu = target.closest(".dropdown-menu[data-datatable-row-action-owner]");
    const ownerId = menu?.getAttribute("data-datatable-row-action-owner");
    return ownerId ? rowById(ownerId) : null;
  };

  const closeRowMenu = (target) => {
    const menu = target.closest(".dropdown-menu[data-datatable-row-action-owner]");
    const triggerId = menu?.getAttribute("data-datatable-row-action-trigger");
    const triggerFromMenu = triggerId ? documentRoot.getElementById(triggerId) : null;
    const toggle =
      target.closest(".dropdown")?.querySelector('[data-bs-toggle="dropdown"]') ||
      triggerFromMenu ||
      page.querySelector('.table-row-actions [data-bs-toggle="dropdown"][aria-expanded="true"]');
    bootstrap?.Dropdown.getInstance(toggle)?.hide();
  };

  const openEditSheet = (row) => {
    const values = {
      name: row.querySelector('[data-moo-fill="name"]')?.textContent.trim() ?? "",
      email: row.querySelector('[data-moo-fill="email"]')?.textContent.trim() ?? "",
      role: (row.querySelector('[data-datatable-column="role"]')?.textContent.trim() ?? "").toLowerCase(),
      team: row.getAttribute("data-datatable-facet-team") ?? "platform",
      status: row.getAttribute("data-datatable-facet-status") ?? "active",
    };
    fields.name.value = values.name;
    fields.email.value = values.email;
    fields.role.value = values.role;
    fields.team.value = values.team;
    fields.status.value = values.status;
    editRow = row;
    setSheetMode(true);
    bootstrap?.Offcanvas.getOrCreateInstance(sheet).show();
  };

  const onPageClick = (event) => {
    const target = event.target;
    if (!windowRoot || !(target instanceof windowRoot.Element)) {
      return;
    }
    if (target.closest("[data-moo-user-delete]")) {
      const row = findRowFromAction(target);
      if (!row) {
        return;
      }
      closeRowMenu(target);
      deleteRow = row;
      const name = row.querySelector('[data-moo-fill="name"]')?.textContent.trim() || "this user";
      if (deleteDialogTitle) {
        deleteDialogTitle.textContent = `Delete this user: ${name}?`;
      }
      if (deleteDialogDescription) {
        deleteDialogDescription.textContent = `You are about to delete “${name}”.\nThis action cannot be undone.`;
      }
      bootstrap?.Modal.getOrCreateInstance(deleteDialog).show();
      return;
    }
    if (target.closest("[data-moo-user-edit]")) {
      const row = findRowFromAction(target);
      if (!row) {
        return;
      }
      closeRowMenu(target);
      openEditSheet(row);
      return;
    }
    if (target.closest("[data-moo-user-copy]")) {
      const row = findRowFromAction(target);
      if (!row) {
        return;
      }
      const email = row.querySelector('[data-moo-fill="email"]')?.textContent.trim() ?? "";
      windowRoot.navigator.clipboard?.writeText(email).catch(() => {});
      closeRowMenu(target);
    }
  };

  const onSheetShow = () => {
    if (!editRow) {
      form.reset();
      setSheetMode(false);
    }
  };
  const onSheetHidden = () => {
    editRow = null;
  };
  const onDeleteConfirm = () => {
    const row = deleteRow;
    deleteRow = null;
    if (!row) {
      return;
    }
    cardById(row.id)?.remove();
    row.remove();
    if (editRow === row) {
      editRow = null;
    }
    reinitTable();
  };
  const onDeleteDialogHidden = () => {
    deleteRow = null;
  };

  // datatable.js updates plain cell/card content and cached facets. The
  // Users demo owns richer badge/avatar/team markup and search/sort metadata,
  // so restore those hooks and re-read the table after bulk changes.
  const onBulkUpdate = (event) => {
    const { key, value, ids } = event.detail ?? {};
    if (key !== "status" && key !== "team") {
      return;
    }
    const label = optionLabel(key === "status" ? fields.status : fields.team, value);
    const updatedIds = Array.isArray(ids) ? ids : [];
    let updated = false;
    updatedIds.forEach((id) => {
      const row = rowById(id);
      if (!row) {
        return;
      }
      const card = cardById(id);
      if (key === "status") {
        setStatusBadge(row, value);
        setStatusBadge(card, value);
        const avatarActive = value === "active";
        [row, card].forEach((scope) => {
          setActiveDot(scope?.querySelector(".avatar"), avatarActive);
        });
        syncBulkMetadata(row, { status: value, statusLabel: label });
      } else {
        setTeamLabel(row, label);
        setTeamLabel(card, label);
        syncBulkMetadata(row, { team: value, teamLabel: label });
      }
      updated = true;
    });
    if (updated) {
      queueMicrotask(reinitTable);
    }
  };

  form.addEventListener("submit", onSubmit);
  documentRoot.addEventListener("click", onPageClick);
  sheet.addEventListener("show.bs.offcanvas", onSheetShow);
  sheet.addEventListener("hidden.bs.offcanvas", onSheetHidden);
  deleteConfirm.addEventListener("click", onDeleteConfirm);
  deleteDialog.addEventListener("hidden.bs.modal", onDeleteDialogHidden);
  tableRoot.addEventListener("bulk-update.moo.datatable", onBulkUpdate);

  const dispose = () => {
    form.removeEventListener("submit", onSubmit);
    documentRoot.removeEventListener("click", onPageClick);
    sheet.removeEventListener("show.bs.offcanvas", onSheetShow);
    sheet.removeEventListener("hidden.bs.offcanvas", onSheetHidden);
    deleteConfirm.removeEventListener("click", onDeleteConfirm);
    deleteDialog.removeEventListener("hidden.bs.modal", onDeleteDialogHidden);
    tableRoot.removeEventListener("bulk-update.moo.datatable", onBulkUpdate);
    // reinitTable() leaves a live DataTable behind; release it so a
    // disposed example page carries no orphaned listeners.
    DataTable.getOrCreateInstance(tableRoot).dispose();
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

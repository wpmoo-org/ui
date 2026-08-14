import DataTable from "../../../../src/js/components/datatable.js";

const states = new WeakMap();

// Tasks example interactivity: one Sheet form for create + edit, plus
// Edit / Copy link / Delete task row actions. Every mutation stays
// in the browser; the table is re-read through the Data Table's frozen
// public API (dispose + getOrCreateInstance) after each DOM change. JS
// fills the server-rendered row skeleton instead of fabricating markup.

const STATUS_RANKS = { open: 0, "in-progress": 1, blocked: 2, done: 3 };
const PRIORITY_RANKS = { high: 0, medium: 1, low: 2 };
const CREATE_COPY =
  "Fill in the details and add the task — it appears in the table right away. This is a live demo, so nothing is stored.";
const EDIT_COPY =
  "Change what you need and save — the row updates in the table right away. This is a live demo, so nothing is stored.";

// Icons for status/priority swaps are cloned from the server-rendered
// fixture rows, so the module never hard-codes svg paths.
function collectIcons(tableRoot, facetKey, values) {
  const icons = {};
  for (const value of values) {
    const cell = tableRoot.querySelector(
      `tr[data-datatable-facet-${facetKey}="${value}"] [data-datatable-column="${facetKey}"] svg`,
    );
    if (cell) {
      icons[value] = cell.cloneNode(true);
    }
  }
  return icons;
}

function setChoice(node, label, icon) {
  if (!node) {
    return;
  }
  const target = node.querySelector("[data-datatable-cell-label]");
  if (target) {
    target.textContent = label;
  }
  const svg = node.querySelector("svg");
  if (svg && icon) {
    svg.replaceWith(icon.cloneNode(true));
  }
}

function dueRank(due) {
  const day = Number.parseInt(due.replace(/^\D+/, ""), 10);
  return Number.isFinite(day) ? day : 99;
}

export function initExamplesTasks(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const page = root.querySelector("[data-moo-example-tasks]");
  const tableRoot = page?.querySelector(".datatable");
  const tbody = tableRoot?.querySelector("tbody");
  const cards = tableRoot?.querySelector("[data-datatable-cards]");
  const skeleton = page?.querySelector("[data-moo-task-skeleton]");
  const sheet = page?.querySelector("#tasks-new-sheet");
  const form = sheet?.querySelector("form");
  const sheetTitle = sheet?.querySelector(".offcanvas-title");
  const sheetCopy = sheet?.querySelector("[data-moo-task-sheet-copy]");
  const submitButton = sheet?.querySelector(".moo-task-sheet-submit");
  const deleteDialog = page?.querySelector("#tasks-delete-dialog");
  const deleteDialogTitle = deleteDialog?.querySelector(".modal-title");
  const deleteDialogDescription = deleteDialog?.querySelector(".modal-description");
  const deleteConfirm = deleteDialog?.querySelector(".moo-task-delete-confirm");
  const fields = {
    title: sheet?.querySelector("#tasks-new-title"),
    tag: sheet?.querySelector("#tasks-new-tag"),
    status: sheet?.querySelector("#tasks-new-status"),
    priority: sheet?.querySelector("#tasks-new-priority"),
    due: sheet?.querySelector("#tasks-new-due"),
    assignee: sheet?.querySelector("#tasks-new-assignee"),
  };

  if (!page || !tableRoot || !tbody || !skeleton || !sheet || !form || !deleteDialog || !deleteConfirm || Object.values(fields).some((field) => !field)) {
    const dispose = () => states.delete(root);
    states.set(root, dispose);
    return dispose;
  }

  const statusIcons = collectIcons(tableRoot, "status", Object.keys(STATUS_RANKS));
  const priorityIcons = collectIcons(tableRoot, "priority", Object.keys(PRIORITY_RANKS));
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

  const setSheetMode = (editing) => {
    if (!sheetTitle || !submitButton || !sheetCopy) {
      return;
    }
    sheetTitle.textContent = editing ? "Edit task" : "New task";
    submitButton.textContent = editing ? "Save changes" : "Add task";
    sheetCopy.textContent = editing ? EDIT_COPY : CREATE_COPY;
  };

  const rowById = (id) => tbody.querySelector(`tr[data-datatable-row]#${CSS.escape(id)}`);
  const cardById = (id) => cards?.querySelector(`[data-datatable-card-for="${CSS.escape(id)}"]`) ?? null;

  const applyValues = (row, card, values) => {
    const statusRank = STATUS_RANKS[values.status] ?? 99;
    const priorityRank = PRIORITY_RANKS[values.priority] ?? 99;

    // The skeleton renders the same data-moo-* markers on the row and its
    // card, so fill both scopes; fixture rows/cards carry no markers and
    // are rewritten by the edit branch instead.
    const scopes = [row, card];
    const fillAll = (key, text) => {
      for (const scope of scopes) {
        scope?.querySelectorAll(`[data-moo-fill="${key}"]`).forEach((node) => {
          node.textContent = text;
        });
      }
    };
    fillAll("title", values.title);
    fillAll("assignee", values.assignee);
    fillAll("due", values.due);
    for (const scope of scopes) {
      const badge = scope?.querySelector("[data-moo-badge=\"tag\"] .badge");
      if (badge) {
        badge.textContent = values.tagLabel;
      }
      scope?.querySelectorAll("[data-moo-choice=\"status\"]").forEach((node) => {
        setChoice(node, values.statusLabel, statusIcons[values.status]);
      });
      scope?.querySelectorAll("[data-moo-choice=\"priority\"]").forEach((node) => {
        setChoice(node, values.priorityLabel, priorityIcons[values.priority]);
      });
    }

    // Server rows lead the search payload with the TSK-nnn ref; derive it
    // from the row id (tsk-118 -> TSK-118) so ref searches keep working
    // after an edit.
    row.setAttribute(
      "data-datatable-search",
      [row.id.toUpperCase(), values.title, values.tagLabel, values.statusLabel, values.priorityLabel, values.assignee, values.due].join(" "),
    );
    row.setAttribute("data-datatable-facet-status", values.status);
    row.setAttribute("data-datatable-facet-priority", values.priority);
    row.setAttribute("data-datatable-facet-tag", values.tag);
    const taskCell = row.querySelector("[data-datatable-column=\"task\"]");
    taskCell?.setAttribute("data-datatable-sort-value", values.title.toLowerCase());
    row.querySelector("[data-datatable-column=\"status\"]")?.setAttribute("data-datatable-sort-value", String(statusRank));
    row.querySelector("[data-datatable-column=\"priority\"]")?.setAttribute("data-datatable-sort-value", String(priorityRank));
    row.querySelector("[data-datatable-column=\"assignee\"]")?.setAttribute("data-datatable-sort-value", values.assignee.toLowerCase());
    row.querySelector("[data-datatable-column=\"due\"]")?.setAttribute("data-datatable-sort-value", String(dueRank(values.due)));

    if (card) {
      card.setAttribute("data-datatable-card-for", row.id);
    }
  };

  const readFormValues = () => ({
    title: fields.title.value.trim(),
    tag: fields.tag.value,
    tagLabel: selectedLabel(fields.tag),
    status: fields.status.value,
    statusLabel: selectedLabel(fields.status),
    priority: fields.priority.value,
    priorityLabel: selectedLabel(fields.priority),
    due: fields.due.value.trim() || "—",
    assignee: fields.assignee.value.trim() || "Unassigned",
  });

  const onSubmit = (event) => {
    event.preventDefault();
    const values = readFormValues();
    if (!values.title) {
      return;
    }

    if (editRow) {
      const row = editRow;
      const card = cardById(row.id);
      applyValues(row, card, values);
      // Fixture rows carry no data-moo-fill markers; rewrite the title
      // span the server rendered instead.
      const titleCell = row.querySelector("[data-datatable-column=\"task\"] .text-truncate");
      if (titleCell) {
        titleCell.textContent = values.title;
      }
      // Fixture rows render assignee/due as bare text; rewrite both shapes.
      const assigneeCell = row.querySelector("[data-datatable-column=\"assignee\"]");
      const assigneeFill = assigneeCell?.querySelector("[data-moo-fill=\"assignee\"]");
      if (assigneeFill) {
        assigneeFill.textContent = values.assignee;
      } else if (assigneeCell) {
        assigneeCell.textContent = values.assignee;
      }
      const dueCell = row.querySelector("[data-datatable-column=\"due\"]");
      const dueFill = dueCell?.querySelector("[data-moo-fill=\"due\"]");
      if (dueFill) {
        dueFill.textContent = values.due;
      } else {
        dueCell?.querySelector("span")?.replaceChildren(values.due);
      }
      const cardAssignee = card?.querySelector("[data-datatable-detail-column=\"assignee\"] .datatable-card-value");
      if (cardAssignee) {
        cardAssignee.textContent = values.assignee;
      }
      const cardDue = card?.querySelector("[data-datatable-detail-column=\"due\"] .datatable-card-value span");
      if (cardDue) {
        cardDue.textContent = values.due;
      }
      card?.querySelector(".datatable-card-title")?.replaceChildren(values.title);
      // Icon + label cells: setChoice works from any ancestor of the
      // label/svg pair, so one selector covers fixture tds, skeleton
      // spans, and the card detail values alike.
      setChoice(row.querySelector("[data-datatable-column=\"status\"]"), values.statusLabel, statusIcons[values.status]);
      setChoice(row.querySelector("[data-datatable-column=\"priority\"]"), values.priorityLabel, priorityIcons[values.priority]);
      setChoice(card?.querySelector("[data-datatable-detail-column=\"status\"] .datatable-card-value"), values.statusLabel, statusIcons[values.status]);
      setChoice(card?.querySelector("[data-datatable-detail-column=\"priority\"] .datatable-card-value"), values.priorityLabel, priorityIcons[values.priority]);
      row.querySelector("[data-datatable-column=\"task\"] .badge")?.replaceChildren(values.tagLabel);
    } else {
      const clone = skeleton.content.querySelector("[data-moo-task-skeleton-item]").cloneNode(true);
      const row = clone.querySelector("tr[data-datatable-row]");
      const card = clone.querySelector("article[data-datatable-card]");
      added += 1;
      row.id = `tsk-new-${added}`;
      // The skeleton's select checkboxes carry placeholder ids; give them
      // the package's <table>-<row>-{table,card}-select convention once
      // the row has its id.
      const syncSelect = (scope, suffix) => {
        const input = scope?.querySelector("input[data-datatable-select-row]");
        if (input) {
          input.id = `${tableRoot.id}-${row.id}-${suffix}`;
          input.setAttribute("aria-label", `Select ${values.title}`);
        }
      };
      syncSelect(row, "table-select");
      syncSelect(card, "card-select");
      applyValues(row, card, values);
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
      target.closest(".dropdown")?.querySelector("[data-bs-toggle=\"dropdown\"]") ||
      triggerFromMenu ||
      page.querySelector(".table-row-actions [data-bs-toggle=\"dropdown\"][aria-expanded=\"true\"]");
    bootstrap?.Dropdown.getInstance(toggle)?.hide();
  };

  const openEditSheet = (row) => {
    const values = {
      title: row.querySelector("[data-datatable-column=\"task\"] .text-truncate")?.textContent.trim() ?? "",
      tag: row.getAttribute("data-datatable-facet-tag") ?? "docs",
      status: row.getAttribute("data-datatable-facet-status") ?? "open",
      priority: row.getAttribute("data-datatable-facet-priority") ?? "medium",
      due: row.querySelector("[data-datatable-column=\"due\"]")?.textContent.trim() ?? "",
      assignee: row.querySelector("[data-datatable-column=\"assignee\"]")?.textContent.trim() ?? "",
    };
    fields.title.value = values.title;
    fields.tag.value = values.tag;
    fields.status.value = values.status;
    fields.priority.value = values.priority;
    fields.due.value = values.due === "—" ? "" : values.due;
    fields.assignee.value = values.assignee === "Unassigned" ? "" : values.assignee;
    editRow = row;
    setSheetMode(true);
    bootstrap?.Offcanvas.getOrCreateInstance(sheet).show();
  };

  const onPageClick = (event) => {
    const target = event.target;
    if (!windowRoot || !(target instanceof windowRoot.Element)) {
      return;
    }
    if (target.closest("[data-moo-task-delete]")) {
      const row = findRowFromAction(target);
      if (!row) {
        return;
      }
      closeRowMenu(target);
      // Destructive actions confirm first: the Alert Dialog names the row
      // it will remove; only its Delete button deletes.
      deleteRow = row;
      const ref = row.id.toUpperCase();
      const title = row.querySelector("[data-datatable-column=\"task\"] .text-truncate")?.textContent.trim() || ref;
      if (deleteDialogTitle) {
        deleteDialogTitle.textContent = `Delete this task: ${ref}?`;
      }
      if (deleteDialogDescription) {
        deleteDialogDescription.textContent = `You are about to delete “${title}” (${ref}).\nThis action cannot be undone.`;
      }
      bootstrap?.Modal.getOrCreateInstance(deleteDialog).show();
      return;
    }
    if (target.closest("[data-moo-task-edit]")) {
      const row = findRowFromAction(target);
      if (!row) {
        return;
      }
      closeRowMenu(target);
      openEditSheet(row);
      return;
    }
    if (target.closest("[data-moo-task-copy]")) {
      const row = findRowFromAction(target);
      if (!row) {
        return;
      }
      const link = `${windowRoot.location.href.split("#")[0]}#${row.id}`;
      windowRoot.navigator.clipboard?.writeText(link).catch(() => {});
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

  form.addEventListener("submit", onSubmit);
  documentRoot.addEventListener("click", onPageClick);
  sheet.addEventListener("show.bs.offcanvas", onSheetShow);
  sheet.addEventListener("hidden.bs.offcanvas", onSheetHidden);
  deleteConfirm.addEventListener("click", onDeleteConfirm);
  deleteDialog.addEventListener("hidden.bs.modal", onDeleteDialogHidden);

  const dispose = () => {
    form.removeEventListener("submit", onSubmit);
    documentRoot.removeEventListener("click", onPageClick);
    sheet.removeEventListener("show.bs.offcanvas", onSheetShow);
    sheet.removeEventListener("hidden.bs.offcanvas", onSheetHidden);
    deleteConfirm.removeEventListener("click", onDeleteConfirm);
    deleteDialog.removeEventListener("hidden.bs.modal", onDeleteDialogHidden);
    // reinitTable() leaves a live DataTable behind; release it so a
    // disposed example page carries no orphaned listeners.
    DataTable.getOrCreateInstance(tableRoot).dispose();
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

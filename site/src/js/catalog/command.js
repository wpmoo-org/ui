const states = new WeakMap();
const normalize = (value) => value.trim().toLowerCase();

export function initCommand(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const modal = root.getElementById?.("catalog-command") || root.querySelector("#catalog-command");
  const input = modal?.querySelector("input[type='search']");
  const items = Array.from(modal?.querySelectorAll("[data-moo-command-item]") || []);
  const empty = modal?.querySelector(".moo-catalog__command-empty");
  const groups = Array.from(modal?.querySelectorAll("[data-moo-command-group]") || []);
  const searchTrigger = root.querySelector(".moo-catalog__search-trigger");
  const list = modal?.querySelector('[role="listbox"]');
  const listeners = [];
  let active = -1;
  let modalInstance = null;

  const listen = (target, type, handler) => {
    target?.addEventListener(type, handler);
    if (target) {
      listeners.push({ target, type, handler });
    }
  };
  if (list && !list.id) {
    list.id = "catalog-command-list";
  }
  items.forEach((item, index) => {
    if (!item.id) {
      item.id = `catalog-command-item-${index}`;
    }
    item.setAttribute("aria-selected", "false");
  });
  if (input && list) {
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-controls", list.id);
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
  }

  const visibleItems = () => items.filter((item) => !item.hidden);
  const setActive = (index) => {
    const visible = visibleItems();
    items.forEach((item) => {
      item.classList.remove("active");
      item.setAttribute("aria-selected", "false");
    });
    if (visible.length === 0) {
      active = -1;
      input?.removeAttribute("aria-activedescendant");
      return;
    }
    active = ((index % visible.length) + visible.length) % visible.length;
    const current = visible[active];
    current.classList.add("active");
    current.setAttribute("aria-selected", "true");
    current.scrollIntoView({ block: "nearest" });
    input?.setAttribute("aria-activedescendant", current.id);
  };
  const filter = (query = input?.value || "") => {
    const needle = normalize(query);
    let count = 0;
    items.forEach((item) => {
      const matches = !needle || normalize(item.textContent).includes(needle);
      item.hidden = !matches;
      count += matches ? 1 : 0;
    });
    groups.forEach((group) => {
      group.hidden = !Array.from(
        group.querySelectorAll("[data-moo-command-item]")
      ).some((item) => !item.hidden);
    });
    if (empty) {
      empty.hidden = count !== 0;
    }
    setActive(0);
  };
  const open = () => {
    const Modal = view.bootstrap?.Modal;
    if (modal && Modal) {
      modalInstance = Modal.getOrCreateInstance(modal);
      modalInstance.show();
    }
  };

  listen(searchTrigger, "click", open);
  listen(input, "input", () => filter());
  listen(input, "keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(active + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(active - 1);
    } else if (event.key === "Enter") {
      const target = visibleItems()[active];
      if (target) {
        event.preventDefault();
        view.location.href = target.getAttribute("href");
      }
    }
  });
  listen(modal, "shown.bs.modal", () => {
    input?.setAttribute("aria-expanded", "true");
    input?.focus();
    input?.select();
    filter();
  });
  listen(modal, "hidden.bs.modal", () => {
    input?.setAttribute("aria-expanded", "false");
    input?.removeAttribute("aria-activedescendant");
    if (input) {
      input.value = "";
    }
    filter("");
  });
  listen(root, "keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      open();
    }
  });

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    modalInstance?.dispose();
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

const states = new WeakMap();
const VIEWS = ["grid", "list"];

// Grid/list view toggle shared by the Examples and Components index pages.
// data-moo-catalog-view holds the current view (the CSS hook the list
// layout reads); the radio group name comes from the inputs themselves and
// names the localStorage key ("moo:<name>"), so each index keeps its own
// persisted choice.
export function initCatalogViewToggle(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const container = root.querySelector("[data-moo-catalog-view]");
  const listeners = [];

  if (container) {
    const view = root.defaultView || root.ownerDocument?.defaultView;
    const firstInput = container.querySelector('input[type="radio"][name]');
    const name = firstInput?.name || "catalog-view";
    const storageKey = `moo:${name}`;
    const inputs = Array.from(
      container.querySelectorAll(`input[name="${name}"]`)
    );
    const listen = (target, type, handler) => {
      target.addEventListener(type, handler);
      listeners.push({ target, type, handler });
    };

    const applyView = (value) => {
      container.dataset.mooCatalogView = value;
      inputs.forEach((input) => {
        input.checked = input.value === value;
      });
    };

    let stored = null;
    try {
      stored = view.localStorage.getItem(storageKey);
    } catch (_) {
      /* Storage can be unavailable in restricted browsing contexts. */
    }
    if (VIEWS.includes(stored)) {
      applyView(stored);
    }

    inputs.forEach((input) => {
      listen(input, "change", () => {
        if (!input.checked) {
          return;
        }
        applyView(input.value);
        try {
          view.localStorage.setItem(storageKey, input.value);
        } catch (_) {
          /* Storage is best-effort. */
        }
      });
    });
  }

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

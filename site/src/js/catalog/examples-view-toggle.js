const states = new WeakMap();
const VIEW_STORAGE_KEY = "moo:examples-view";
const VIEWS = ["grid", "list"];

export function initExamplesViewToggle(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const container = root.querySelector("[data-moo-examples-view]");
  const listeners = [];

  if (container) {
    const view = root.defaultView || root.ownerDocument?.defaultView;
    const inputs = Array.from(
      container.querySelectorAll('input[name="examples-view"]')
    );
    const listen = (target, type, handler) => {
      target.addEventListener(type, handler);
      listeners.push({ target, type, handler });
    };

    const applyView = (value) => {
      container.dataset.mooExamplesView = value;
      inputs.forEach((input) => {
        input.checked = input.value === value;
      });
    };

    let stored = null;
    try {
      stored = view.localStorage.getItem(VIEW_STORAGE_KEY);
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
          view.localStorage.setItem(VIEW_STORAGE_KEY, input.value);
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

const states = new WeakMap();
const THEME_STORAGE_KEY = "moo:theme";

function effectiveTheme(preference, view) {
  if (preference === "system") {
    return view.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return preference === "dark" ? "dark" : "light";
}

// Global settings panel (Phase 6): wires the System/Light/Dark theme radios
// and the Reset affordance. The stored moo:theme preference is the shared
// source of truth with theme.js, so choosing here updates the whole site the
// same way the navbar toggle does; opening the sheet re-syncs the radios to
// whatever the current preference is (including changes made via the navbar
// toggle).
export function initSettingsPanel(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const sheet = root.querySelector("#catalog-settings");
  const listeners = [];

  if (sheet) {
    const documentElement = root.documentElement || root.ownerDocument?.documentElement;
    const view = root.defaultView || root.ownerDocument?.defaultView;
    const themeInputs = Array.from(
      sheet.querySelectorAll("[data-moo-settings-theme]")
    );
    const reset = sheet.querySelector("[data-moo-settings-reset]");
    const listen = (target, type, handler) => {
      target?.addEventListener(type, handler);
      if (target) {
        listeners.push({ target, type, handler });
      }
    };

    const readPreference = () => {
      try {
        const stored = view.localStorage.getItem(THEME_STORAGE_KEY);
        if (stored === "dark" || stored === "light" || stored === "system") {
          return stored;
        }
      } catch (_) {
        /* Storage can be unavailable in restricted browsing contexts. */
      }
      return "light";
    };

    const applyPreference = (preference) => {
      documentElement.dataset.bsTheme = effectiveTheme(preference, view);
      try {
        view.localStorage.setItem(THEME_STORAGE_KEY, preference);
      } catch (_) {
        /* Storage is best-effort. */
      }
      themeInputs.forEach((input) => {
        input.checked = input.value === preference;
      });
    };

    themeInputs.forEach((input) => {
      listen(input, "change", () => {
        if (input.checked) {
          applyPreference(input.value);
        }
      });
    });

    listen(reset, "click", () => {
      try {
        view.localStorage.removeItem(THEME_STORAGE_KEY);
      } catch (_) {
        /* Storage is best-effort. */
      }
      documentElement.dataset.bsTheme = "light";
      themeInputs.forEach((input) => {
        input.checked = input.value === "light";
      });
    });

    // Reflect the current preference whenever the sheet opens, so a choice
    // made through the navbar toggle shows up here too.
    listen(sheet, "show.bs.offcanvas", () => {
      const preference = readPreference();
      themeInputs.forEach((input) => {
        input.checked = input.value === preference;
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

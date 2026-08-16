const states = new WeakMap();
const THEME_STORAGE_KEY = "moo:theme";
const DIRECTION_STORAGE_KEY = "moo:direction";
const SIDEBAR_STORAGE_KEY = "moo:sidebar-variant";

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
    const directionInputs = Array.from(
      sheet.querySelectorAll("[data-moo-settings-direction]")
    );
    const sidebarInputs = Array.from(
      sheet.querySelectorAll("[data-moo-settings-sidebar]")
    );
    const reset = sheet.querySelector("[data-moo-settings-reset]");
    const listen = (target, type, handler) => {
      target?.addEventListener(type, handler);
      if (target) {
        listeners.push({ target, type, handler });
      }
    };

    // The navbar toggle only has light/dark states; keep its sun/moon icon
    // and aria-label in step with the effective theme (which resolves
    // "system" to the OS preference) when the panel changes it.
    const syncThemeButton = () => {
      const button = root.querySelector(
        "[data-moo-theme], .moo-catalog__theme-toggle"
      );
      const theme = documentElement.dataset.bsTheme || "light";
      button?.setAttribute(
        "aria-label",
        theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
      );
      button?.querySelectorAll("[data-moo-theme-icon]").forEach((icon) => {
        icon.classList.toggle("d-none", icon.dataset.mooThemeIcon !== theme);
      });
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
      // The default is System: follow the OS preference.
      return "system";
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
      syncThemeButton();
    };

    themeInputs.forEach((input) => {
      listen(input, "change", () => {
        if (input.checked) {
          applyPreference(input.value);
        }
      });
    });

    // Phase 7: the LTR/RTL picker flips the document direction live and
    // persists it under moo:direction so it survives navigation.
    const readDirection = () => {
      try {
        const stored = view.localStorage.getItem(DIRECTION_STORAGE_KEY);
        if (stored === "ltr" || stored === "rtl") {
          return stored;
        }
      } catch (_) {
        /* Storage can be unavailable in restricted browsing contexts. */
      }
      return "ltr";
    };
    const applyDirection = (direction) => {
      documentElement.dir = direction;
      try {
        view.localStorage.setItem(DIRECTION_STORAGE_KEY, direction);
      } catch (_) {
        /* Storage is best-effort. */
      }
      directionInputs.forEach((input) => {
        input.checked = input.value === direction;
      });
    };
    directionInputs.forEach((input) => {
      listen(input, "change", () => {
        if (input.checked) {
          applyDirection(input.value);
        }
      });
    });

    // Phase 8: the Sidebar picker switches the catalog layout's data-variant
    // live (the sidebar SCSS keys off it) and persists the choice.
    const sidebar = root.querySelector("#catalog-sidebar");
    const readSidebarVariant = () => {
      try {
        const stored = view.localStorage.getItem(SIDEBAR_STORAGE_KEY);
        if (stored === "sidebar" || stored === "inset" || stored === "floating") {
          return stored;
        }
      } catch (_) {
        /* Storage can be unavailable in restricted browsing contexts. */
      }
      return "sidebar";
    };
    const applySidebarVariant = (variant) => {
      if (sidebar) {
        sidebar.dataset.variant = variant;
      }
      try {
        view.localStorage.setItem(SIDEBAR_STORAGE_KEY, variant);
      } catch (_) {
        /* Storage is best-effort. */
      }
      sidebarInputs.forEach((input) => {
        input.checked = input.value === variant;
      });
    };
    sidebarInputs.forEach((input) => {
      listen(input, "change", () => {
        if (input.checked) {
          applySidebarVariant(input.value);
        }
      });
    });

    listen(reset, "click", () => {
      try {
        view.localStorage.removeItem(THEME_STORAGE_KEY);
        view.localStorage.removeItem(DIRECTION_STORAGE_KEY);
        view.localStorage.removeItem(SIDEBAR_STORAGE_KEY);
      } catch (_) {
        /* Storage is best-effort. */
      }
      documentElement.dataset.bsTheme = effectiveTheme("system", view);
      documentElement.dir = "ltr";
      themeInputs.forEach((input) => {
        input.checked = input.value === "system";
      });
      directionInputs.forEach((input) => {
        input.checked = input.value === "ltr";
      });
      if (sidebar) {
        sidebar.dataset.variant = "sidebar";
      }
      sidebarInputs.forEach((input) => {
        input.checked = input.value === "sidebar";
      });
      syncThemeButton();
    });

    // Reflect the current preferences whenever the sheet opens, so choices
    // made through the navbar toggle show up here too.
    listen(sheet, "show.bs.offcanvas", () => {
      const preference = readPreference();
      themeInputs.forEach((input) => {
        input.checked = input.value === preference;
      });
      const direction = readDirection();
      directionInputs.forEach((input) => {
        input.checked = input.value === direction;
      });
      const sidebarVariant = readSidebarVariant();
      sidebarInputs.forEach((input) => {
        input.checked = input.value === sidebarVariant;
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

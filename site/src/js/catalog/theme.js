const states = new WeakMap();
const THEME_STORAGE_KEY = "moo:theme";

function prefersDark(view) {
  return Boolean(view.matchMedia?.("(prefers-color-scheme: dark)").matches);
}

function resolveTheme(preference, view) {
  if (preference === "system") {
    return prefersDark(view) ? "dark" : "light";
  }
  return preference === "dark" ? "dark" : "light";
}

export function initTheme(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const documentElement = root.documentElement || root.ownerDocument?.documentElement;
  const view = root.defaultView || root.ownerDocument?.defaultView;
  const themeButton = root.querySelector(
    "[data-moo-theme], .moo-catalog__theme-toggle"
  );
  const themeIcons = Array.from(
    themeButton?.querySelectorAll("[data-moo-theme-icon]") || []
  );
  const listeners = [];
  const listen = (target, type, handler) => {
    target?.addEventListener(type, handler);
    if (target) {
      listeners.push({ target, type, handler });
    }
  };

  // The stored preference is the single source of truth (the settings panel
  // writes the same key), so the OS-color listener re-reads it each time
  // instead of tracking its own copy -- both surfaces stay in sync without
  // shared state.
  const readPreference = () => {
    try {
      const stored = view.localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === "dark" || stored === "light" || stored === "system") {
        return stored;
      }
    } catch (_) {
      /* Storage can be unavailable in restricted browsing contexts. */
    }
    // The default is System: follow the OS preference until the visitor
    // chooses an explicit theme.
    return "system";
  };

  const updateThemeButton = () => {
    const theme = documentElement.dataset.bsTheme || "light";
    themeButton?.setAttribute(
      "aria-label",
      theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
    );
    themeIcons.forEach((icon) => {
      icon.classList.toggle("d-none", icon.dataset.mooThemeIcon !== theme);
    });
  };

  const applyPreference = (preference) => {
    documentElement.dataset.bsTheme = resolveTheme(preference, view);
    updateThemeButton();
  };

  applyPreference(readPreference());

  const media = view.matchMedia ? view.matchMedia("(prefers-color-scheme: dark)") : null;
  listen(media, "change", () => {
    if (readPreference() === "system") {
      documentElement.dataset.bsTheme = resolveTheme("system", view);
      updateThemeButton();
    }
  });

  listen(themeButton, "click", () => {
    const theme = documentElement.dataset.bsTheme === "dark" ? "light" : "dark";
    documentElement.dataset.bsTheme = theme;
    try {
      view.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (_) {
      /* Storage is best-effort. */
    }
    updateThemeButton();
  });

  updateThemeButton();
  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

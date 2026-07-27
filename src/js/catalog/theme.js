const states = new WeakMap();
const THEME_STORAGE_KEY = "moo:theme";

export function initTheme(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const documentElement = root.documentElement || root.ownerDocument?.documentElement;
  const view = root.defaultView || root.ownerDocument?.defaultView;
  const themeButton = root.querySelector(
    "[data-moo-theme], .moo-catalog__theme-toggle"
  );
  const directionButton = root.querySelector(
    "[data-moo-direction], .moo-catalog__direction-toggle"
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

  try {
    const stored = view.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light") {
      documentElement.dataset.bsTheme = stored;
    }
  } catch (_) {
    /* Storage can be unavailable in restricted browsing contexts. */
  }

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

  listen(directionButton, "click", () => {
    const direction = documentElement.dir === "rtl" ? "ltr" : "rtl";
    documentElement.dir = direction;
    directionButton.textContent = direction === "rtl" ? "LTR" : "RTL";
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

import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  THEME_BUILDER_DEFAULTS,
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./theme-builder-schema.js";

const states = new WeakMap();
const THEME_STORAGE_KEY = "moo:theme";
const DIRECTION_STORAGE_KEY = "moo:direction";
const SIDEBAR_STORAGE_KEY = "moo:sidebar-variant";
const BUILDER_STORAGE_KEY = "moo:theme-builder";

const BUILDER_SELECTORS = {
  style: "[data-moo-catalog-theme-builder-style]",
  baseColor: "[data-moo-catalog-theme-builder-base-color]",
  themeColor: "[data-moo-catalog-theme-builder-theme-color]",
  chartColor: "[data-moo-catalog-theme-builder-chart-color]",
  headingFont: "[data-moo-catalog-theme-builder-heading-font]",
  bodyFont: "[data-moo-catalog-theme-builder-body-font]",
  radius: "[data-moo-catalog-theme-builder-radius]",
};

const BUILDER_DATASETS = {
  style: "mooCatalogThemeBuilderStyle",
  baseColor: "mooCatalogThemeBuilderBaseColor",
  themeColor: "mooCatalogThemeBuilderThemeColor",
};

const BUILDER_OPTION_SELECTOR = "[data-moo-catalog-theme-builder-option]";
const BUILDER_VALUE_SELECTOR = "[data-moo-catalog-theme-builder-value]";

function effectiveTheme(preference, view) {
  if (preference === "system") {
    return view.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return preference === "dark" ? "dark" : "light";
}

function normalizedBuilderPreference(candidate = {}) {
  return normalizeThemeBuilderState(candidate);
}

function applyTokenSet(style, tokenNames, tokenValues = {}) {
  if (!style) return;
  tokenNames.forEach((token) => {
    style.removeProperty(token);
  });
  Object.entries(tokenValues).forEach(([token, value]) => {
    style.setProperty(token, value);
  });
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
  const cleanups = [];

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
    const builderControls = Object.fromEntries(
      Object.entries(BUILDER_SELECTORS).map(([key, selector]) => {
        const fieldRoot = sheet.querySelector(selector);
        return [
          key,
          {
            options: Array.from(
              fieldRoot?.querySelectorAll(BUILDER_OPTION_SELECTOR) || []
            ),
            value: fieldRoot?.querySelector(BUILDER_VALUE_SELECTOR),
            swatch: fieldRoot?.querySelector(
              "[data-moo-catalog-theme-builder-trigger-swatch]"
            ),
          },
        ];
      })
    );
    const reset = sheet.querySelector("[data-moo-settings-reset]");
    let builderTransitionGeneration = 0;
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
      applyBuilderPreference(readBuilderPreference(), { persist: false });
    };

    themeInputs.forEach((input) => {
      listen(input, "change", () => {
        if (input.checked) {
          applyPreference(input.value);
        }
      });
    });

    const syncBuilderControls = (preference) => {
      Object.entries(builderControls).forEach(([key, control]) => {
        let selectedLabel = preference[key];
        let selectedSwatch = "";
        control.options.forEach((option) => {
          const isSelected =
            option.dataset.mooCatalogThemeBuilderOption === preference[key];
          option.classList.toggle("active", isSelected);
          option.setAttribute("aria-pressed", String(isSelected));
          if (isSelected) {
            selectedLabel =
              option
                .querySelector("[data-moo-catalog-theme-builder-option-label]")
                ?.textContent?.trim() || selectedLabel;
            selectedSwatch = option.dataset.mooCatalogThemeBuilderSwatch || "";
          }
        });
        if (control.value) {
          control.value.textContent = selectedLabel;
        }
        if (control.swatch) {
          if (selectedSwatch) {
            control.swatch.dataset.mooCatalogThemeBuilderTriggerSwatch =
              selectedSwatch;
          } else {
            delete control.swatch.dataset.mooCatalogThemeBuilderTriggerSwatch;
          }
        }
      });
    };

    const readBuilderPreference = () => {
      try {
        const raw = view.localStorage.getItem(BUILDER_STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : {};
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          const normalized = normalizedBuilderPreference(parsed);
          if (raw && JSON.stringify(parsed) !== JSON.stringify(normalized)) {
            persistBuilderPreference(normalized);
          }
          return normalized;
        }
      } catch (_) {
        /* Storage can be unavailable or contain stale JSON. */
      }
      return normalizedBuilderPreference();
    };

    const persistBuilderPreference = (preference) => {
      try {
        view.localStorage.setItem(
          BUILDER_STORAGE_KEY,
          JSON.stringify(preference)
        );
      } catch (_) {
        /* Storage is best-effort. */
      }
    };

    const withBuilderTransitionSuppressed = (work) => {
      documentElement.dataset.mooCatalogThemeBuilderUpdating = "true";
      builderTransitionGeneration += 1;
      const generation = builderTransitionGeneration;
      const clear = () => {
        if (generation === builderTransitionGeneration) {
          delete documentElement.dataset.mooCatalogThemeBuilderUpdating;
        }
      };
      const afterPaint =
        typeof view.requestAnimationFrame === "function"
          ? (callback) =>
              view.requestAnimationFrame(() => {
                view.requestAnimationFrame(callback);
              })
          : (callback) => {
              const setTimeoutFallback =
                typeof view.setTimeout === "function"
                  ? view.setTimeout.bind(view)
                  : typeof globalThis.setTimeout === "function"
                    ? globalThis.setTimeout.bind(globalThis)
                    : null;
              if (setTimeoutFallback) {
                setTimeoutFallback(callback, 32);
              } else {
                callback();
              }
            };

      const result = work();
      afterPaint(clear);
      return result;
    };

    const applyBuilderPreference = (candidate, { persist = true } = {}) => {
      const preference = normalizedBuilderPreference(candidate);
      withBuilderTransitionSuppressed(() => {
        Object.entries(BUILDER_DATASETS).forEach(([key, datasetKey]) => {
          if (preference[key] === THEME_BUILDER_DEFAULTS[key]) {
            delete documentElement.dataset[datasetKey];
          } else {
            documentElement.dataset[datasetKey] = preference[key];
          }
        });
        applyTokenSet(
          documentElement.style,
          PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
          resolveThemeBuilderTokens(preference, {
            theme: documentElement.dataset.bsTheme,
          })
        );
        syncBuilderControls(preference);
      });
      if (persist) {
        persistBuilderPreference(preference);
      }
      return preference;
    };

    Object.entries(builderControls).forEach(([key, control]) => {
      control.options.forEach((option) => {
        listen(option, "click", () => {
          applyBuilderPreference({
            ...readBuilderPreference(),
            [key]: option.dataset.mooCatalogThemeBuilderOption,
          });
        });
      });
    });

    applyBuilderPreference(readBuilderPreference(), { persist: false });

    if (typeof view.MutationObserver === "function") {
      const observer = new view.MutationObserver((mutations) => {
        if (
          mutations.some(
            (mutation) => mutation.attributeName === "data-bs-theme"
          )
        ) {
          applyBuilderPreference(readBuilderPreference(), { persist: false });
          syncThemeButton();
        }
      });
      observer.observe(documentElement, {
        attributes: true,
        attributeFilter: ["data-bs-theme"],
      });
      cleanups.push(() => observer.disconnect());
    }

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
        view.localStorage.removeItem(BUILDER_STORAGE_KEY);
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
      applyBuilderPreference(THEME_BUILDER_DEFAULTS, { persist: false });
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
      syncBuilderControls(readBuilderPreference());
    });
  }

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    cleanups.forEach((cleanup) => cleanup());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

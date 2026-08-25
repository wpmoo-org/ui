const states = new WeakMap();
const THEME_STORAGE_KEY = "moo:theme";
const DIRECTION_STORAGE_KEY = "moo:direction";
const SIDEBAR_STORAGE_KEY = "moo:sidebar-variant";
const BUILDER_STORAGE_KEY = "moo:theme-builder";

const BUILDER_DEFAULTS = {
  style: "default",
  baseColor: "neutral",
  chartPalette: "default",
  headingFont: "default",
  bodyFont: "default",
  radius: "default",
};

const BUILDER_SELECTORS = {
  style: "[data-moo-catalog-theme-builder-style]",
  baseColor: "[data-moo-catalog-theme-builder-base-color]",
  chartPalette: "[data-moo-catalog-theme-builder-chart-palette]",
  headingFont: "[data-moo-catalog-theme-builder-heading-font]",
  bodyFont: "[data-moo-catalog-theme-builder-body-font]",
  radius: "[data-moo-catalog-theme-builder-radius]",
};

const BUILDER_DATASETS = {
  style: "mooCatalogThemeBuilderStyle",
  baseColor: "mooCatalogThemeBuilderBaseColor",
};

const BUILDER_OPTION_SELECTOR = "[data-moo-catalog-theme-builder-option]";
const BUILDER_VALUE_SELECTOR = "[data-moo-catalog-theme-builder-value]";

const BASE_COLOR_TOKENS = ["--bs-primary", "--moo-primary", "--moo-ring"];
const CHART_PALETTE_TOKENS = [
  "--moo-chart-1",
  "--moo-chart-2",
  "--moo-chart-3",
  "--moo-chart-4",
  "--moo-chart-5",
];
const FONT_TOKENS = [
  "--bs-body-font-family",
  "--moo-catalog-font-family",
  "--moo-heading-font-family",
];
const RADIUS_TOKENS = [
  "--bs-border-radius",
  "--bs-border-radius-sm",
  "--bs-border-radius-lg",
  "--bs-border-radius-xl",
  "--bs-border-radius-xxl",
];

const BASE_COLOR_PRESETS = {
  neutral: {},
  blue: {
    "--bs-primary": "rgb(37, 99, 235)",
    "--moo-primary": "rgb(37, 99, 235)",
    "--moo-ring": "rgb(96, 165, 250)",
  },
  emerald: {
    "--bs-primary": "rgb(5, 150, 105)",
    "--moo-primary": "rgb(5, 150, 105)",
    "--moo-ring": "rgb(52, 211, 153)",
  },
  violet: {
    "--bs-primary": "rgb(124, 58, 237)",
    "--moo-primary": "rgb(124, 58, 237)",
    "--moo-ring": "rgb(167, 139, 250)",
  },
};

const CHART_PALETTE_PRESETS = {
  default: {},
  pastel: {
    "--moo-chart-1": "rgb(103, 169, 232)",
    "--moo-chart-2": "rgb(118, 187, 170)",
    "--moo-chart-3": "rgb(246, 198, 110)",
    "--moo-chart-4": "rgb(198, 157, 232)",
    "--moo-chart-5": "rgb(238, 135, 142)",
  },
  vivid: {
    "--moo-chart-1": "rgb(37, 99, 235)",
    "--moo-chart-2": "rgb(5, 150, 105)",
    "--moo-chart-3": "rgb(217, 119, 6)",
    "--moo-chart-4": "rgb(124, 58, 237)",
    "--moo-chart-5": "rgb(225, 29, 72)",
  },
};

const FONT_PRESETS = {
  headingFont: {
    default: {},
    geist: { "--moo-heading-font-family": '"Geist", var(--bs-body-font-family)' },
    system: { "--moo-heading-font-family": 'system-ui, -apple-system, "Segoe UI", sans-serif' },
  },
  bodyFont: {
    default: {},
    geist: {
      "--bs-body-font-family": '"Geist", system-ui, -apple-system, "Segoe UI", sans-serif',
      "--moo-catalog-font-family": '"Geist"',
    },
    system: {
      "--bs-body-font-family": 'system-ui, -apple-system, "Segoe UI", sans-serif',
      "--moo-catalog-font-family": "system-ui",
    },
  },
};

const RADIUS_PRESETS = {
  default: {},
  compact: {
    "--bs-border-radius": "0.25rem",
    "--bs-border-radius-sm": "0.1875rem",
    "--bs-border-radius-lg": "0.375rem",
    "--bs-border-radius-xl": "0.5rem",
    "--bs-border-radius-xxl": "0.75rem",
  },
  large: {
    "--bs-border-radius": "0.75rem",
    "--bs-border-radius-sm": "0.5rem",
    "--bs-border-radius-lg": "1rem",
    "--bs-border-radius-xl": "1.25rem",
    "--bs-border-radius-xxl": "1.5rem",
  },
};

const BUILDER_PRESETS = {
  style: new Set(["default", "soft", "solid", "nova"]),
  baseColor: new Set(Object.keys(BASE_COLOR_PRESETS)),
  chartPalette: new Set(Object.keys(CHART_PALETTE_PRESETS)),
  headingFont: new Set(Object.keys(FONT_PRESETS.headingFont)),
  bodyFont: new Set(Object.keys(FONT_PRESETS.bodyFont)),
  radius: new Set(Object.keys(RADIUS_PRESETS)),
};

function effectiveTheme(preference, view) {
  if (preference === "system") {
    return view.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return preference === "dark" ? "dark" : "light";
}

function normalizedBuilderPreference(candidate = {}) {
  return Object.fromEntries(
    Object.entries(BUILDER_DEFAULTS).map(([key, fallback]) => {
      const value = candidate[key];
      return [key, BUILDER_PRESETS[key].has(value) ? value : fallback];
    })
  );
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
          return normalizedBuilderPreference(parsed);
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
          if (preference[key] === BUILDER_DEFAULTS[key]) {
            delete documentElement.dataset[datasetKey];
          } else {
            documentElement.dataset[datasetKey] = preference[key];
          }
        });
        applyTokenSet(
          documentElement.style,
          BASE_COLOR_TOKENS,
          BASE_COLOR_PRESETS[preference.baseColor]
        );
        applyTokenSet(
          documentElement.style,
          CHART_PALETTE_TOKENS,
          CHART_PALETTE_PRESETS[preference.chartPalette]
        );
        applyTokenSet(
          documentElement.style,
          RADIUS_TOKENS,
          RADIUS_PRESETS[preference.radius]
        );
        applyTokenSet(
          documentElement.style,
          FONT_TOKENS,
          {
            ...FONT_PRESETS.headingFont[preference.headingFont],
            ...FONT_PRESETS.bodyFont[preference.bodyFont],
          }
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
      applyBuilderPreference(BUILDER_DEFAULTS, { persist: false });
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
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

import {
  PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
  THEME_BUILDER_DEFAULTS,
  normalizeThemeBuilderState,
  resolveThemeBuilderTokens,
} from "./theme-builder-schema.js";
import {
  findThemeOwner,
  isDocumentOwner,
  ownerStorageKey,
  readOwnerPreference,
  resolveOwnerDirection,
  resolveOwnerTheme,
  setOwnerDirection,
  setOwnerTheme,
} from "../../../../src/js/theme-owner.js";

const states = new WeakMap();
const SIDEBAR_STORAGE_KEY = "moo:sidebar-variant";
const BUILDER_STORAGE_KEY = "moo:theme-builder";
let themeBuilderOwnerSequence = 0;

const BUILDER_SELECTORS = {
  baseColor: "[data-moo-catalog-theme-builder-base-color]",
  themeColor: "[data-moo-catalog-theme-builder-theme-color]",
  chartColor: "[data-moo-catalog-theme-builder-chart-color]",
  headingFont: "[data-moo-catalog-theme-builder-heading-font]",
  bodyFont: "[data-moo-catalog-theme-builder-body-font]",
  radius: "[data-moo-catalog-theme-builder-radius]",
};

const BUILDER_DATASETS = {
  baseColor: "mooCatalogThemeBuilderBaseColor",
  themeColor: "mooCatalogThemeBuilderThemeColor",
};

const BUILDER_OPTION_SELECTOR = "[data-moo-catalog-theme-builder-option]";
const BUILDER_VALUE_SELECTOR = "[data-moo-catalog-theme-builder-value]";
const BUILDER_PREVIEW_KEYS = new Set(["baseColor", "themeColor", "chartColor"]);

function normalizedBuilderPreference(candidate = {}) {
  return normalizeThemeBuilderState(candidate);
}

function isDefaultBuilderPreference(preference) {
  return Object.entries(THEME_BUILDER_DEFAULTS).every(
    ([key, value]) => preference[key] === value
  );
}

function generatedOwnerMarker(owner, view) {
  const existing = owner?.dataset?.mooThemeBuilderOwner;
  if (existing) return existing;

  const identifier =
    view?.crypto?.randomUUID?.() ||
    globalThis.crypto?.randomUUID?.() ||
    `local-${++themeBuilderOwnerSequence}`;
  const marker = `moo-owner-${identifier}`;
  owner.dataset.mooThemeBuilderOwner = marker;
  return marker;
}

function findThemeBuilderStyle(owner) {
  let style = owner?.querySelector?.(
    ":scope > style[data-moo-theme-builder-style]"
  );
  if (!style) {
    style = Array.from(owner?.children || []).find((child) =>
      child.matches?.("style[data-moo-theme-builder-style]")
    );
  }
  return style || null;
}

function ensureThemeBuilderStyle(owner) {
  let style = findThemeBuilderStyle(owner);
  if (style || !owner?.ownerDocument?.createElement) return style || null;

  style = owner.ownerDocument.createElement("style");
  style.dataset.mooThemeBuilderStyle = "";
  owner.append(style);
  return style;
}

function applyTokenStyle(owner, view, tokenNames, tokenValues = {}) {
  const allowedTokens = new Set(tokenNames);
  const declarations = Object.entries(tokenValues)
    .filter(([token]) => allowedTokens.has(token))
    .map(([token, value]) => `  ${token}: ${value};`)
    .join("\n");
  if (!declarations) {
    const existing = findThemeBuilderStyle(owner);
    if (existing) existing.textContent = "";
    return;
  }

  const style = ensureThemeBuilderStyle(owner);
  if (!style) return;

  const marker = generatedOwnerMarker(owner, view);
  const escape = view?.CSS?.escape || globalThis.CSS?.escape;
  const escapedMarker = escape ? escape(marker) : marker;
  style.textContent =
    `[data-moo-theme-builder-owner="${escapedMarker}"] {\n${declarations}\n}`;
}

function writeOwnerPreference(owner, axis, value, view) {
  const key = ownerStorageKey(owner, axis);
  if (!key) return;
  try {
    view?.localStorage?.setItem(key, value);
  } catch (_) {
    /* Storage can be unavailable in restricted browsing contexts. */
  }
}

function removeOwnerPreference(owner, axis, view) {
  const key = ownerStorageKey(owner, axis);
  if (!key) return;
  try {
    view?.localStorage?.removeItem(key);
  } catch (_) {
    /* Storage can be unavailable in restricted browsing contexts. */
  }
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

  const owner = sheet && findThemeOwner(sheet);

  if (sheet && owner) {
    const view =
      owner.ownerDocument?.defaultView ||
      root.defaultView ||
      root.ownerDocument?.defaultView;
    const builderStorageKey = isDocumentOwner(owner)
      ? BUILDER_STORAGE_KEY
      : null;
    const serverTheme = owner.dataset.bsTheme;
    const serverDirection = resolveOwnerDirection(owner, null) || "ltr";
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
            root: fieldRoot,
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
    let builderPreference = null;
    let builderPreferenceHasOverrides = false;
    let builderPreview = null;
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
      const theme = owner.dataset.bsTheme || "light";
      Array.from(
        root.querySelectorAll?.(
          "[data-moo-theme], .moo-catalog__theme-toggle"
        ) || []
      )
        .filter((button) => findThemeOwner(button) === owner)
        .forEach((button) => {
          button.setAttribute?.(
            "aria-label",
            theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
          );
        });
    };

    const readPreference = () => readOwnerPreference(owner, "theme") || "system";

    const applyPreference = (preference) => {
      setOwnerTheme(owner, resolveOwnerTheme(owner, preference, view));
      writeOwnerPreference(owner, "theme", preference, view);
      themeInputs.forEach((input) => {
        input.checked = input.value === preference;
      });
      syncThemeButton();
      applyBuilderPreference(readBuilderPreference(), {
        persist: false,
        clearDefaultTokens: builderPreferenceHasOverrides,
      });
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
      if (builderPreference) {
        return builderPreference;
      }
      if (!builderStorageKey) {
        builderPreference = normalizedBuilderPreference();
        builderPreferenceHasOverrides = false;
        return builderPreference;
      }
      try {
        const raw = view.localStorage.getItem(builderStorageKey);
        const parsed = raw ? JSON.parse(raw) : null;
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
          const normalized = normalizedBuilderPreference(parsed);
          const hasOverrides = !isDefaultBuilderPreference(normalized);
          if (hasOverrides && JSON.stringify(parsed) !== JSON.stringify(normalized)) {
            persistBuilderPreference(normalized);
          } else if (!hasOverrides) {
            removeBuilderPreferenceStorage();
          }
          builderPreferenceHasOverrides = hasOverrides;
          builderPreference = normalized;
          return normalized;
        }
      } catch (_) {
        /* Storage can be unavailable or contain stale JSON. */
      }
      builderPreference = normalizedBuilderPreference();
      builderPreferenceHasOverrides = false;
      return builderPreference;
    };

    const persistBuilderPreference = (preference) => {
      if (!builderStorageKey) return;
      try {
        view.localStorage.setItem(
          builderStorageKey,
          JSON.stringify(preference)
        );
      } catch (_) {
        /* Storage is best-effort. */
      }
    };

    const removeBuilderPreferenceStorage = () => {
      if (!builderStorageKey) return;
      try {
        view.localStorage.removeItem(builderStorageKey);
      } catch (_) {
        /* Storage is best-effort. */
      }
    };

    const withBuilderTransitionSuppressed = (work) => {
      owner.dataset.mooCatalogThemeBuilderUpdating = "true";
      builderTransitionGeneration += 1;
      const generation = builderTransitionGeneration;
      const clear = () => {
        if (generation === builderTransitionGeneration) {
          delete owner.dataset.mooCatalogThemeBuilderUpdating;
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

    const applyBuilderTokens = (preference) => {
      Object.entries(BUILDER_DATASETS).forEach(([key, datasetKey]) => {
        if (preference[key] === THEME_BUILDER_DEFAULTS[key]) {
          delete owner.dataset[datasetKey];
        } else {
          owner.dataset[datasetKey] = preference[key];
        }
      });
      applyTokenStyle(
        owner,
        view,
        PUBLIC_THEME_BUILDER_TOKEN_ALLOW_LIST,
        isDefaultBuilderPreference(preference)
          ? {}
          : resolveThemeBuilderTokens(preference, {
              theme: owner.dataset.bsTheme,
              surface: "catalog",
            })
      );
    };

    const applyBuilderPreference = (
      candidate,
      { persist = true, clearDefaultTokens = true } = {}
    ) => {
      const preference = normalizedBuilderPreference(candidate);
      const hasOverrides = !isDefaultBuilderPreference(preference);
      builderPreview = null;
      builderPreference = preference;
      builderPreferenceHasOverrides = hasOverrides;
      const sync = () => {
        applyBuilderTokens(preference);
        syncBuilderControls(preference);
      };
      if (hasOverrides || clearDefaultTokens) {
        withBuilderTransitionSuppressed(sync);
      } else {
        syncBuilderControls(preference);
      }
      if (persist) {
        if (hasOverrides) {
          persistBuilderPreference(preference);
        } else {
          removeBuilderPreferenceStorage();
        }
      }
      return preference;
    };

    const previewBuilderPreference = (key, value) => {
      builderPreview = { key, value };
      const preference = normalizedBuilderPreference({
        ...readBuilderPreference(),
        [key]: value,
      });
      withBuilderTransitionSuppressed(() => applyBuilderTokens(preference));
      return preference;
    };

    const restoreBuilderPreview = (key, value) => {
      if (
        !builderPreview ||
        builderPreview.key !== key ||
        builderPreview.value !== value
      ) {
        return;
      }
      builderPreview = null;
      applyBuilderPreference(readBuilderPreference(), { persist: false });
    };

    Object.entries(builderControls).forEach(([key, control]) => {
      if (BUILDER_PREVIEW_KEYS.has(key)) {
        listen(control.root, "hidden.bs.dropdown", () => {
          if (builderPreview?.key === key) {
            builderPreview = null;
            applyBuilderPreference(readBuilderPreference(), { persist: false });
          }
        });
      }
      control.options.forEach((option) => {
        const value = option.dataset.mooCatalogThemeBuilderOption;
        if (BUILDER_PREVIEW_KEYS.has(key)) {
          listen(option, "pointerenter", () => {
            previewBuilderPreference(key, value);
          });
          listen(option, "focusin", () => {
            previewBuilderPreference(key, value);
          });
          listen(option, "pointerleave", () => {
            restoreBuilderPreview(key, value);
          });
          listen(option, "focusout", () => {
            restoreBuilderPreview(key, value);
          });
        }
        listen(option, "click", () => {
          applyBuilderPreference({
            ...readBuilderPreference(),
            [key]: value,
          });
        });
      });
    });

    applyBuilderPreference(readBuilderPreference(), {
      persist: false,
      clearDefaultTokens: builderPreferenceHasOverrides,
    });

    if (typeof view.MutationObserver === "function") {
      const observer = new view.MutationObserver((mutations) => {
        if (
          mutations.some(
            (mutation) => mutation.attributeName === "data-bs-theme"
          )
        ) {
          applyBuilderPreference(readBuilderPreference(), {
            persist: false,
            clearDefaultTokens: builderPreferenceHasOverrides,
          });
          syncThemeButton();
        }
      });
      observer.observe(owner, {
        attributes: true,
        attributeFilter: ["data-bs-theme"],
      });
      cleanups.push(() => observer.disconnect());
    }

    // The document owner writes html[dir]; embedded owners write only their
    // own dir attribute through the shared resolver contract.
    const readDirection = () =>
      readOwnerPreference(owner, "direction") ||
      resolveOwnerDirection(owner, null) ||
      "ltr";
    const applyDirection = (direction) => {
      setOwnerDirection(owner, direction);
      writeOwnerPreference(owner, "direction", direction, view);
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
      removeOwnerPreference(owner, "theme", view);
      removeOwnerPreference(owner, "direction", view);
      try {
        view.localStorage.removeItem(SIDEBAR_STORAGE_KEY);
        if (builderStorageKey) view.localStorage.removeItem(builderStorageKey);
      } catch (_) {
        /* Storage is best-effort. */
      }
      setOwnerTheme(owner, serverTheme === "dark" ? "dark" : "light");
      setOwnerDirection(owner, serverDirection);
      themeInputs.forEach((input) => {
        input.checked = input.value === "system";
      });
      directionInputs.forEach((input) => {
        input.checked = input.value === serverDirection;
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

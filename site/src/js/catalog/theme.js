import {
  findThemeOwner,
  findThemeOwners,
  ownerStorageKey,
  readOwnerPreference,
  resolveOwnerDirection,
  resolveOwnerTheme,
  safeColorSchemeMedia,
  setOwnerDirection,
  setOwnerTheme,
} from "../../../../src/js/theme-owner.js";

const states = new WeakMap();

function ownerView(owner, root) {
  return (
    owner?.ownerDocument?.defaultView ||
    root?.defaultView ||
    root?.ownerDocument?.defaultView
  );
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

function ownerButtons(root, owner) {
  return Array.from(
    root?.querySelectorAll?.("[data-moo-theme], .moo-catalog__theme-toggle") || []
  ).filter((button) => findThemeOwner(button) === owner);
}

function updateThemeButtons(buttons, theme) {
  buttons.forEach((button) => {
    button.setAttribute?.(
      "aria-label",
      theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
    );
  });
}

function applyOwnerTheme(owner, theme) {
  if (owner?.dataset?.bsTheme !== theme) {
    setOwnerTheme(owner, theme);
  }
}

// Theme preference lives on the resolved .moo-ui owner, never on html or body.
// A full document owner may use the legacy default key; embedded owners must
// opt into their own key, so unrelated host fragments never share a preference.
export function initTheme(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const listeners = [];
  const listen = (target, type, handler) => {
    target?.addEventListener?.(type, handler);
    if (target) listeners.push({ target, type, handler });
  };

  for (const owner of findThemeOwners(root)) {
    const view = ownerView(owner, root);
    const buttons = ownerButtons(root, owner);
    const applyPreference = (preference) => {
      const theme = resolveOwnerTheme(owner, preference, view);
      applyOwnerTheme(owner, theme);
      updateThemeButtons(buttons, theme);
      return theme;
    };

    applyPreference(readOwnerPreference(owner, "theme"));
    const direction = resolveOwnerDirection(
      owner,
      readOwnerPreference(owner, "direction")
    );
    if (direction) {
      setOwnerDirection(owner, direction);
    }

    const media = safeColorSchemeMedia(view);
    listen(media, "change", () => {
      if (readOwnerPreference(owner, "theme") === "system") {
        applyPreference("system");
      }
    });

    buttons.forEach((button) => {
      listen(button, "click", () => {
        const nextTheme = owner.dataset?.bsTheme === "dark" ? "light" : "dark";
        writeOwnerPreference(owner, "theme", nextTheme, view);
        applyPreference(nextTheme);
      });
    });
  }

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener?.(type, handler);
    });
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

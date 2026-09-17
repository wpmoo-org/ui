/*!
 * Moo UI theme prepaint
 * Copyright 2026 WPMoo (https://wpmoo.org)
 * Licensed under MIT (https://github.com/wpmoo-org/ui/blob/main/LICENSE)
 */
(() => {
  const ownerDocument =
    typeof document === "undefined"
      ? null
      : document;
  const owner = ownerDocument?.currentScript?.parentElement;
  const ownerSelector =
    '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';

  if (!owner?.matches?.(ownerSelector)) return;

  const body = ownerDocument?.body;
  const documentOwner =
    owner.dataset?.mooDocumentOwner === "true" &&
    owner.parentElement === body &&
    owner === body?.firstElementChild;
  const view =
    ownerDocument?.defaultView ||
    (typeof window === "undefined" ? null : window);
  const normalizeDirection = (value) =>
    value === "ltr" || value === "rtl" ? value : null;
  const ownerDirection = normalizeDirection(
    owner.getAttribute?.("dir") || owner.dir,
  );
  const documentDirection = normalizeDirection(
    ownerDocument?.documentElement?.getAttribute?.("dir") ||
      ownerDocument?.documentElement?.dir,
  );
  owner.__mooPrepaintBaseline = {
    theme: owner.dataset.bsTheme === "dark" ? "dark" : "light",
    direction: documentOwner ? documentDirection || "ltr" : ownerDirection,
  };

  const readPreference = (axis, allowed) => {
    const dataKey = axis === "theme" ? "mooThemeKey" : "mooDirectionKey";
    const explicit = owner.dataset?.[dataKey]?.trim();
    const key = explicit || (documentOwner ? `moo:${axis}` : null);
    if (!key) return null;

    try {
      const value = view?.localStorage?.getItem(key);
      return allowed.includes(value) ? value : null;
    } catch (_) {
      return null;
    }
  };

  const systemPrefersDark = () => {
    try {
      const matchMedia = view?.matchMedia;
      if (typeof matchMedia !== "function") return null;
      return Boolean(
        matchMedia.call(view, "(prefers-color-scheme: dark)")?.matches,
      );
    } catch (_) {
      return null;
    }
  };

  try {
    const storedTheme = readPreference("theme", ["light", "dark", "system"]);
    const mediaPrefersDark =
      storedTheme === "system" ? systemPrefersDark() : null;
    const resolvedTheme =
      storedTheme === "dark"
        ? "dark"
        : storedTheme === "light"
          ? "light"
          : storedTheme === "system" && mediaPrefersDark !== null
            ? mediaPrefersDark
              ? "dark"
              : "light"
            : owner.dataset.bsTheme === "dark"
              ? "dark"
              : "light";
    owner.dataset.bsTheme = resolvedTheme;

    const storedDirection = readPreference("direction", ["ltr", "rtl"]);
    if (storedDirection) {
      if (documentOwner) ownerDocument.documentElement.dir = storedDirection;
      else owner.dir = storedDirection;
    }
  } finally {
    owner.dataset.mooPrepaint = "ready";
  }
})();

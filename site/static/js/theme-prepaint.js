(() => {
  const owner = document.currentScript?.parentElement;
  const ownerSelector =
    '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';

  if (!owner?.matches?.(ownerSelector)) return;

  const topLevelOwners = Array.from(document.body?.children || []).filter((child) =>
    child.matches?.(ownerSelector),
  );
  const documentOwner =
    owner.parentElement === document.body &&
    owner === document.body.firstElementChild &&
    topLevelOwners.length === 1;
  const readPreference = (axis, allowed) => {
    const dataKey = axis === 'theme' ? 'mooThemeKey' : 'mooDirectionKey';
    const explicit = owner.dataset?.[dataKey]?.trim();
    const key = explicit || (documentOwner ? `moo:${axis}` : null);
    if (!key) return null;

    try {
      const value = window.localStorage?.getItem(key);
      return allowed.includes(value) ? value : null;
    } catch (_) {
      return null;
    }
  };

  try {
    const storedTheme = readPreference('theme', ['light', 'dark', 'system']);
    const prefersDark =
      storedTheme === 'system' &&
      Boolean(window.matchMedia?.('(prefers-color-scheme: dark)').matches);
    const resolvedTheme =
      storedTheme === 'dark' || prefersDark
        ? 'dark'
        : storedTheme === 'light'
          ? 'light'
          : owner.dataset.bsTheme === 'dark'
            ? 'dark'
            : 'light';
    owner.dataset.bsTheme = resolvedTheme;

    const storedDirection = readPreference('direction', ['ltr', 'rtl']);
    if (storedDirection) {
      if (documentOwner) document.documentElement.dir = storedDirection;
      else owner.dir = storedDirection;
    }
  } finally {
    owner.dataset.mooPrepaint = 'ready';
  }
})();

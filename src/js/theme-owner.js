const OWNER_SELECTOR =
  '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';
const PORTAL_SELECTOR = '[data-moo-overlay-portal-host]';

const OWNER_PREFERENCES = {
  theme: {
    dataKey: 'mooThemeKey',
    storageKey: 'moo:theme',
    values: new Set(['light', 'dark', 'system']),
  },
  direction: {
    dataKey: 'mooDirectionKey',
    storageKey: 'moo:direction',
    values: new Set(['ltr', 'rtl']),
  },
};

function documentFor(node) {
  if (node?.nodeType === 9) return node;
  if (node?.ownerDocument) return node.ownerDocument;
  return typeof document === 'undefined' ? null : document;
}

function isResolvedOwner(node) {
  return Boolean(node?.matches?.(OWNER_SELECTOR));
}

function ownerRootFor(node) {
  const ownerDocument = documentFor(node);
  if (node?.nodeType === 9 || node === ownerDocument?.body) {
    return ownerDocument?.body?.firstElementChild || null;
  }
  return node;
}

function explicitDirection(owner) {
  const value = owner?.getAttribute?.('dir') || owner?.dir;
  return normalizeDirection(value);
}

function normalizeDirection(value) {
  return value === 'ltr' || value === 'rtl' ? value : null;
}

function normalizeTheme(value) {
  return value === 'dark' ? 'dark' : 'light';
}

export function findThemeOwner(node = typeof document === 'undefined' ? null : document) {
  const start = ownerRootFor(node);
  if (!start) return null;
  if (isResolvedOwner(start)) return start;
  return start.closest?.(OWNER_SELECTOR) || null;
}

export function findThemeOwners(root = typeof document === 'undefined' ? null : document) {
  const ownerDocument = documentFor(root);
  const scope = root?.nodeType === 9 ? ownerDocument?.body : root;
  if (!scope) return [];

  const owners = isResolvedOwner(scope) ? [scope] : [];
  const descendants = scope.querySelectorAll?.(OWNER_SELECTOR) || [];
  for (const owner of descendants) {
    if (owner !== scope) owners.push(owner);
  }
  return owners;
}

export function isDocumentOwner(owner) {
  if (!isResolvedOwner(owner)) return false;
  const ownerDocument = documentFor(owner);
  const body = ownerDocument?.body;
  if (!body || owner.parentElement !== body || body.firstElementChild !== owner) {
    return false;
  }
  const topLevelOwners = Array.from(body.children || []).filter(isResolvedOwner);
  return topLevelOwners.length === 1;
}

export function resolveThemeElement(node = typeof document === 'undefined' ? null : document) {
  return findThemeOwner(node) || documentFor(node)?.body || null;
}

export function ownerPortalRoot(owner) {
  if (!owner) return null;
  return (
    Array.from(owner.children || []).find((child) =>
      child.matches?.(PORTAL_SELECTOR),
    ) || owner
  );
}

export function ownerStorageKey(owner, axis) {
  const preference = OWNER_PREFERENCES[axis];
  if (!owner || !preference) return null;

  const explicit = owner.dataset?.[preference.dataKey]?.trim();
  if (explicit) return explicit;
  return isDocumentOwner(owner) ? preference.storageKey : null;
}

export function readOwnerPreference(owner, axis) {
  const preference = OWNER_PREFERENCES[axis];
  const key = ownerStorageKey(owner, axis);
  if (!preference || !key) return null;

  try {
    const value = documentFor(owner)?.defaultView?.localStorage?.getItem(key);
    return preference.values.has(value) ? value : null;
  } catch (_) {
    return null;
  }
}

export function safeColorSchemeMedia(view) {
  try {
    const matchMedia = view?.matchMedia;
    return typeof matchMedia === 'function'
      ? matchMedia.call(view, '(prefers-color-scheme: dark)')
      : null;
  } catch (_) {
    return null;
  }
}

export function ownerPrepaintBaseline(owner) {
  const baseline = owner?.__mooPrepaintBaseline;
  const hasBaselineDirection = Object.hasOwn(baseline || {}, 'direction');
  const fallbackDirection = isDocumentOwner(owner)
    ? explicitDirection(documentFor(owner)?.documentElement) || 'ltr'
    : explicitDirection(owner);

  return {
    theme: normalizeTheme(baseline?.theme || owner?.dataset?.bsTheme),
    direction: hasBaselineDirection
      ? normalizeDirection(baseline.direction)
      : fallbackDirection,
  };
}

export function effectiveOwnerDirection(owner) {
  const visited = new Set();
  let node = owner;

  while (node && !visited.has(node)) {
    visited.add(node);
    const direction = explicitDirection(node);
    if (direction) return direction;
    node = node.parentElement;
  }

  return explicitDirection(documentFor(owner)?.documentElement) || 'ltr';
}

export function resolveOwnerTheme(owner, preference, view) {
  if (preference === 'light' || preference === 'dark') return preference;
  if (preference === 'system') {
    try {
      return safeColorSchemeMedia(view)?.matches ? 'dark' : 'light';
    } catch (_) {
      return 'light';
    }
  }
  return owner?.dataset?.bsTheme === 'dark' ? 'dark' : 'light';
}

export function resolveOwnerDirection(owner, preference) {
  if (preference === 'ltr' || preference === 'rtl') return preference;
  if (!owner) return null;
  if (isDocumentOwner(owner)) {
    return explicitDirection(documentFor(owner)?.documentElement) || 'ltr';
  }
  return explicitDirection(owner);
}

export function setOwnerTheme(owner, theme) {
  if (!owner || (theme !== 'light' && theme !== 'dark')) return;
  owner.dataset.bsTheme = theme;
}

export function setOwnerDirection(owner, direction) {
  if (!owner || (direction !== 'ltr' && direction !== 'rtl')) return;
  if (isDocumentOwner(owner)) {
    documentFor(owner).documentElement.dir = direction;
    return;
  }
  owner.dir = direction;
}

export function restoreOwnerDirection(owner, direction) {
  if (!owner) return;
  const normalized = normalizeDirection(direction);

  if (isDocumentOwner(owner)) {
    setOwnerDirection(owner, normalized || 'ltr');
    return;
  }

  if (normalized) {
    setOwnerDirection(owner, normalized);
    return;
  }
  owner.removeAttribute?.('dir');
}

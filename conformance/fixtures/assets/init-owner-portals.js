/**
 * Owner portal conformance fixture initialization.
 *
 * Bootstrap's Tooltip and Popover APIs are intentionally initialized with a
 * resolved owner portal. The fixture stays CSP-clean: no inline script and no
 * body-level portal fallback while a resolved owner exists.
 */
(() => {
  "use strict";

  const OWNER_SELECTOR =
    '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';

  const findThemeOwner = (trigger) => trigger.closest(OWNER_SELECTOR);
  const ownerPortalRoot = (owner) => (
    Array.from(owner.children).find((child) =>
      child.matches("[data-moo-overlay-portal-host]"),
    ) || owner
  );

  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((trigger) => {
    const portal = ownerPortalRoot(findThemeOwner(trigger));
    window.bootstrap.Tooltip.getOrCreateInstance(trigger, { container: portal });
  });
  document.querySelectorAll('[data-bs-toggle="popover"]').forEach((trigger) => {
    const portal = ownerPortalRoot(findThemeOwner(trigger));
    window.bootstrap.Popover.getOrCreateInstance(trigger, { container: portal });
  });

  document.body.dataset.ownerPortalsReady = "true";
})();

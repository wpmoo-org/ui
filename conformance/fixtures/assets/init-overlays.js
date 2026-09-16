/**
 * Generic Host Conformance Kit — overlays fixture initialization.
 *
 * Tooltips and popovers are opt-in under Bootstrap 5: the documented host
 * responsibility is to construct them explicitly. Kept as a standalone
 * external script so the fixture stays strict-CSP clean (no inline scripts).
 */
(() => {
  "use strict";

  const { Tooltip, Popover } = window.bootstrap;
  const ownerSelector =
    '.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]';
  const ownerPortalRoot = (owner) => (
    Array.from(owner?.children || []).find((child) =>
      child.matches("[data-moo-overlay-portal-host]"),
    ) || owner
  );

  document
    .querySelectorAll('[data-bs-toggle="tooltip"]')
    .forEach((element) => {
      const owner = element.closest(ownerSelector);
      const portal = ownerPortalRoot(owner);
      Tooltip.getOrCreateInstance(element, { container: portal });
    });

  document
    .querySelectorAll('[data-bs-toggle="popover"]')
    .forEach((element) => {
      const owner = element.closest(ownerSelector);
      const portal = ownerPortalRoot(owner);
      Popover.getOrCreateInstance(element, { container: portal });
    });

  document.body.dataset.overlaysReady = "true";
})();

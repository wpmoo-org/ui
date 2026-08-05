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

  document
    .querySelectorAll('[data-bs-toggle="tooltip"]')
    .forEach((element) => Tooltip.getOrCreateInstance(element));

  document
    .querySelectorAll('[data-bs-toggle="popover"]')
    .forEach((element) => Popover.getOrCreateInstance(element));

  document.body.dataset.overlaysReady = "true";
})();

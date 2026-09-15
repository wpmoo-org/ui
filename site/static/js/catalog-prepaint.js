/*
 * Catalog initial state runs synchronously before the deferred catalog module
 * initializes, keeping layout state setup in one external script.
 */
(function () {
  "use strict";

  const state = document.documentElement.dataset.sidebarCatalogState;
  const shell = document.querySelector(
    '[data-slot="sidebar-wrapper"][data-sidebar-key="catalog-shell"]'
  );
  if (
    (state === "collapsed" || state === "expanded") &&
    shell?.dataset.sidebarKey === "catalog-shell"
  ) {
    shell.dataset.sidebarState = state;
  }

  // Apply a saved Sidebar variant synchronously, right after the sidebar
  // renders and before the rest of the page paints, so a non-default choice
  // never flashes the default layout first.
  const sidebar = document.getElementById("catalog-sidebar");
  if (sidebar) {
    let stored;
    try {
      stored = window.localStorage.getItem("moo:sidebar-variant");
    } catch (_) {
      stored = null;
    }
    if (stored === "sidebar" || stored === "inset" || stored === "floating") {
      sidebar.dataset.variant = stored;
    }
  }

  // data-moo-sidebar-active-prepaint
  // Match Sidebar's active route positioning before the deferred catalog
  // module loads, so deep menu pages never flash from the top.
  const active = shell?.querySelector(
    '[data-slot="sidebar-content"] a[data-slot="sidebar-menu-button"][aria-current="page"], ' +
      '[data-slot="sidebar-content"] a.sidebar-menu-button[aria-current="page"], ' +
      '[data-slot="sidebar-content"] a.sidebar-menu-button.active'
  );
  const content = active?.closest('[data-slot="sidebar-content"]');
  if (!active || !content || content.clientHeight <= 0) {
    return;
  }
  const maxScrollTop = content.scrollHeight - content.clientHeight;
  if (maxScrollTop <= 0) {
    return;
  }

  const contentRect = content.getBoundingClientRect();
  const activeRect = active.getBoundingClientRect();
  if (contentRect.height <= 0 || activeRect.height <= 0) {
    return;
  }

  const targetScrollTop =
    content.scrollTop +
    activeRect.top -
    contentRect.top -
    (content.clientHeight - activeRect.height) / 2;
  content.scrollTop = Math.round(
    Math.min(Math.max(targetScrollTop, 0), maxScrollTop)
  );
})();

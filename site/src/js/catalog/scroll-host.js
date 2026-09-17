export function resolveCatalogScrollHost(root = document) {
  const documentNode = root.nodeType === 9 ? root : root.ownerDocument;
  const view = root.defaultView || documentNode?.defaultView || window;
  const page = root.querySelector?.('[data-slot="page"]') || null;
  const main = page?.querySelector?.(':scope > main#main-content') || null;
  const mainOverflowY = main ? view.getComputedStyle(main).overflowY : "visible";
  const overflowY = page ? view.getComputedStyle(page).overflowY : "visible";

  if (main && (mainOverflowY === "auto" || mainOverflowY === "scroll")) {
    return { element: main, eventTarget: main, page };
  }

  if (page && (overflowY === "auto" || overflowY === "scroll")) {
    return { element: page, eventTarget: page, page };
  }

  const documentScroller = documentNode?.scrollingElement || documentNode?.documentElement;
  return { element: documentScroller, eventTarget: view, page };
}

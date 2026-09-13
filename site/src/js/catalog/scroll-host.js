export function resolveCatalogScrollHost(root = document) {
  const documentNode = root.nodeType === 9 ? root : root.ownerDocument;
  const view = root.defaultView || documentNode?.defaultView || window;
  const page = root.querySelector?.('[data-slot="page"]') || null;
  const overflowY = page ? view.getComputedStyle(page).overflowY : "visible";

  if (page && (overflowY === "auto" || overflowY === "scroll")) {
    return { element: page, eventTarget: page, page };
  }

  const documentScroller = documentNode?.scrollingElement || documentNode?.documentElement;
  return { element: documentScroller, eventTarget: view, page };
}

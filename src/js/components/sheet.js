const states = new WeakMap();

export function initSheets(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const documentRoot = root.nodeType === 9 ? root : root.ownerDocument;
  const Offcanvas = documentRoot?.defaultView?.bootstrap?.Offcanvas;
  if (!Offcanvas) {
    return () => {};
  }

  const sheets = Array.from(root.querySelectorAll(".offcanvas.sheet"));
  const focusInitialField = (event) => {
    if (event.target === event.currentTarget) {
      event.currentTarget.querySelector("[autofocus]:not(:disabled)")?.focus();
    }
  };
  const dispose = () => {
    if (states.get(root) !== dispose) {
      return;
    }
    sheets.forEach((sheet) => {
      sheet.removeEventListener("shown.bs.offcanvas", focusInitialField);
    });
    states.delete(root);
  };
  states.set(root, dispose);

  sheets.forEach((sheet) => {
    // Bootstrap focuses the panel before emitting shown; then honor native autofocus.
    sheet.addEventListener("shown.bs.offcanvas", focusInitialField);
    if (sheet.dataset.sheetOpenOnLoad === "true") {
      sheet.removeAttribute("data-sheet-open-on-load");
      Offcanvas.getOrCreateInstance(sheet).show();
    }
  });
  return dispose;
}

function focusInitialField(event) {
  if (event.target === event.currentTarget) {
    event.currentTarget.querySelector("[autofocus]:not(:disabled)")?.focus();
  }
}

export function initSheets(root = document) {
  const documentRoot = root.nodeType === 9 ? root : root.ownerDocument;
  const Offcanvas = documentRoot?.defaultView?.bootstrap?.Offcanvas;
  if (!Offcanvas) {
    return;
  }

  root.querySelectorAll(".offcanvas.sheet").forEach((sheet) => {
    // Bootstrap focuses the panel before emitting shown; then honor native autofocus.
    sheet.removeEventListener("shown.bs.offcanvas", focusInitialField);
    sheet.addEventListener("shown.bs.offcanvas", focusInitialField);
    if (sheet.dataset.sheetOpenOnLoad === "true") {
      sheet.removeAttribute("data-sheet-open-on-load");
      Offcanvas.getOrCreateInstance(sheet).show();
    }
  });
}

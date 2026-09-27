export function initSheets(root = document) {
  const documentRoot = root.nodeType === 9 ? root : root.ownerDocument;
  const Offcanvas = documentRoot?.defaultView?.bootstrap?.Offcanvas;
  if (!Offcanvas) {
    return;
  }

  root.querySelectorAll('.offcanvas.sheet[data-sheet-open-on-load="true"]').forEach((sheet) => {
    sheet.removeAttribute("data-sheet-open-on-load");
    Offcanvas.getOrCreateInstance(sheet).show();
  });
}

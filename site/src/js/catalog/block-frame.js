const states = new WeakMap();

export function initBlockFrames(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const shells = Array.from(root.querySelectorAll("[data-moo-block-frame-shell]"));
  const listeners = [];
  let observer = null;
  const listen = (target, type, handler) => {
    target?.addEventListener(type, handler);
    if (target) {
      listeners.push({ target, type, handler });
    }
  };
  const resize = (shell) => {
    const viewport = shell.querySelector("[data-moo-block-frame-viewport]");
    const frame = shell.querySelector("[data-moo-block-frame]");
    const width = Number(
      shell.dataset.mooFrameWidth || frame?.getAttribute("width") || 1280
    );
    const height = Number(
      shell.dataset.mooFrameHeight || frame?.getAttribute("height") || 720
    );
    if (!viewport || !frame || !width || !height) {
      return;
    }
    const scale = Math.min(1, viewport.clientWidth / width);
    frame.style.width = `${width}px`;
    frame.style.height = `${height}px`;
    frame.style.transform = `scale(${scale})`;
    viewport.style.height = `${Math.ceil(height * scale)}px`;
  };
  const resizeAll = () => shells.forEach(resize);

  if (shells.length > 0) {
    if (view.ResizeObserver) {
      observer = new view.ResizeObserver(resizeAll);
      shells.forEach((shell) => observer.observe(shell));
    }
    shells.forEach((shell) => {
      listen(shell.querySelector("[data-moo-block-frame]"), "load", () => resize(shell));
    });
    listen(view, "resize", resizeAll);
    resizeAll();
  }

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    observer?.disconnect();
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

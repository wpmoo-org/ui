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
  const updateSizeLabel = (shell, width, height) => {
    const label = shell.querySelector("[data-moo-frame-size-label]");
    if (label) {
      label.textContent = `${width} x ${height}`;
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
    updateSizeLabel(shell, width, height);
  };
  const resizeAll = () => shells.forEach(resize);
  const setActiveButton = (buttons, activeButton) => {
    buttons.forEach((button) => {
      const isActive = button === activeButton;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  };
  const setFrameSize = (shell, width, height) => {
    shell.dataset.mooFrameWidth = String(width);
    shell.dataset.mooFrameHeight = String(height);
    const frame = shell.querySelector("[data-moo-block-frame]");
    frame?.setAttribute("width", String(width));
    frame?.setAttribute("height", String(height));
    resize(shell);
  };
  const setVariant = (shell, button) => {
    const frame = shell.querySelector("[data-moo-block-frame]");
    const standaloneLink = shell.querySelector("[data-moo-frame-standalone-link]");
    const label = shell.querySelector("[data-moo-frame-variant-label]");
    const src = button.dataset.mooFrameSrc;
    if (!frame || !src) {
      return;
    }
    const buttons = Array.from(shell.querySelectorAll("[data-moo-frame-variant]"));
    buttons.forEach((candidate) => {
      const isActive = candidate === button;
      candidate.classList.toggle("active", isActive);
      if (isActive) {
        candidate.setAttribute("aria-current", "true");
      } else {
        candidate.removeAttribute("aria-current");
      }
    });
    if (label) {
      label.textContent = button.dataset.mooFrameVariantLabel || button.textContent.trim();
    }
    if (standaloneLink) {
      standaloneLink.href = src;
    }
    if (frame.getAttribute("src") !== src) {
      frame.setAttribute("src", src);
    }
    resize(shell);
  };
  const setViewportPreset = (shell, button) => {
    const width = Number(button.dataset.mooFrameWidth || 0);
    const height = Number(button.dataset.mooFrameHeight || 0);
    if (!width || !height) {
      return;
    }
    setActiveButton(Array.from(shell.querySelectorAll("[data-moo-frame-preset]")), button);
    setFrameSize(shell, width, height);
  };

  if (shells.length > 0) {
    if (view.ResizeObserver) {
      observer = new view.ResizeObserver(resizeAll);
      shells.forEach((shell) => observer.observe(shell));
    }
    shells.forEach((shell) => {
      listen(shell.querySelector("[data-moo-block-frame]"), "load", () => resize(shell));
      shell.querySelectorAll("[data-moo-frame-variant]").forEach((button) => {
        listen(button, "click", () => setVariant(shell, button));
      });
      shell.querySelectorAll("[data-moo-frame-preset]").forEach((button) => {
        listen(button, "click", () => setViewportPreset(shell, button));
      });
      const activePreset = shell.querySelector("[data-moo-frame-preset].active");
      if (activePreset) {
        setViewportPreset(shell, activePreset);
      }
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

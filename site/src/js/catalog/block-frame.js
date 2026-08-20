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
  // The viewport wrapper is overflow: hidden and never meant to scroll --
  // the iframe inside it is sized to fit via transform: scale(), not via
  // scrolling. Safari's "scroll the focused element's ancestors into view"
  // behavior can still reach out across the iframe boundary and give this
  // wrapper a real (if scrollbar-less) horizontal scroll offset when focus
  // lands inside the iframe (e.g. opening the release-review preview's
  // "View" dropdown), which shifts the scaled iframe's whole static
  // position -- not just its paint -- off to the side. Reset it back
  // unconditionally on scroll; a container that should never scroll has no
  // legitimate offset to preserve.
  const clampViewportScroll = (viewport) => {
    if (viewport.scrollLeft !== 0) {
      viewport.scrollLeft = 0;
    }
    if (viewport.scrollTop !== 0) {
      viewport.scrollTop = 0;
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
    clampViewportScroll(viewport);
    updateSizeLabel(shell, width, height);
  };
  const revealFrame = (shell) => {
    // The iframe has finished loading its content; fade out the loading
    // placeholder so the rendered preview shows through. idempotent.
    const viewport = shell.querySelector("[data-moo-block-frame-viewport]");
    if (viewport) {
      viewport.classList.add("is-loaded");
    }
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
      // A different preview is about to load; bring the loading placeholder
      // back until the new document fires its load event.
      const viewport = shell.querySelector("[data-moo-block-frame-viewport]");
      viewport?.classList.remove("is-loaded");
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
      const frame = shell.querySelector("[data-moo-block-frame]");
      listen(frame, "load", () => {
        revealFrame(shell);
        resize(shell);
      });
      // If the iframe already finished loading before this module ran (e.g.
      // it was cached and painted synchronously), the load event will never
      // fire again; reveal it immediately instead of leaving the placeholder
      // stuck over a ready preview. A lazy iframe starts on about:blank whose
      // readyState is already "complete", so the check must also confirm the
      // document is not the initial blank placeholder before revealing.
      if (
        frame?.contentWindow &&
        frame.contentWindow.location?.href !== "about:blank" &&
        frame.contentDocument?.readyState === "complete"
      ) {
        revealFrame(shell);
      }
      const viewport = shell.querySelector("[data-moo-block-frame-viewport]");
      if (viewport) {
        listen(viewport, "scroll", () => clampViewportScroll(viewport));
      }
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

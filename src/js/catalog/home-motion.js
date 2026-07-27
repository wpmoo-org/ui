const states = new WeakMap();

export function initHomeMotion(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const targets = Array.from(root.querySelectorAll("[data-moo-tilt]"));
  const motionQuery = view.matchMedia("(prefers-reduced-motion: reduce)");
  const listeners = [];
  const listen = (target, type, handler, options) => {
    target?.addEventListener(type, handler, options);
    if (target) {
      listeners.push({ target, type, handler, options });
    }
  };
  const reset = (target) => {
    delete target.dataset.mooTiltActive;
    target.style.removeProperty("--moo-tilt-x");
    target.style.removeProperty("--moo-tilt-y");
    target.style.removeProperty("--moo-tilt-shift-x");
    target.style.removeProperty("--moo-tilt-shift-y");
  };
  const bindTargets = () => {
    if (motionQuery.matches) {
      targets.forEach(reset);
      return;
    }
    targets.forEach((target) => {
      listen(target, "pointermove", (event) => {
        if (event.pointerType === "touch") {
          return;
        }
        const rect = target.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
        const y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
        target.dataset.mooTiltActive = "true";
        target.style.setProperty("--moo-tilt-x", `${(-y * 5).toFixed(2)}deg`);
        target.style.setProperty("--moo-tilt-y", `${(x * 6).toFixed(2)}deg`);
        target.style.setProperty("--moo-tilt-shift-x", `${(x * 6).toFixed(1)}px`);
        target.style.setProperty("--moo-tilt-shift-y", `${(y * 4).toFixed(1)}px`);
      });
      listen(target, "pointerleave", () => reset(target));
      listen(target, "blur", () => reset(target), true);
    });
  };

  bindTargets();
  listen(motionQuery, "change", () => {
    if (motionQuery.matches) {
      targets.forEach(reset);
    }
  });

  const dispose = () => {
    listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    targets.forEach(reset);
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

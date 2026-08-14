const states = new WeakMap();

export function initCodePreview(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const listeners = [];
  const timers = new Set();
  const listen = (target, type, handler, options) => {
    target?.addEventListener(type, handler, options);
    if (target) {
      listeners.push({ target, type, handler, options });
    }
  };
  const delay = (handler, timeout) => {
    const timer = view.setTimeout(() => {
      timers.delete(timer);
      handler();
    }, timeout);
    timers.add(timer);
    return timer;
  };

  root.querySelectorAll("[data-moo-copy-page]").forEach((trigger) => {
    listen(trigger, "click", async () => {
      const value =
        trigger.getAttribute("data-moo-copy-value") || view.location.href.split("#")[0];
      const label = trigger.querySelector("[data-moo-copy-page-label]");
      const previous = label?.textContent;
      try {
        await view.navigator.clipboard.writeText(value);
        if (label) {
          label.textContent = "Copied";
        }
      } catch (_) {
        if (label) {
          label.textContent = "Copy failed";
        }
      }
      if (label) {
        delay(() => {
          label.textContent = previous;
        }, 1600);
      }
    });
  });

  const main = root.querySelector(".moo-catalog__main");
  let pendingScrollTop = null;
  const captureTabScroll = () => {
    if (main) {
      pendingScrollTop = main.scrollTop;
    }
  };
  const freezeTabScroll = () => {
    if (!main) {
      return;
    }
    const scrollTop = pendingScrollTop ?? main.scrollTop;
    pendingScrollTop = null;
    const previousBehavior = main.style.scrollBehavior;
    main.style.scrollBehavior = "auto";
    main.scrollTop = scrollTop;
    view.requestAnimationFrame(() => {
      main.scrollTop = scrollTop;
      view.requestAnimationFrame(() => {
        main.scrollTop = scrollTop;
        delay(() => {
          main.scrollTop = scrollTop;
          main.style.scrollBehavior = previousBehavior;
        }, 180);
      });
    });
  };
  listen(root, "pointerdown", (event) => {
    const target = event.target;
    if (
      target instanceof view.Element &&
      target.closest(".tabs-list [data-bs-toggle='tab']")
    ) {
      captureTabScroll();
    }
  }, true);
  listen(root, "keydown", (event) => {
    const target = event.target;
    if (
      target instanceof view.Element &&
      target.closest(".tabs-list [data-bs-toggle='tab']") &&
      (event.key === "Enter" || event.key === " ")
    ) {
      captureTabScroll();
    }
  }, true);
  listen(root, "show.bs.tab", (event) => {
    const target = event.target;
    if (target instanceof view.Element && target.closest(".tabs-list")) {
      freezeTabScroll();
    }
  }, true);

  const renderCodeLineNumbers = (panel) => {
    const lines = panel.querySelector(".moo-code__lines");
    const code = panel.querySelector("code");
    if (!lines || !code) {
      return;
    }
    const count = Math.max(1, code.textContent.split("\n").length);
    lines.textContent = Array.from(
      { length: count },
      (_, index) => String(index + 1)
    ).join("\n");
  };

  root.querySelectorAll("[data-moo-code-panel]").forEach((panel) => {
    const toggle = panel.querySelector("[data-moo-code-toggle]");
    const copyButton = panel.querySelector("[data-moo-code-copy]");
    const copyStatus = panel.querySelector("[data-moo-copy-status]");
    const copyIcon = copyButton?.querySelector('[data-moo-copy-icon="copy"]');
    const checkIcon = copyButton?.querySelector('[data-moo-copy-icon="check"]');
    const scroller = panel.querySelector(".moo-code");
    const code = panel.querySelector("code");
    let copyResetTimer = null;
    const setCopyState = (copied) => {
      if (copyIcon && checkIcon) {
        copyIcon.hidden = copied;
        checkIcon.hidden = !copied;
      }
      copyButton.dataset.mooCopied = copied ? "true" : "false";
      copyButton.setAttribute("aria-label", copied ? "Copied" : "Copy code");
      copyButton.setAttribute("title", copied ? "Copied" : "Copy code");
    };
    renderCodeLineNumbers(panel);
    listen(toggle, "click", () => {
      panel.dataset.expanded = "true";
      scroller.classList.toggle(
        "moo-code--scrolling",
        scroller.scrollHeight > scroller.clientHeight
      );
      toggle.setAttribute("aria-expanded", "true");
      copyButton.hidden = false;
    });
    listen(copyButton, "click", async () => {
      try {
        await view.navigator.clipboard.writeText(code.textContent);
        copyStatus.textContent = "Copied";
        setCopyState(true);
        if (copyResetTimer) {
          view.clearTimeout(copyResetTimer);
          timers.delete(copyResetTimer);
        }
        copyResetTimer = delay(() => {
          copyStatus.textContent = "";
          setCopyState(false);
          copyResetTimer = null;
        }, 1600);
      } catch (_) {
        copyStatus.textContent = "Copy failed";
        setCopyState(false);
        delay(() => {
          copyStatus.textContent = "";
        }, 2000);
      }
    });
  });

  const dispose = () => {
    listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    timers.forEach((timer) => view.clearTimeout(timer));
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

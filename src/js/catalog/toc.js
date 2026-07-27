const states = new WeakMap();

export function initToc(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const componentToc = root.querySelector("[data-moo-component-toc]");
  const componentNav = componentToc?.querySelector("[data-moo-component-toc-nav]");
  const examples = Array.from(
    root.querySelectorAll(".moo-component-examples > .moo-example[aria-labelledby]")
  );
  const generatedLinks = [];
  const listeners = [];
  const listen = (target, type, handler, options) => {
    target?.addEventListener(type, handler, options);
    if (target) {
      listeners.push({ target, type, handler, options });
    }
  };

  if (componentToc && componentNav && examples.length > 0) {
    examples.forEach((example) => {
      const titleId = example.getAttribute("aria-labelledby");
      const title = titleId ? root.getElementById(titleId) : null;
      if (!titleId || !title?.textContent?.trim()) {
        return;
      }
      const link = root.createElement("a");
      link.className = "nav-link";
      link.href = `#${titleId}`;
      link.textContent = title.textContent.trim();
      componentNav.appendChild(link);
      generatedLinks.push(link);
    });
    componentToc.hidden = componentNav.children.length === 0;
  }

  const links = Array.from(root.querySelectorAll(".moo-doc-toc .nav-link"));
  const targets = links
    .map((link) => {
      const id = link.getAttribute("href")?.slice(1);
      const target = id ? root.getElementById(id) : null;
      return target ? { link, target } : null;
    })
    .filter(Boolean);
  const main = root.querySelector(".moo-catalog__main");
  let frame = 0;
  let clickUntil = 0;

  const activate = (activeLink) => {
    targets.forEach(({ link }) => {
      const active = link === activeLink;
      link.classList.toggle("active", active);
      if (active) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };
  const update = () => {
    frame = 0;
    if (targets.length === 0 || Date.now() < clickUntil) {
      return;
    }
    const offset = parseFloat(view.getComputedStyle(root.documentElement).fontSize) * 6;
    let active = targets[0];
    targets.forEach((item) => {
      if (item.target.getBoundingClientRect().top <= offset) {
        active = item;
      }
    });
    activate(active.link);
  };
  const requestUpdate = () => {
    if (frame === 0) {
      frame = view.requestAnimationFrame(update);
    }
  };

  if (targets.length > 0) {
    targets.forEach(({ link }) => {
      listen(link, "click", () => {
        clickUntil = Date.now() + 2500;
        activate(link);
      });
    });
    update();
    listen(main, "scroll", requestUpdate, { passive: true });
    listen(view, "resize", requestUpdate);
    listen(view, "hashchange", requestUpdate);
  }

  const dispose = () => {
    listeners.forEach(({ target, type, handler, options }) => {
      target.removeEventListener(type, handler, options);
    });
    if (frame) {
      view.cancelAnimationFrame(frame);
    }
    generatedLinks.forEach((link) => link.remove());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

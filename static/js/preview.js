import Combobox from "./components/combobox.js";
import Sidebar from "./components/sidebar.js";

(() => {
  const root = document.documentElement;
  const THEME_STORAGE_KEY = "moo:theme";
  const themeButton = document.querySelector("[data-moo-theme], .moo-catalog__theme-toggle");
  const directionButton = document.querySelector("[data-moo-direction], .moo-catalog__direction-toggle");
  const themeIcons = Array.from(themeButton?.querySelectorAll("[data-moo-theme-icon]") || []);

  const getStoredTheme = () => {
    try {
      const theme = window.localStorage.getItem(THEME_STORAGE_KEY);
      return theme === "dark" || theme === "light" ? theme : null;
    } catch (_) {
      return null;
    }
  };

  const setStoredTheme = (theme) => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (_) {
      /* localStorage can be unavailable in restricted browsing contexts. */
    }
  };

  const storedTheme = getStoredTheme();

  if (storedTheme) {
    root.dataset.bsTheme = storedTheme;
  }

  const updateThemeButton = () => {
    const theme = root.dataset.bsTheme || "light";

    themeButton?.setAttribute(
      "aria-label",
      theme === "dark" ? "Switch to light mode" : "Switch to dark mode"
    );

    themeIcons.forEach((icon) => {
      icon.classList.toggle("d-none", icon.dataset.mooThemeIcon !== theme);
    });
  };

  themeButton?.addEventListener("click", () => {
    const theme = root.dataset.bsTheme === "dark" ? "light" : "dark";
    root.dataset.bsTheme = theme;
    setStoredTheme(theme);
    updateThemeButton();
  });

  updateThemeButton();

  const searchControls = Array.from(
    document.querySelectorAll(".moo-catalog__toolbar input[type='search']")
  );
  const sectionFilterItems = Array.from(
    document.querySelectorAll("[data-moo-catalog-section-filter]")
  );
  const sectionFilterToggle = document.querySelector(".moo-catalog__status-menu > .btn");
  const catalogSections = Array.from(document.querySelectorAll("[data-moo-catalog-section]"));
  const catalogCards = Array.from(document.querySelectorAll(".moo-catalog__app-card"));
  let selectedCatalogSection = "all";

  const normalize = (value) => value.trim().toLowerCase();

  const filterCatalog = (query = searchControls[0]?.value || "") => {
    const needle = normalize(query);

    searchControls.forEach((control) => {
      if (control.value !== query) {
        control.value = query;
      }
    });

    catalogSections.forEach((section) => {
      const sectionName = section.dataset.mooCatalogSection;
      section.hidden =
        selectedCatalogSection !== "all" && sectionName !== selectedCatalogSection;
    });

    catalogCards.forEach((card) => {
      const matchesText = !needle || normalize(card.textContent).includes(needle);
      const section = card.closest("[data-moo-catalog-section]");
      const matchesSection =
        selectedCatalogSection === "all" ||
        section?.dataset.mooCatalogSection === selectedCatalogSection;
      card.hidden = !matchesText || !matchesSection;
    });

  };

  searchControls.forEach((control) => {
    control.addEventListener("input", () => filterCatalog(control.value));
  });

  sectionFilterItems.forEach((item) => {
    item.addEventListener("click", () => {
      selectedCatalogSection = item.dataset.mooCatalogSectionFilter || "all";
      sectionFilterItems.forEach((option) => {
        const isActive = option === item;
        option.classList.toggle("active", isActive);
        if (isActive) {
          option.setAttribute("aria-current", "true");
        } else {
          option.removeAttribute("aria-current");
        }
      });
      if (sectionFilterToggle) {
        const label = item.textContent.trim();
        sectionFilterToggle.childNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
            node.textContent = label;
          }
        });
      }
      filterCatalog();
    });
  });

  filterCatalog();

  // Command palette: the header search trigger and Cmd/Ctrl+K open a Bootstrap
  // modal that filters catalog pages; arrow keys move the highlight and Enter
  // navigates to the highlighted page.
  const commandModalEl = document.getElementById("catalog-command");
  const commandInput = commandModalEl?.querySelector("input[type='search']");
  const commandItems = Array.from(
    commandModalEl?.querySelectorAll("[data-moo-command-item]") || []
  );
  const commandEmpty = commandModalEl?.querySelector(".moo-catalog__command-empty");
  const commandGroups = Array.from(
    commandModalEl?.querySelectorAll("[data-moo-command-group]") || []
  );
  const searchTrigger = document.querySelector(".moo-catalog__search-trigger");
  let commandActive = -1;

  // Wire the ARIA combobox/listbox relationship so assistive tech follows the
  // highlighted option, not just the CSS `.active` class.
  const commandList = commandModalEl?.querySelector('[role="listbox"]');
  if (commandList && !commandList.id) {
    commandList.id = "catalog-command-list";
  }
  commandItems.forEach((item, index) => {
    if (!item.id) {
      item.id = `catalog-command-item-${index}`;
    }
    item.setAttribute("aria-selected", "false");
  });
  if (commandInput && commandList) {
    commandInput.setAttribute("role", "combobox");
    commandInput.setAttribute("aria-controls", commandList.id);
    commandInput.setAttribute("aria-autocomplete", "list");
    commandInput.setAttribute("aria-expanded", "false");
  }

  const openCommand = () => {
    const Modal = window.bootstrap?.Modal;
    if (commandModalEl && Modal) {
      Modal.getOrCreateInstance(commandModalEl).show();
    }
  };

  const visibleCommandItems = () => commandItems.filter((item) => !item.hidden);

  const setCommandActive = (index) => {
    const items = visibleCommandItems();
    commandItems.forEach((item) => {
      item.classList.remove("active");
      item.setAttribute("aria-selected", "false");
    });
    if (items.length === 0) {
      commandActive = -1;
      commandInput?.removeAttribute("aria-activedescendant");
      return;
    }
    commandActive = ((index % items.length) + items.length) % items.length;
    const current = items[commandActive];
    current.classList.add("active");
    current.setAttribute("aria-selected", "true");
    current.scrollIntoView({ block: "nearest" });
    commandInput?.setAttribute("aria-activedescendant", current.id);
  };

  const filterCommand = (query = commandInput?.value || "") => {
    const needle = normalize(query);
    let visible = 0;
    commandItems.forEach((item) => {
      const matches = !needle || normalize(item.textContent).includes(needle);
      item.hidden = !matches;
      if (matches) {
        visible += 1;
      }
    });
    commandGroups.forEach((group) => {
      const hasVisibleItems = Array.from(
        group.querySelectorAll("[data-moo-command-item]")
      ).some((item) => !item.hidden);
      group.hidden = !hasVisibleItems;
    });
    if (commandEmpty) {
      commandEmpty.hidden = visible !== 0;
    }
    setCommandActive(0);
  };

  searchTrigger?.addEventListener("click", () => openCommand());
  commandInput?.addEventListener("input", () => filterCommand());

  commandInput?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setCommandActive(commandActive + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setCommandActive(commandActive - 1);
    } else if (event.key === "Enter") {
      const target = visibleCommandItems()[commandActive];
      if (target) {
        event.preventDefault();
        window.location.href = target.getAttribute("href");
      }
    }
  });

  commandModalEl?.addEventListener("shown.bs.modal", () => {
    commandInput?.setAttribute("aria-expanded", "true");
    commandInput?.focus();
    commandInput?.select();
    filterCommand();
  });

  commandModalEl?.addEventListener("hidden.bs.modal", () => {
    commandInput?.setAttribute("aria-expanded", "false");
    commandInput?.removeAttribute("aria-activedescendant");
    if (commandInput) {
      commandInput.value = "";
    }
    filterCommand("");
  });

  // Component pages derive their right-side table of contents from rendered
  // example headings. The examples already own stable ids for code toggles and
  // deep links, so new component examples join the TOC without per-page wiring.
  const componentToc = document.querySelector("[data-moo-component-toc]");
  const componentTocNav = componentToc?.querySelector("[data-moo-component-toc-nav]");
  const componentExamples = Array.from(
    document.querySelectorAll(".moo-component-examples > .moo-example[aria-labelledby]")
  );
  if (componentToc && componentTocNav && componentExamples.length > 0) {
    componentExamples.forEach((example) => {
      const titleId = example.getAttribute("aria-labelledby");
      const title = titleId ? document.getElementById(titleId) : null;
      if (!titleId || !title?.textContent?.trim()) {
        return;
      }
      const link = document.createElement("a");
      link.className = "nav-link";
      link.href = `#${titleId}`;
      link.textContent = title.textContent.trim();
      componentTocNav.appendChild(link);
    });
    componentToc.hidden = componentTocNav.children.length === 0;
  }

  const docTocLinks = Array.from(document.querySelectorAll(".moo-doc-toc .nav-link"));
  const docTocTargets = docTocLinks
    .map((link) => {
      const targetId = link.getAttribute("href")?.slice(1);
      const target = targetId ? document.getElementById(targetId) : null;
      return target ? { link, target } : null;
    })
    .filter(Boolean);
  const catalogMain = document.querySelector(".moo-catalog__main");
  let docTocFrame = 0;
  let docTocClickUntil = 0;

  const activateDocTocLink = (activeLink) => {
    docTocTargets.forEach(({ link }) => {
      const isActive = link === activeLink;
      link.classList.toggle("active", isActive);
      if (isActive) {
        link.setAttribute("aria-current", "true");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };

  const setActiveDocTocLink = () => {
    docTocFrame = 0;
    if (docTocTargets.length === 0) {
      return;
    }
    if (Date.now() < docTocClickUntil) {
      return;
    }

    const offset = parseFloat(getComputedStyle(document.documentElement).fontSize) * 6;
    let activeItem = docTocTargets[0];
    docTocTargets.forEach((item) => {
      if (item.target.getBoundingClientRect().top <= offset) {
        activeItem = item;
      }
    });

    activateDocTocLink(activeItem.link);
  };

  const requestDocTocUpdate = () => {
    if (docTocFrame === 0) {
      docTocFrame = window.requestAnimationFrame(setActiveDocTocLink);
    }
  };

  if (docTocTargets.length > 0) {
    docTocTargets.forEach(({ link }) => {
      link.addEventListener("click", () => {
        docTocClickUntil = Date.now() + 2500;
        activateDocTocLink(link);
      });
    });
    setActiveDocTocLink();
    catalogMain?.addEventListener("scroll", requestDocTocUpdate, { passive: true });
    window.addEventListener("resize", requestDocTocUpdate);
    window.addEventListener("hashchange", requestDocTocUpdate);
  }


  document.querySelectorAll(".combobox").forEach((element) => {
    Combobox.getOrCreateInstance(element);
  });

  document.querySelectorAll("[data-moo-copy-page]").forEach((trigger) => {
    trigger.addEventListener("click", async () => {
      const value = trigger.getAttribute("data-moo-copy-value") || window.location.href.split("#")[0];
      const label = trigger.querySelector("[data-moo-copy-page-label]");
      const previousLabel = label?.textContent;

      try {
        await navigator.clipboard.writeText(value);
        if (label) {
          label.textContent = "Copied";
          window.setTimeout(() => { label.textContent = previousLabel; }, 1600);
        }
      } catch {
        if (label) {
          label.textContent = "Copy failed";
          window.setTimeout(() => { label.textContent = previousLabel; }, 1600);
        }
      }
    });
  });

  // Hash navigation and TOC clicks use smooth scrolling in the catalog main
  // pane. If a tab is switched while that smooth scroll is still settling, the
  // browser keeps moving the scroll container and the tab list appears to jump.
  // Capture scroll before pointer/key activation because focusing a visible
  // tab can move the scroll container before Bootstrap emits show.bs.tab.
  // Freeze that pre-focus position for the tab handoff only; the tab panel
  // animation still runs, and normal smooth anchor scrolling resumes after it.
  let pendingCatalogTabScrollTop = null;

  const captureCatalogScrollForTab = () => {
    if (catalogMain) {
      pendingCatalogTabScrollTop = catalogMain.scrollTop;
    }
  };

  const freezeCatalogScrollForTab = () => {
    if (!catalogMain) {
      return;
    }

    const currentScrollTop = pendingCatalogTabScrollTop ?? catalogMain.scrollTop;
    pendingCatalogTabScrollTop = null;
    const previousScrollBehavior = catalogMain.style.scrollBehavior;
    catalogMain.style.scrollBehavior = "auto";
    catalogMain.scrollTop = currentScrollTop;
    window.requestAnimationFrame(() => {
      catalogMain.scrollTop = currentScrollTop;
      window.requestAnimationFrame(() => {
        catalogMain.scrollTop = currentScrollTop;
        window.setTimeout(() => {
          catalogMain.scrollTop = currentScrollTop;
          catalogMain.style.scrollBehavior = previousScrollBehavior;
        }, 180);
      });
    });
  };

  document.addEventListener("pointerdown", (event) => {
    const trigger = event.target;
    if (trigger instanceof Element && trigger.closest(".tabs-list [data-bs-toggle='tab']")) {
      captureCatalogScrollForTab();
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    const trigger = event.target;
    if (
      trigger instanceof Element &&
      trigger.closest(".tabs-list [data-bs-toggle='tab']") &&
      (event.key === "Enter" || event.key === " ")
    ) {
      captureCatalogScrollForTab();
    }
  }, true);

  document.addEventListener("show.bs.tab", (event) => {
    const trigger = event.target;
    if (trigger instanceof Element && trigger.closest(".tabs-list")) {
      freezeCatalogScrollForTab();
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openCommand();
    }
  });

  // Bootstrap appends Modal backdrops directly to <body>. Component previews
  // render examples inside clipped/nested catalog surfaces, so a nested modal
  // can paint underneath its body-level backdrop even though Bootstrap's z-index
  // scale is correct. Portal catalog-owned modals to <body> only while open,
  // then restore their original DOM position after Bootstrap finishes hiding.
  const catalogModalPlaceholders = new WeakMap();

  document.addEventListener("show.bs.modal", (event) => {
    const modal = event.target;
    if (!(modal instanceof HTMLElement) || !modal.classList.contains("modal")) {
      return;
    }
    if (!modal.closest(".moo-catalog") || modal.parentElement === document.body) {
      return;
    }

    const placeholder = document.createComment("moo-modal-placeholder");
    modal.parentNode?.insertBefore(placeholder, modal);
    document.body.appendChild(modal);
    catalogModalPlaceholders.set(modal, placeholder);
  }, true);

  document.addEventListener("hidden.bs.modal", (event) => {
    const modal = event.target;
    if (!(modal instanceof HTMLElement)) {
      return;
    }

    const placeholder = catalogModalPlaceholders.get(modal);
    if (placeholder?.parentNode) {
      placeholder.parentNode.insertBefore(modal, placeholder);
      placeholder.remove();
    }
    catalogModalPlaceholders.delete(modal);
  }, true);

  // Bootstrap creates an Offcanvas backdrop under the panel's parent node. Keep
  // catalog Sheet panels at <body> level before Bootstrap creates an instance so
  // Safari and other browsers dim the same page chrome as Bootstrap's examples.
  const portalCatalogSheet = (sheet) => {
    if (
      !(sheet instanceof HTMLElement) ||
      !sheet.classList.contains("sheet") ||
      sheet.parentElement === document.body
    ) {
      return;
    }

    sheet.dataset.mooCatalogSheet = "true";
    document.body.appendChild(sheet);
  };

  document.addEventListener("click", (event) => {
    const targetElement =
      event.target instanceof Element ? event.target : event.target?.parentElement;
    const trigger = targetElement?.closest?.('[data-bs-toggle="offcanvas"][data-bs-target]');
    const target = trigger?.getAttribute("data-bs-target");
    if (!target?.startsWith("#")) {
      return;
    }
    portalCatalogSheet(document.querySelector(target));
  }, true);

  document.addEventListener("show.bs.offcanvas", (event) => {
    const sheet = event.target;
    if (sheet instanceof HTMLElement && sheet.dataset.mooCatalogSheet === "true") {
      portalCatalogSheet(sheet);
    }
  }, true);

  document.querySelectorAll(".moo-catalog .offcanvas.sheet").forEach(portalCatalogSheet);

  document.querySelectorAll("[data-moo-code-panel]").forEach((panel) => {
    const toggle = panel.querySelector("[data-moo-code-toggle]");
    const copyButton = panel.querySelector("[data-moo-code-copy]");
    const copyStatus = panel.querySelector("[data-moo-copy-status]");
    const scroller = panel.querySelector(".moo-code");
    const code = panel.querySelector("code");

    toggle?.addEventListener("click", () => {
      panel.dataset.expanded = "true";
      scroller.classList.toggle("moo-code--scrolling", scroller.scrollHeight > scroller.clientHeight);
      toggle.setAttribute("aria-expanded", "true");
      copyButton.hidden = false;
    });

    copyButton?.addEventListener("click", async () => {
      let message = "Code copied";

      try {
        await navigator.clipboard.writeText(code.textContent);
      } catch {
        message = "Copy failed";
      }

      copyStatus.textContent = message;
      window.setTimeout(() => { copyStatus.textContent = ""; }, 2000);
    });
  });

  // Tooltip is opt-in per Bootstrap's own contract, so the catalog performs
  // this one explicit init pass. getOrCreateInstance keeps it idempotent if
  // this ever runs more than once against the same trigger (see the Wave 0
  // preflight note: one DOM element may hold only one Bootstrap plugin
  // instance). The public Sidebar module separately owns its state-driven
  // data-moo-sidebar-tooltip anchors, which this catalog pass does not touch.
  const Tooltip = window.bootstrap?.Tooltip;
  if (Tooltip) {
    document
      .querySelectorAll('[data-bs-toggle="tooltip"]')
      .forEach((trigger) => Tooltip.getOrCreateInstance(trigger));
  }

  // Popover is opt-in for the same reason and gets the same idempotent
  // explicit init pass; it is a distinct Bootstrap plugin from Tooltip, so a
  // trigger must never carry both data-bs-toggle values at once (enforced by
  // the button() macro's own fail() guards).
  const Popover = window.bootstrap?.Popover;
  if (Popover) {
    document
      .querySelectorAll('[data-bs-toggle="popover"]')
      .forEach((trigger) => Popover.getOrCreateInstance(trigger));
  }

  // Toast has no Bootstrap data-api click trigger (unlike Modal/Offcanvas),
  // so Bootstrap's own docs recommend wiring a manual click listener that
  // calls .show(). data-moo-toast-target is that wiring, generalized across
  // every toast trigger on the page; it is catalog sugar, not a Bootstrap or
  // public Moo data attribute, and getOrCreateInstance keeps repeated clicks
  // idempotent.
  const Toast = window.bootstrap?.Toast;
  if (Toast) {
    document.addEventListener("click", (event) => {
      const trigger =
        event.target instanceof Element
          ? event.target.closest("[data-moo-toast-target]")
          : null;
      const targetSelector = trigger?.dataset.mooToastTarget || "";
      const targetId = targetSelector.startsWith("#")
        ? targetSelector.slice(1)
        : targetSelector;
      const target = targetId ? document.getElementById(targetId) : null;
      if (target) {
        Toast.getOrCreateInstance(target).show();
      }
    });
  }

  // Bootstrap ships no validation engine of its own -- .needs-validation is
  // its own documented className for the recipe every consuming app is
  // expected to copy: block submit while invalid and add .was-validated so
  // its own :invalid/:invalid-feedback CSS takes over. The catalog's only
  // addition is always calling preventDefault(), since this demo form has
  // no real endpoint to submit to.
  document.querySelectorAll("form.needs-validation").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!form.checkValidity()) {
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  directionButton?.addEventListener("click", () => {
    const direction = root.dir === "rtl" ? "ltr" : "rtl";
    root.dir = direction;
    directionButton.textContent = direction === "rtl" ? "LTR" : "RTL";
  });

  document.querySelectorAll('[data-slot="sidebar-wrapper"]').forEach((element) => {
    Sidebar.getOrCreateInstance(element);
  });

  const tiltTargets = Array.from(document.querySelectorAll("[data-moo-tilt]"));
  const tiltMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

  const resetTilt = (target) => {
    delete target.dataset.mooTiltActive;
    target.style.removeProperty("--moo-tilt-x");
    target.style.removeProperty("--moo-tilt-y");
    target.style.removeProperty("--moo-tilt-shift-x");
    target.style.removeProperty("--moo-tilt-shift-y");
  };

  if (!tiltMotionQuery.matches) {
    tiltTargets.forEach((target) => {
      target.addEventListener("pointermove", (event) => {
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
      target.addEventListener("pointerleave", () => resetTilt(target));
      target.addEventListener("blur", () => resetTilt(target), true);
    });
  }

  tiltMotionQuery.addEventListener?.("change", () => {
    if (tiltMotionQuery.matches) {
      tiltTargets.forEach((target) => resetTilt(target));
    }
  });

  const blockFrameShells = Array.from(
    document.querySelectorAll("[data-moo-block-frame-shell]")
  );

  const resizeBlockFrame = (shell) => {
    const viewport = shell.querySelector("[data-moo-block-frame-viewport]");
    const frame = shell.querySelector("[data-moo-block-frame]");
    const frameWidth = Number(shell.dataset.mooFrameWidth || frame?.getAttribute("width") || 1280);
    const frameHeight = Number(shell.dataset.mooFrameHeight || frame?.getAttribute("height") || 720);

    if (!viewport || !frame || !frameWidth || !frameHeight) {
      return;
    }

    const scale = Math.min(1, viewport.clientWidth / frameWidth);
    frame.style.width = `${frameWidth}px`;
    frame.style.height = `${frameHeight}px`;
    frame.style.transform = `scale(${scale})`;
    viewport.style.height = `${Math.ceil(frameHeight * scale)}px`;
  };

  if (blockFrameShells.length > 0) {
    const resizeBlockFrames = () => {
      blockFrameShells.forEach((shell) => resizeBlockFrame(shell));
    };

    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(resizeBlockFrames);
      blockFrameShells.forEach((shell) => observer.observe(shell));
    }

    blockFrameShells.forEach((shell) => {
      shell.querySelector("[data-moo-block-frame]")?.addEventListener(
        "load",
        () => resizeBlockFrame(shell)
      );
    });
    window.addEventListener("resize", resizeBlockFrames);
    resizeBlockFrames();
  }
})();

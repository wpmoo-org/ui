(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-moo-theme], .moo-catalog__theme-toggle");
  const directionButton = document.querySelector("[data-moo-direction], .moo-catalog__direction-toggle");
  const themeIcons = Array.from(themeButton?.querySelectorAll("[data-moo-theme-icon]") || []);

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
    updateThemeButton();
  });

  updateThemeButton();

  const searchControls = Array.from(
    document.querySelectorAll(".moo-catalog__toolbar input[type='search']")
  );
  const sectionFilter = document.querySelector(".moo-catalog__status-select");
  const catalogSections = Array.from(document.querySelectorAll("[data-moo-catalog-section]"));
  const catalogCards = Array.from(document.querySelectorAll(".moo-catalog__app-card"));

  const normalize = (value) => value.trim().toLowerCase();

  const filterCatalog = (query = searchControls[0]?.value || "") => {
    const needle = normalize(query);
    const selectedSection = sectionFilter?.value || "all";

    searchControls.forEach((control) => {
      if (control.value !== query) {
        control.value = query;
      }
    });

    catalogSections.forEach((section) => {
      const sectionName = section.dataset.mooCatalogSection;
      section.hidden = selectedSection !== "all" && sectionName !== selectedSection;
    });

    catalogCards.forEach((card) => {
      const matchesText = !needle || normalize(card.textContent).includes(needle);
      const section = card.closest("[data-moo-catalog-section]");
      const matchesSection =
        selectedSection === "all" || section?.dataset.mooCatalogSection === selectedSection;
      card.hidden = !matchesText || !matchesSection;
    });

  };

  searchControls.forEach((control) => {
    control.addEventListener("input", () => filterCatalog(control.value));
  });

  sectionFilter?.addEventListener("change", () => filterCatalog());

  // Command palette: the header search trigger and Cmd/Ctrl+K open a Bootstrap
  // modal that filters catalog pages; arrow keys move the highlight and Enter
  // navigates to the highlighted page.
  const commandModalEl = document.getElementById("catalog-command");
  const commandInput = commandModalEl?.querySelector("input[type='search']");
  const commandItems = Array.from(
    commandModalEl?.querySelectorAll("[data-moo-command-item]") || []
  );
  const commandEmpty = commandModalEl?.querySelector(".moo-catalog__command-empty");
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

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openCommand();
    }
  });

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

  const sidebarWrappers = Array.from(
    document.querySelectorAll('[data-slot="sidebar-wrapper"]')
  );
  const SIDEBAR_STORAGE_PREFIX = "moo-sidebar:";
  const SIDEBAR_COLLAPSE_BREAKPOINT = "(min-width: 992px)";

  const syncSidebarTooltips = (wrapper) => {
    const Tooltip = window.bootstrap?.Tooltip;
    if (!Tooltip) {
      return;
    }
    const collapsed =
      window.matchMedia(SIDEBAR_COLLAPSE_BREAKPOINT).matches &&
      wrapper.dataset.mooSidebarState === "collapsed";
    const placement = root.dir === "rtl" ? "left" : "right";
    wrapper.querySelectorAll("[data-moo-sidebar-tooltip]").forEach((button) => {
      // Bootstrap allows only one plugin instance per element (see
      // Data.set in bootstrap/js/dist/dom/data.js). A menu button with its
      // own data-bs-toggle (dropdown/collapse) already owns that element's
      // single instance slot, so a Tooltip constructed on the same node is
      // silently rejected and both plugins log a console error. Anchor the
      // tooltip to the row's <li> wrapper instead, which never owns a
      // competing Bootstrap instance.
      const anchor = button.closest("li") || button;
      const existing = Tooltip.getInstance(anchor);
      if (existing) {
        existing.dispose();
      }
      if (collapsed) {
        new Tooltip(anchor, {
          title: button.getAttribute("data-moo-sidebar-tooltip"),
          placement,
          container: "body",
          trigger: "hover focus",
        });
      }
    });
  };

  const setSidebarState = (wrapper, state, persist = true) => {
    state = state === "collapsed" ? "collapsed" : "expanded";
    wrapper.dataset.mooSidebarState = state;
    const key = wrapper.dataset.mooSidebarKey;
    if (persist && key) {
      try {
        window.localStorage.setItem(SIDEBAR_STORAGE_PREFIX + key, state);
      } catch {
        // Storage is best-effort; ignore private-mode or quota errors.
      }
    }
    syncSidebarControls(wrapper);
    syncSidebarTooltips(wrapper);
  };

  const toggleSidebar = (wrapper) => {
    const collapsed = wrapper.dataset.mooSidebarState === "collapsed";
    setSidebarState(wrapper, collapsed ? "expanded" : "collapsed");
  };

  const isDesktopSidebar = () => window.matchMedia(SIDEBAR_COLLAPSE_BREAKPOINT).matches;

  const syncSidebarControls = (wrapper) => {
    const sidebar = wrapper.querySelector('[data-slot="sidebar"]');
    const isExpanded = isDesktopSidebar()
      ? wrapper.dataset.mooSidebarState === "expanded"
      : sidebar?.classList.contains("show") || false;
    wrapper
      .querySelectorAll("[data-moo-sidebar-trigger], [data-moo-sidebar-rail]")
      .forEach((control) => {
        control.setAttribute("aria-expanded", String(isExpanded));
      });
  };

  const bindSidebarOffcanvas = (wrapper) => {
    const sidebar = wrapper.querySelector('[data-slot="sidebar"]');
    if (!sidebar) {
      return;
    }
    sidebar.addEventListener("shown.bs.offcanvas", () => syncSidebarControls(wrapper));
    sidebar.addEventListener("hidden.bs.offcanvas", () => syncSidebarControls(wrapper));
  };

  directionButton?.addEventListener("click", () => {
    const direction = root.dir === "rtl" ? "ltr" : "rtl";
    root.dir = direction;
    directionButton.textContent = direction === "rtl" ? "LTR" : "RTL";
    sidebarWrappers.forEach((wrapper) => syncSidebarTooltips(wrapper));
  });

  sidebarWrappers.forEach((wrapper) => {
    bindSidebarOffcanvas(wrapper);
    const key = wrapper.dataset.mooSidebarKey;
    let stored = null;
    if (key) {
      try {
        stored = window.localStorage.getItem(SIDEBAR_STORAGE_PREFIX + key);
      } catch {
        stored = null;
      }
    }
    const initialState =
      stored === "collapsed" || stored === "expanded"
        ? stored
        : wrapper.dataset.mooSidebarState === "collapsed"
          ? "collapsed"
          : "expanded";
    setSidebarState(wrapper, initialState, false);
  });

  window.addEventListener("resize", () => {
    sidebarWrappers.forEach((wrapper) => {
      syncSidebarControls(wrapper);
      syncSidebarTooltips(wrapper);
    });
  });

  document.addEventListener("click", (event) => {
    const control = event.target.closest(
      "[data-moo-sidebar-trigger], [data-moo-sidebar-rail]"
    );
    if (!control) {
      return;
    }
    const wrapper = control.closest('[data-slot="sidebar-wrapper"]');
    if (!wrapper) {
      return;
    }
    if (isDesktopSidebar()) {
      event.preventDefault();
      toggleSidebar(wrapper);
      return;
    }
    if (control.matches("[data-moo-sidebar-trigger]")) {
      const sidebar = document.getElementById(control.getAttribute("aria-controls"));
      const Offcanvas = window.bootstrap?.Offcanvas;
      if (sidebar && Offcanvas) {
        Offcanvas.getOrCreateInstance(sidebar).toggle();
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "b") {
      return;
    }
    if (!isDesktopSidebar()) {
      return;
    }
    const wrapper =
      document.querySelector(
        '[data-slot="sidebar-wrapper"][data-moo-sidebar-key]'
      ) || sidebarWrappers[0];
    if (wrapper) {
      event.preventDefault();
      toggleSidebar(wrapper);
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

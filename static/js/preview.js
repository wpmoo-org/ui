(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-moo-theme], .moo-catalog__theme-toggle");
  const directionButton = document.querySelector("[data-moo-direction], .moo-catalog__direction-toggle");
  const sidebarToggle = document.querySelector("[data-moo-sidebar-toggle]");
  const catalogShell = document.querySelector(".moo-catalog");
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

  directionButton?.addEventListener("click", () => {
    const direction = root.dir === "rtl" ? "ltr" : "rtl";
    root.dir = direction;
    directionButton.textContent = direction === "rtl" ? "LTR" : "RTL";
  });

  const updateSidebarToggle = () => {
    const collapsed = catalogShell?.classList.contains("moo-catalog--sidebar-collapsed") || false;
    sidebarToggle?.setAttribute("aria-expanded", String(!collapsed));
  };

  sidebarToggle?.addEventListener("click", () => {
    catalogShell?.classList.toggle("moo-catalog--sidebar-collapsed");
    updateSidebarToggle();
  });

  updateSidebarToggle();

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

  const commandModal = document.getElementById("catalog-command");
  const commandInput = commandModal?.querySelector("input[type='search']");
  const commandItems = Array.from(commandModal?.querySelectorAll("[data-moo-command-item]") || []);
  const commandEmpty = commandModal?.querySelector(".moo-catalog__command-empty");

  const filterCommand = (query = commandInput?.value || "") => {
    const needle = normalize(query);
    let visibleCount = 0;

    commandItems.forEach((item) => {
      const matches = !needle || normalize(item.textContent).includes(needle);
      item.hidden = !matches;
      if (matches) {
        visibleCount += 1;
      }
    });

    if (commandEmpty) {
      commandEmpty.hidden = visibleCount !== 0;
    }
  };

  commandInput?.addEventListener("input", () => filterCommand());

  commandModal?.addEventListener("shown.bs.modal", () => {
    commandInput?.focus();
    commandInput?.select();
    filterCommand();
  });

  commandModal?.addEventListener("hidden.bs.modal", () => {
    if (commandInput) {
      commandInput.value = "";
    }
    filterCommand("");
  });

  document.addEventListener("keydown", (event) => {
    if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "k") {
      return;
    }

    event.preventDefault();
    if (commandModal && window.bootstrap?.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(commandModal).show();
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

  const syncSidebarTooltips = (wrapper) => {
    const Tooltip = window.bootstrap?.Tooltip;
    if (!Tooltip) {
      return;
    }
    const collapsed = wrapper.dataset.mooSidebarState === "collapsed";
    const placement = root.dir === "rtl" ? "left" : "right";
    wrapper.querySelectorAll("[data-moo-sidebar-tooltip]").forEach((button) => {
      const existing = Tooltip.getInstance(button);
      if (collapsed) {
        if (!existing) {
          new Tooltip(button, {
            title: button.getAttribute("data-moo-sidebar-tooltip"),
            placement,
            container: "body",
            trigger: "hover focus",
          });
        }
      } else if (existing) {
        existing.dispose();
      }
    });
  };

  const setSidebarState = (wrapper, state, persist = true) => {
    wrapper.dataset.mooSidebarState = state;
    const key = wrapper.dataset.mooSidebarKey;
    if (persist && key) {
      try {
        window.localStorage.setItem(SIDEBAR_STORAGE_PREFIX + key, state);
      } catch {
        // Storage is best-effort; ignore private-mode or quota errors.
      }
    }
    syncSidebarTooltips(wrapper);
  };

  const toggleSidebar = (wrapper) => {
    const collapsed = wrapper.dataset.mooSidebarState === "collapsed";
    setSidebarState(wrapper, collapsed ? "expanded" : "collapsed");
  };

  sidebarWrappers.forEach((wrapper) => {
    const key = wrapper.dataset.mooSidebarKey;
    let stored = null;
    if (key) {
      try {
        stored = window.localStorage.getItem(SIDEBAR_STORAGE_PREFIX + key);
      } catch {
        stored = null;
      }
    }
    if (stored === "collapsed" || stored === "expanded") {
      setSidebarState(wrapper, stored, false);
    } else {
      syncSidebarTooltips(wrapper);
    }
  });

  document.addEventListener("click", (event) => {
    const control = event.target.closest(
      "[data-moo-sidebar-trigger], [data-moo-sidebar-rail]"
    );
    if (!control) {
      return;
    }
    const wrapper = control.closest('[data-slot="sidebar-wrapper"]');
    if (wrapper) {
      toggleSidebar(wrapper);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "b") {
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
})();

(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-moo-theme]");
  const directionButton = document.querySelector("[data-moo-direction]");

  themeButton?.addEventListener("click", () => {
    const theme = root.dataset.bsTheme === "dark" ? "light" : "dark";
    root.dataset.bsTheme = theme;
    themeButton.textContent = theme === "dark" ? "Light" : "Dark";
  });

  directionButton?.addEventListener("click", () => {
    const direction = root.dir === "rtl" ? "ltr" : "rtl";
    root.dir = direction;
    directionButton.textContent = direction === "rtl" ? "LTR" : "RTL";
  });

  document.querySelectorAll("[data-moo-code-panel]").forEach((panel) => {
    const toggle = panel.querySelector("[data-moo-code-toggle]");
    const copyButton = panel.querySelector("[data-moo-code-copy]");
    const copyStatus = panel.querySelector("[data-moo-copy-status]");
    const code = panel.querySelector("code");

    toggle?.addEventListener("click", () => {
      panel.dataset.expanded = "true";
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
})();

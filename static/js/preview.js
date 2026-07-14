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
})();

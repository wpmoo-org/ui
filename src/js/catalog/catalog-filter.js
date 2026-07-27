const states = new WeakMap();
const normalize = (value) => value.trim().toLowerCase();

export function initCatalogFilter(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const view = root.defaultView || root.ownerDocument?.defaultView;
  const searchControls = Array.from(
    root.querySelectorAll(".moo-catalog__toolbar input[type='search']")
  );
  const filterItems = Array.from(
    root.querySelectorAll("[data-moo-catalog-section-filter]")
  );
  const filterToggle = root.querySelector(".moo-catalog__status-menu > .btn");
  const sections = Array.from(root.querySelectorAll("[data-moo-catalog-section]"));
  const cards = Array.from(root.querySelectorAll(".moo-catalog__app-card"));
  const listeners = [];
  let selectedSection = "all";

  const listen = (target, type, handler) => {
    target.addEventListener(type, handler);
    listeners.push({ target, type, handler });
  };
  const filter = (query = searchControls[0]?.value || "") => {
    const needle = normalize(query);
    searchControls.forEach((control) => {
      if (control.value !== query) {
        control.value = query;
      }
    });
    sections.forEach((section) => {
      section.hidden =
        selectedSection !== "all" &&
        section.dataset.mooCatalogSection !== selectedSection;
    });
    cards.forEach((card) => {
      const section = card.closest("[data-moo-catalog-section]");
      card.hidden =
        Boolean(needle && !normalize(card.textContent).includes(needle)) ||
        Boolean(
          selectedSection !== "all" &&
          section?.dataset.mooCatalogSection !== selectedSection
        );
    });
  };

  searchControls.forEach((control) => {
    listen(control, "input", () => filter(control.value));
  });
  filterItems.forEach((item) => {
    listen(item, "click", () => {
      selectedSection = item.dataset.mooCatalogSectionFilter || "all";
      filterItems.forEach((option) => {
        const active = option === item;
        option.classList.toggle("active", active);
        if (active) {
          option.setAttribute("aria-current", "true");
        } else {
          option.removeAttribute("aria-current");
        }
      });
      if (filterToggle) {
        const label = item.textContent.trim();
        filterToggle.childNodes.forEach((node) => {
          if (node.nodeType === view.Node.TEXT_NODE && node.textContent.trim()) {
            node.textContent = label;
          }
        });
      }
      filter();
    });
  });
  filter();

  const dispose = () => {
    listeners.forEach(({ target, type, handler }) => {
      target.removeEventListener(type, handler);
    });
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

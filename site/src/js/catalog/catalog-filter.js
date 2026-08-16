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
  const multiFilter = root.querySelector("[data-moo-catalog-filter-multi]");
  const sections = Array.from(root.querySelectorAll("[data-moo-catalog-section]"));
  const cards = Array.from(root.querySelectorAll(".moo-catalog__app-card"));
  const listeners = [];
  // Single-select (the Components index): one section at a time, "all"
  // resets. Multi-select (the Examples index): a Set of checked sections,
  // empty means show everything, "Clear filters" empties it.
  let selectedSection = "all";
  const selectedSections = new Set();

  const listen = (target, type, handler) => {
    target.addEventListener(type, handler);
    listeners.push({ target, type, handler });
  };
  const sectionVisible = (section) =>
    multiFilter
      ? selectedSections.size === 0 || selectedSections.has(section)
      : selectedSection === "all" || selectedSection === section;
  const filter = (query = searchControls[0]?.value || "") => {
    const needle = normalize(query);
    searchControls.forEach((control) => {
      if (control.value !== query) {
        control.value = query;
      }
    });
    cards.forEach((card) => {
      const section = card.closest("[data-moo-catalog-section]");
      card.hidden =
        Boolean(needle && !normalize(card.textContent).includes(needle)) ||
        !sectionVisible(section?.dataset.mooCatalogSection);
    });
    // A section heading only stays when at least one of its cards is
    // visible; otherwise a search or filter would leave empty headings
    // behind with nothing under them.
    sections.forEach((section) => {
      section.hidden = !cards.some(
        (card) => card.closest("[data-moo-catalog-section]") === section && !card.hidden
      );
    });
  };

  searchControls.forEach((control) => {
    listen(control, "input", () => filter(control.value));
  });
  if (multiFilter) {
    const checkboxItems = Array.from(
      multiFilter.querySelectorAll("[data-moo-catalog-section-filter]")
    );
    checkboxItems.forEach((input) => {
      listen(input, "change", () => {
        const key = input.dataset.mooCatalogSectionFilter;
        if (input.checked) {
          selectedSections.add(key);
        } else {
          selectedSections.delete(key);
        }
        filter();
      });
    });
    const clear = multiFilter.querySelector("[data-moo-catalog-filter-clear]");
    if (clear) {
      listen(clear, "click", () => {
        checkboxItems.forEach((input) => {
          input.checked = false;
        });
        selectedSections.clear();
        filter();
      });
    }
  } else {
    const filterItems = Array.from(
      root.querySelectorAll("[data-moo-catalog-section-filter]")
    );
    const filterToggle = root.querySelector(".moo-catalog__status-menu > .btn");
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
  }
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

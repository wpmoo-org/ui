const states = new WeakMap();

export function initCardSpacing(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const groups = Array.from(root.querySelectorAll("[data-card-spacing]"));
  const cleanup = [];

  groups.forEach((group) => {
    const card = group.querySelector(".card-spacing-demo");
    if (!card) {
      return;
    }

    const apply = (input) => {
      if (input && input.checked && input.value) {
        card.style.setProperty("--card-spacing", input.value);
      }
    };

    const onInput = (event) => {
      if (event.target instanceof HTMLInputElement && event.target.type === "radio") {
        apply(event.target);
      }
    };

    group.addEventListener("input", onInput);
    cleanup.push(() => group.removeEventListener("input", onInput));
    group
      .querySelectorAll("input[type=radio]")
      .forEach((input) => apply(input));
  });

  const dispose = () => {
    cleanup.forEach((fn) => fn());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

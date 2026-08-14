const states = new WeakMap();

// Auth/Settings example pages each tell visitors their form "does not
// submit anywhere or store any data." Their submit buttons already carry
// no type="submit" (button()'s own default is type="button"), which stops
// a click from submitting -- but a form with exactly one text field and no
// submit button can still be submitted implicitly by pressing Enter in
// that field (Forgot Password is the one page shaped like this). This
// guard closes that gap for the example pages specifically, not sitewide,
// so the Form component's own catalog page can still demonstrate real
// submit-driven validation states.
const SCOPE_SELECTOR = ".moo-auth-page form, [data-moo-example-settings] form";

export function initExamplesForms(root = document) {
  if (states.has(root)) {
    return states.get(root);
  }

  const cleanup = [];
  const forms = Array.from(root.querySelectorAll(SCOPE_SELECTOR));

  forms.forEach((form) => {
    const onSubmit = (event) => event.preventDefault();
    form.addEventListener("submit", onSubmit);
    cleanup.push(() => form.removeEventListener("submit", onSubmit));
  });

  const dispose = () => {
    cleanup.forEach((fn) => fn());
    states.delete(root);
  };
  states.set(root, dispose);
  return dispose;
}

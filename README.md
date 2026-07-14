# Moo UI

Moo UI is a standalone Bootstrap 5.3 component library with a compact,
shadcn-inspired visual language.

The reviewed product scope currently contains the shared catalog shell and
Button. Button Group, Spinner, and every other component remain unimplemented.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python build.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python build.py --watch
```

Serve the repository root in a second terminal:

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173/dist/components/button.html`.

## Source boundaries

Jinja macros are canonical component sources. Each example captures one macro
result and reuses it for both the live preview and displayed copy-paste markup.
Generated `dist/` output is disposable and ignored by Git.

The implementation was written from a clean structure. It does not copy source
from the legacy product repositories or the `tmp/ui-html` pilot.

## Styling contract

- Keep Bootstrap classes and `--bs-*` component variables as the public contract.
- Define shared static shadow and radius scales in `scss/_primary_variables.scss`.
- Keep theme colors in `scss/_tokens_root.scss` and bridge component styles to
  those shared tokens. The test suite rejects literal colors, shadows, and radii
  in `scss/components/`.
- Reserve `.moo-*` selectors for catalog chrome. Product component SCSS styles
  native Bootstrap selectors only and stays inside its component boundary.
- Compose examples from component macros already marked ready in `src/catalog.json`.
  If a required macro is missing, build that dependency first or defer the
  example; do not substitute raw interactive or Bootstrap component markup.
- `render_example` owns example title, description, preview, and copyable code.
  `render_api_reference` owns API Reference layout for every component page.

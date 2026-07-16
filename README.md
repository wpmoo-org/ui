# Moo UI

Moo UI is a standalone Bootstrap 5.3 component library with a compact,
shadcn-inspired visual language.

The reviewed product scope currently contains the shared catalog shell, Button,
Button Group, Card, and the Scroll Fade utility. Other components remain
unimplemented until their dependency macros are ready.

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

Tests are organized by ownership instead of accumulating in one build file:

- `tests/helpers.py` owns shared build and fixture helpers.
- `tests/test_<component>.py` owns one component's public contract.
- `tests/test_catalog.py` owns cross-component composition gates.
- `tests/test_code_examples.py` owns the shared example/source renderer.
- `tests/test_<utility>.py` owns one reusable utility contract.

Add new behavior to its owning module. Keep `tests/test_build.py` limited to
the build entrypoints and shared shell output.

### Verification strategy

- Compare the Bootstrap and shadcn reference pages before implementing a
  component; iterate in the browser for styling, spacing, responsive behavior,
  RTL, and dark mode.
- The permanent suite carries four categories only: build entrypoints, the
  design/composition/selector-ownership gates, the code-renderer and
  source-format contracts, and stable public macro contracts plus
  fail-fast/accessibility guards. Visual and DOM-shape pins are not written
  during the shadcn convergence.
- Acceptance-specific contract coverage is added or expanded after visual and
  behavior approval — at catalog acceptance — without pixel pins.
- For catalog copy, example order, and other documentation-only changes, run
  the build and inspect the rendered page.

Every phase closes with browser review plus the green gate suite and lands as
its own commit.

## Source boundaries

Jinja macros are canonical component sources. Each example captures one macro
result and derives both the live preview and displayed copy-paste markup from
it. The shared example macro normalizes indentation, adds build-time syntax
tokens and line numbers, and never loads a runtime highlighter. Generated
`dist/` output is disposable and ignored by Git.

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
- General visual behavior that is useful beyond one component belongs under
  `scss/utilities/` and `src/pages/utils/`, with one dedicated test module.

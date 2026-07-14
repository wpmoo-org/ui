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

# Contributing to Moo UI

Thanks for helping improve Moo UI. Small, source-backed changes are easiest to
review and merge.

## What Helps

- documentation fixes and clearer examples;
- reduced reproductions for visual, keyboard, focus, or browser issues;
- accessibility observations with the input method or assistive technology used;
- focused component improvements that preserve Bootstrap markup and behavior;
- tests that lock a public contract without freezing incidental wording or DOM.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
env npm_config_cache=/private/tmp/wpmoo-npm-cache npm install
.venv/bin/python build.py
.venv/bin/python dev.py
```

Browse the local catalog at `http://localhost:4173/`.

## Branch And PR Flow

- Work from `dev`; `main` is released through PRs.
- Keep each PR focused on one public concern.
- Do not combine docs copy, runtime behavior, release automation, and version
  bumps unless the maintainer explicitly scopes that release PR.
- Preserve package exports, public URLs, and the Core/Docs boundary unless the
  PR is specifically about those contracts.

## Core / Docs Boundary

Moo UI Core source and package outputs live outside `site/`; `dist/` is the npm
package build. The `site/` tree owns ui.wpmoo.org templates, catalog chrome,
metadata, and preview artwork. Do not move site-only assets into the package or
describe internal Jinja macros as npm APIs.

## Verification

Run the narrowest relevant test first, then expand before asking for review:

```bash
.venv/bin/python build.py
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

For visual or interaction changes, include the browser, device, and viewport you
used. If a component involves Bootstrap JavaScript or optional Moo ESM, include
keyboard and focus-return checks when applicable.

## Public Contract Impact

Call out any change that affects:

- documented classes, selectors, `data-*` attributes, or ARIA relationships;
- package exports and file list;
- CSS load order or scoped `.moo-ui` behavior;
- Bootstrap peer range or plugin ownership;
- optional Combobox or Sidebar ESM lifecycle.

If a change only improves documentation, say that explicitly.

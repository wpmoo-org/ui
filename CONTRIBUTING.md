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

## Release Package

Prepare release archives from the repository root:

```bash
.venv/bin/python build.py --core
.venv/bin/python scripts/package_release.py --pack-destination dist/npm-release
```

The packer preserves checkout sources and public Sass paths. Distributed
SCSS omits silent `//` comments and retains `/* ... */` comments. Expanded
CSS includes section headings; minified CSS retains license notices only.
Component headings belong in their own partials; import aggregates have only
group headings. All CSS outputs start with one license block containing Moo UI
followed by Bootstrap, with a blank line between them.
Sass-only guidance uses silent comments. Public JavaScript is formatted with
the locked esbuild; minified JavaScript keeps readable license notices above
a single-line body while preserving multiline and tagged string values.

The release tier prepares and verifies the archive under `dist/rc-rehearsal/`.
The publish workflow uses that exact archive. Manual publication must also
use an explicit prepared tarball path, with `--tag rc` for prereleases and
`--tag latest` for stable versions. Raw `npm pack` remains an inventory check.

## Verification

Run the narrowest relevant test first, then expand before asking for review:

```bash
.venv/bin/python build.py
.venv/bin/python scripts/run-test-tier.py run quick
.venv/bin/python scripts/run-test-tier.py run browser-smoke  # when browser behavior changed
.venv/bin/python scripts/run-test-tier.py run browser-full   # when certification/browser harnesses changed
.venv/bin/python scripts/run-test-tier.py run release        # before dev -> main, tags, or publish
git diff --check
```

Ordinary `dev` pushes use the changed-files classifier to choose `quick`, a
browser tier, or a capped `browser-full` fallback. Browser tiers are cumulative:
they include the quick source and boundary contracts before running the browser
surface. Release-surface paths and any path the classifier does not recognize
no longer run the full release gate on `dev`; they use the capped browser-full
fallback with targeted package/workflow/certification contract tests when
available. `main`, release tags, publish workflows, manual `release` dispatches,
and `dev` -> `main` PRs always use the release gate.

For visual or interaction changes, include the browser, device, and viewport you
used. If a component involves Bootstrap JavaScript or optional Moo ESM, include
keyboard and focus-return checks when applicable.

## Public Contract Impact

Call out any change that affects:

- documented classes, selectors, `data-*` attributes, or ARIA relationships;
- package exports and file list;
- CSS load order or scoped `.moo-ui` behavior;
- Bootstrap peer range or plugin ownership;
- optional Moo UI ESM lifecycle.

If a change only improves documentation, say that explicitly.

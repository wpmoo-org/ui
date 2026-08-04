<p align="center">
  <img src="https://ui.wpmoo.org/assets/images/readme-hero.webp" alt="Moo UI catalog preview" width="760">
</p>

<p align="center">
  <a href="https://github.com/wpmoo-org/ui/actions/workflows/ui-ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/wpmoo-org/ui/ui-ci.yml?branch=main&label=CI"></a>
  <a href="https://github.com/wpmoo-org/ui"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white"></a>
  <a href="https://www.npmjs.com/package/@wpmoo/ui"><img alt="npm" src="https://img.shields.io/npm/v/@wpmoo/ui?label=npm&logo=npm&color=cb3837"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
</p>

<p align="center"><strong>Bootstrap markup. shadcn feel.</strong></p>

<p align="center">
  Moo UI is a Bootstrap 5.3-native component system with a restrained,
  shadcn-inspired visual language.
</p>

<p align="center">
  <a href="https://ui.wpmoo.org/"><strong>Explore the catalog »</strong></a> ·
  <a href="#try-it-in-30-seconds">Try it in 30 seconds</a> ·
  <a href="https://github.com/wpmoo-org/ui/issues">Report an issue</a>
</p>

# Moo UI

Moo UI preserves Bootstrap markup, variables, and JavaScript plugins wherever
Bootstrap already provides the contract. For patterns Bootstrap does not
provide, Moo UI adds small documented extensions, including optional ESM for
Combobox, Context Menu, DataTable, and Sidebar.

- **CSS-first.** Most components need only the stylesheet and ordinary HTML.
- **Bootstrap owns native behavior.** Keep using Bootstrap's bundle for its
  Dropdown, Modal, Offcanvas, Tooltip, Popover, Toast, and other plugins.
- **Moo extends verified gaps.** Optional Moo ESM is explicit and
  side-effect-free; importing it never scans the document automatically.
- **Adopt all at once or gradually.** Use the full Bootstrap build or scope the
  Moo component layer to a `.moo-ui` boundary.

## Try It in 30 Seconds

The quick demo intentionally follows the floating npm tag:

```html
<link rel="stylesheet"
      href="https://unpkg.com/@wpmoo/ui@latest/dist/assets/css/moo-ui.css">

<button type="button" class="btn btn-primary">Create workspace</button>
```

`moo-ui.css` is a complete Bootstrap CSS build with Moo UI defaults. Use it
instead of another Bootstrap stylesheet, not in addition to one.

## Runtime Ownership

| Surface | Runtime owner | What to load |
| --- | --- | --- |
| Static HTML and CSS components | Browser + Bootstrap markup | `moo-ui.css`, or Bootstrap CSS followed by scoped `moo.css` |
| Dropdown, Modal, Offcanvas, Tooltip, Popover, Toast, and other Bootstrap plugins | Bootstrap | Bootstrap's JavaScript bundle and documented initialization |
| Combobox | Optional Moo ESM | `@wpmoo/ui/combobox.js`, then explicit initialization |
| Context Menu pointer and keyboard invocation | Optional Moo ESM, composed with Bootstrap Dropdown | `@wpmoo/ui/context-menu.js`, then explicit initialization |
| DataTable sorting, filtering, selection, pagination, and responsive card sync | Optional Moo ESM, composed with Bootstrap Table and controls | `@wpmoo/ui/datatable.js`, then explicit initialization |
| Sidebar state and responsive coordination | Optional Moo ESM, composed with Bootstrap plugins | `@wpmoo/ui/sidebar.js`, then explicit initialization |

Moo UI does not replace Bootstrap plugins and does not publish a mandatory
aggregate JavaScript runtime.

## Install

```bash
npm install @wpmoo/ui bootstrap
```

### Full replacement

Use the complete Moo UI Bootstrap build instead of Bootstrap's stylesheet:

```js
import "@wpmoo/ui/moo-ui.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js"; // only when plugins are used
```

### Scoped gradual adoption

Keep the existing Bootstrap stylesheet, load the scoped Moo layer after it, and
wrap only the area being migrated:

```js
import "bootstrap/dist/css/bootstrap.min.css";
import "@wpmoo/ui/moo.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js"; // only when plugins are used
```

```html
<div class="moo-ui">
  <button type="button" class="btn btn-primary">Create workspace</button>
</div>
```

### Optional Moo ESM

Initialize only the documented behavior gaps you use:

```js
import Combobox from "@wpmoo/ui/combobox.js";
import ContextMenu from "@wpmoo/ui/context-menu.js";
import DataTable from "@wpmoo/ui/datatable.js";
import Sidebar from "@wpmoo/ui/sidebar.js";

Combobox.getOrCreateInstance(document.querySelector(".combobox"));
ContextMenu.getOrCreateInstance(document.querySelector(".context-menu"));
DataTable.getOrCreateInstance(document.querySelector(".datatable"));
Sidebar.getOrCreateInstance(document.querySelector('[data-slot="sidebar-wrapper"]'));
```

See the [Installation guide](https://ui.wpmoo.org/installation/) for CDN
recipes, load order, and troubleshooting.

## Choose an Adoption Path

| Situation | Recommended path |
| --- | --- |
| New page or whole application | Replace Bootstrap CSS with `moo-ui.css`. |
| Existing Bootstrap application | Load `moo.css` after Bootstrap CSS and add `.moo-ui` around migrated regions. |
| Static page with no interactive plugins | Load CSS only. |
| Page using Bootstrap plugins | Keep Bootstrap's bundle and its documented initialization. |
| Page using Combobox, Context Menu, DataTable, or Sidebar | Add only the corresponding optional Moo ESM module. |

## Public Package Surface

`@wpmoo/ui` exports exactly these public entrypoints:

| Export | Purpose |
| --- | --- |
| `@wpmoo/ui/moo-ui.css` | Full expanded CSS build |
| `@wpmoo/ui/moo-ui.min.css` | Full minified CSS build |
| `@wpmoo/ui/moo.css` | Scoped expanded component layer for `.moo-ui` |
| `@wpmoo/ui/moo.min.css` | Scoped minified component layer |
| `@wpmoo/ui/combobox.js` | Optional Combobox ESM lifecycle |
| `@wpmoo/ui/context-menu.js` | Optional Context Menu ESM lifecycle |
| `@wpmoo/ui/datatable.js` | Optional DataTable ESM lifecycle |
| `@wpmoo/ui/sidebar.js` | Optional Sidebar ESM lifecycle |
| `@wpmoo/ui/certification.json` | Versioned support/evidence manifest |
| `@wpmoo/ui/package.json` | Package metadata |

The tarball also contains `README.md`, `LICENSE`, and `ASSET_LICENSE.md`. It
does not publish catalog templates, preview artwork, catalog JavaScript, SCSS
source, or a Sass facade. Internal Sass partials and
Jinja macros are repository build tools, not npm APIs.

## Why Bootstrap Teams Try It

- Keep server-rendered HTML, Bootstrap classes, and familiar plugin behavior.
- Apply a restrained product rhythm to forms, overlays, navigation, data
  display, and application shells.
- Inspect static rendered examples and copy the resulting HTML contracts.
- Start with one scoped region or replace the full stylesheet after review.

Representative components include Button, Field, Table, DataTable, Dialog,
Toast, Sheet, Combobox, Context Menu, and Sidebar. Browse the [component catalog](https://ui.wpmoo.org/components/)
and composed [blocks](https://ui.wpmoo.org/blocks/).

## Designed, Not Just Restyled

The README uses original WPMoo preview artwork stored under
`site/static/images/`; those files are source assets for the public catalog and
are not part of the npm package.

<p align="center">
  <a href="https://ui.wpmoo.org/components/button/"><picture><source media="(prefers-color-scheme: dark)" srcset="https://ui.wpmoo.org/assets/images/readme/button-dark.svg"><img src="https://ui.wpmoo.org/assets/images/readme/button-light.svg" alt="Button preview" width="31%"></picture></a>
  <a href="https://ui.wpmoo.org/components/dialog/"><picture><source media="(prefers-color-scheme: dark)" srcset="https://ui.wpmoo.org/assets/images/readme/dialog-dark.svg"><img src="https://ui.wpmoo.org/assets/images/readme/dialog-light.svg" alt="Dialog preview" width="31%"></picture></a>
  <a href="https://ui.wpmoo.org/components/sidebar/"><picture><source media="(prefers-color-scheme: dark)" srcset="https://ui.wpmoo.org/assets/images/readme/sidebar-dark.svg"><img src="https://ui.wpmoo.org/assets/images/readme/sidebar-light.svg" alt="Sidebar preview" width="31%"></picture></a>
</p>

## Status And Support

Moo UI is in the `0.x` series. Current package: `@wpmoo/ui@0.7.1`. The
package's certification manifest currently has `preview` status; catalog
availability is WPMoo-maintained preview evidence, not independent or
accredited certification. Read [Support & Evidence](https://ui.wpmoo.org/support/)
for the Bootstrap range, browser policy, maturity definitions, limitations, and
release evidence. Complete release notes are on
[GitHub Releases](https://github.com/wpmoo-org/ui/releases).

## Contributing

Small documentation corrections, reduced reproductions, accessibility checks,
and bounded component improvements are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md), choose an
[issue type](https://github.com/wpmoo-org/ui/issues/new/choose), and review the
[Code of Conduct](CODE_OF_CONDUCT.md) and [security policy](SECURITY.md).

## Repository Layout And Development

Moo UI Core is published from the repository root. Core source and package
outputs live outside `site/`; `dist/` is the package build. The `site/` tree
owns ui.wpmoo.org documentation, catalog chrome, public metadata, and protected
preview artwork; it builds to `site-dist/`.

```bash
.venv/bin/python build.py
.venv/bin/python dev.py
.venv/bin/python -m unittest discover -s tests -v
```

Browse the local catalog at `http://localhost:4173/` while `dev.py` runs.

## Licensing

Moo UI source code is MIT licensed. WPMoo-generated visual assets under
`site/static/images/` remain separately protected as described in
`ASSET_LICENSE.md`. Vendored dependencies retain their original licenses; see
`LICENSE`, `ASSET_LICENSE.md`, and `THIRD_PARTY_NOTICES.md`.

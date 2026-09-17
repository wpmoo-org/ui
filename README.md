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

Moo UI gives Bootstrap 5.3 applications a calmer, shadcn-inspired product
surface without asking teams to abandon the markup, variables, and plugin
contracts they already use.

It is built for server-rendered products, admin screens, dashboards, and SaaS
interfaces where Bootstrap remains the public contract but the default visual
language needs to feel more current.

- **Bootstrap-native.** Keep familiar classes, form markup, layout utilities,
  and Bootstrap JavaScript where Bootstrap already owns the behavior.
- **CSS-first.** Most components need only one stylesheet and ordinary HTML.
- **Gradual when needed.** Use the full build or scope Moo UI inside a
  `.moo-ui` boundary while an existing Bootstrap app migrates piece by piece.
- **Explicit runtime.** Optional Moo UI behavior loads through ESM entrypoints
  only when a component needs behavior Bootstrap does not provide.

## Try It in 30 Seconds

The quick demo intentionally follows the floating npm tag:

```html
<link rel="stylesheet"
      href="https://unpkg.com/@wpmoo/ui@latest/dist/assets/css/moo-ui.css">

<button type="button" class="btn btn-primary">Create workspace</button>
```

`moo-ui.css` is a complete Bootstrap CSS build with Moo UI defaults. Use it
instead of another Bootstrap stylesheet, not in addition to one.
It emits Moo UI's root/body theme tokens before Bootstrap's reboot body rules;
if you persist dark or system mode, set `data-bs-theme` synchronously in the
head before this stylesheet loads.

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

### Theme ownership and first paint

Resolve the initial `light` or `dark` value on the server whenever the host
knows the request or session preference. Put it on the first application owner;
keep `lang` and the document's default `dir` on `html`:

```html
<!-- Server-resolved document: no prepaint required. -->
<html lang="en" dir="ltr">
  <body>
    <div class="moo-ui" data-bs-theme="dark" data-moo-document-owner="true">
      <!-- Moo UI application -->
    </div>
  </body>
</html>
```

For a static or strict-CSP host without an inline bootstrap, keep the classic
external asset as the root's first child. An embedded owner uses explicit keys
when it needs independent browser persistence:

```html
<!-- Static or strict-CSP fallback: classic script is the root's first child. -->
<div class="moo-ui" data-bs-theme="light" data-moo-theme-key="portal:theme">
  <script src="/vendor/@wpmoo/ui/theme-prepaint.js"></script>
  <!-- embedded Moo UI fragment -->
</div>
```

On a first visit, a static host without a known server preference can only
correct a browser-only preference after the external asset is fetched, so that
correction may be visible. The server value remains the deterministic fallback;
an external fetch cannot guarantee zero flash in this profile. The published
asset is available as `@wpmoo/ui/theme-prepaint.js`.

### Optional runtime

```js
import MooUI from "@wpmoo/ui/moo-ui.js";

const combobox = document.querySelector(".combobox");
if (combobox) {
  MooUI.Combobox.getOrCreateInstance(combobox);
}
```

The runtime bundle is optional and side-effect-free. Import the aggregate
`@wpmoo/ui/moo-ui.js` entrypoint, or import only the component module you use.
See the [Installation guide](https://ui.wpmoo.org/installation/) for npm, CDN,
Sass, Bootstrap JavaScript, and ESM recipes.

## Why Teams Try It

- Keep server-rendered HTML, Bootstrap classes, and familiar plugin behavior.
- Apply a restrained product rhythm to forms, overlays, navigation, data
  display, and application shells.
- Inspect static rendered examples and copy the resulting HTML contracts.
- Start with one scoped region or replace the full stylesheet after review.

Browse the [component catalog](https://ui.wpmoo.org/components/), composed
[blocks](https://ui.wpmoo.org/blocks/), and full
[examples](https://ui.wpmoo.org/examples/).

## Designed, Not Just Restyled

Moo UI is tuned for product interfaces: compact controls, quiet cards,
predictable overlays, readable forms, and data-heavy screens that still feel
calm.

<p align="center">
  <a href="https://ui.wpmoo.org/components/button/"><picture><source media="(prefers-color-scheme: dark)" srcset="https://ui.wpmoo.org/assets/images/readme/button-dark.svg"><img src="https://ui.wpmoo.org/assets/images/readme/button-light.svg" alt="Button preview" width="31%"></picture></a>
  <a href="https://ui.wpmoo.org/components/dialog/"><picture><source media="(prefers-color-scheme: dark)" srcset="https://ui.wpmoo.org/assets/images/readme/dialog-dark.svg"><img src="https://ui.wpmoo.org/assets/images/readme/dialog-light.svg" alt="Dialog preview" width="31%"></picture></a>
  <a href="https://ui.wpmoo.org/components/sidebar/"><picture><source media="(prefers-color-scheme: dark)" srcset="https://ui.wpmoo.org/assets/images/readme/sidebar-dark.svg"><img src="https://ui.wpmoo.org/assets/images/readme/sidebar-light.svg" alt="Sidebar preview" width="31%"></picture></a>
</p>

## Status And Support

Moo UI is preparing the `1.0.0-rc.8` release candidate. Public exports, package boundaries, browser support, and release evidence live in [Support & Evidence](https://ui.wpmoo.org/support/).
Complete release notes are on
[GitHub Releases](https://github.com/wpmoo-org/ui/releases).

## Contributing

Small documentation corrections, reduced reproductions, accessibility checks,
and bounded component improvements are welcome. The
[Contributing guide](https://ui.wpmoo.org/contributing/) covers local
development, project boundaries, workflow, and issue types.

## Repository Layout And Development

Development setup and repository boundary notes live in the
[Contributing guide](https://ui.wpmoo.org/contributing/). Consumer install
paths live in the [Installation guide](https://ui.wpmoo.org/installation/).

## Licensing

Moo UI source code is MIT licensed. License details live in
[LICENSE](LICENSE) and the [License page](https://ui.wpmoo.org/license/).
Asset terms live in [ASSET_LICENSE.md](ASSET_LICENSE.md); dependency notices
live in the
[version-pinned third-party notices](https://github.com/wpmoo-org/ui/blob/v1.0.0-rc.8/THIRD_PARTY_NOTICES.md).

# Third-Party Notices

## Bootstrap

Moo UI vendors the official `twbs/bootstrap` v5.3.3 SCSS source and bundled
JavaScript. Bootstrap is licensed under the MIT License; the bundled license is
stored at `vendor/bootstrap/LICENSE`.

Bootstrap's component and Button documentation are behavior, semantics, and
accessibility references for this product.

## shadcn/ui

Moo UI is designed for server-rendered interfaces that keep Bootstrap markup as
the durable contract. shadcn/ui is used as a visual-intent and catalog-coverage
reference. If you are building React and Tailwind applications, use shadcn/ui
directly: https://ui.shadcn.com/

## Lucide

Moo UI vendors a build-time icon metadata subset from Iconify's Lucide icon
set at `src/icons/lucide-icons.json` and renders selected Lucide icons into the
generated catalog. Lucide is licensed under the ISC License. The source
metadata identifies the Lucide project, its contributors, and the upstream
license URL. The root favicon set (`favicon.svg`, `favicon.ico`,
`apple-touch-icon.png`, `icon-192.png`, and `icon-512.png`) uses the Lucide
Blocks geometry and remains covered by the same ISC license notice.

## Geist

Moo UI vendors `Geist-Variable.woff2` for catalog chrome typography only.
Geist is licensed under the SIL Open Font License 1.1 (`OFL-1.1`); the bundled
license is stored at `vendor/geist/LICENSE`.

## Chart.js

Moo UI bundles Chart.js into the published `@wpmoo/ui` ESM outputs at build time.

- **Library:** Chart.js
- **Version:** 4.5.1
- **License:** MIT
- **Source:** <https://github.com/chartjs/Chart.js>
- **Copyright:** Copyright (c) 2014-2024 Chart.js contributors
- **Bundled outputs:** `dist/js/chart.js` (canonical), `dist/js/chart.min.js` (minified)

Only the JavaScript runtime is bundled. Chart.js's default CSS is not imported
or shipped.

## WPMoo visual assets

WPMoo-generated visual assets, including image assets under `site/static/images/`,
are original WPMoo work and are not licensed under MIT unless explicitly
stated. See `ASSET_LICENSE.md`.

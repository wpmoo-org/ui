# Third-Party Notices

Moo UI's own MIT license is kept separately in `LICENSE`. The full Moo CSS
includes Bootstrap-derived styles. Catalog-only assets and optional external
Chart vendors have separate distributions and licenses as described below.

## Bootstrap

Moo UI vendors the official `twbs/bootstrap` v5.3.3 SCSS source and bundled
JavaScript. Bootstrap is licensed under the MIT License; the bundled license is
stored at `vendor/bootstrap/LICENSE`.

The MIT License (MIT)

Copyright (c) 2011-2024 The Bootstrap Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

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

Chart.js4.6.1 is an external optional peer of Moo UI, not embedded in either
`dist/js/chart.js` or `dist/js/chart.min.js`. These files contain the MooChart
adapter. Consumers install Chart.js separately or serve its native ESM files
with an import map. The catalog serves exact locked files separately under
`vendor/chart.js/`, including its unchanged `LICENSE.md`.

- **License:** MIT
- **Source and license:** <https://github.com/chartjs/Chart.js/blob/v4.6.1/LICENSE.md>

## @kurkle/color

Color0.3.4 is Chart.js's own dependency, not embedded in the Moo npm archive.
The catalog serves its native ESM file and unchanged license separately under
`vendor/@kurkle/color/`. npm consumers receive it through their Chart.js install.

- **License:** MIT
- **Source and license:** <https://github.com/kurkle/color/blob/v0.3.4/LICENSE.md>

## WPMoo visual assets

WPMoo-generated visual assets, including image assets under `site/static/images/`,
are original WPMoo work and are not licensed under MIT unless explicitly
stated. See the
[repository visual asset license](https://github.com/wpmoo-org/ui/blob/v2.0.0/ASSET_LICENSE.md).
These assets and their license file are not included in the npm package.

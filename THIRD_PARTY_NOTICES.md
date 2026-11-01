# Third-Party Notices

The npm package bundles Chart.js and `@kurkle/color`; their complete license
texts appear below. Other entries describe repository and catalog references
or assets, which are not included in the npm package. Moo UI's own MIT license
is kept separately in `LICENSE`.

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
- **Version:** 4.6.1
- **License:** MIT
- **Source:** <https://github.com/chartjs/Chart.js>
- **Copyright:** Copyright (c) 2014-2024 Chart.js contributors
- **Bundled outputs:** `dist/js/chart.js` (canonical), `dist/js/chart.min.js` (minified)

Only the JavaScript runtime is bundled. Chart.js's default CSS is not imported
or shipped.

The complete upstream MIT license is retained below in this published notices
file.
Both standalone Chart variants carry their bundled dependency notices before
executable code. The aggregate loads the standalone Chart module on demand.

### Chart.js license text

The MIT License (MIT)

Copyright (c) 2014-2024 Chart.js Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## @kurkle/color

Chart.js bundles `@kurkle/color` v0.3.4 into the same standalone Chart outputs.
It is licensed under MIT, with copyright belonging to Jukka Kurkela. Its
original MIT license text is retained below in this published notices file;
the upstream copyright notice is preserved in both Chart output headers.

- **Source:** <https://github.com/kurkle/color>

### @kurkle/color license text

The MIT License (MIT)

Copyright (c) 2018-2024 Jukka Kurkela

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## WPMoo visual assets

WPMoo-generated visual assets, including image assets under `site/static/images/`,
are original WPMoo work and are not licensed under MIT unless explicitly
stated. See the
[repository visual asset license](https://github.com/wpmoo-org/ui/blob/v1.6.0/ASSET_LICENSE.md).
These assets and their license file are not included in the npm package.

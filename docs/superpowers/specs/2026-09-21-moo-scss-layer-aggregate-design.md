# Moo Sass Layer Aggregate Boundary

## Status

Implemented in the RC8 App/Sidebar boundary refactor.

## Intent

Make the internal Sass layer boundaries match the public HTML architecture:

- `components` contains component styles only.
- `layouts` contains App/Page shell geometry.
- `foundations` contains shared foundation rules and the scoped composition
  boundary.
- `utilities` contains opt-in utility selectors such as scroll fade.

The published `./scss/components` export path remains present. Its source
facade becomes component-only; no new public Sass export is added.

## Current problem

`scss/_components.scss` currently imports Bootstrap and Moo components, but also
imports `foundations/focus`, `utilities/scroll_fade`, and `layouts/app`. That
makes the filename describe neither its ownership nor the layer contract.

## Design

1. Keep `scss/_components.scss` as the existing published facade, but remove
   its foundation, utility, and layout imports. It will retain only the
   Bootstrap component imports and `components/*` Moo component imports.
2. Keep `scss/layouts/_app.scss` as the App layout owner. It is imported only
   by the scoped composition boundary.
3. Make `scss/foundations/_scope.scss` the explicit composition boundary. Its
   scoped block will import the component facade, foundation focus rules,
   scroll-fade utilities, App layout rules, and theme form rules in one
   documented layer order.
4. Keep `package.json` exports unchanged. Update the public Sass contract,
   source-inventory tests, and ownership tests to assert the new meaning of
   `./scss/components`.
5. Do not change Odoo or Portal source in this refactor. If the compiled CSS
   bytes change because the import order is made layer-correct, record that
   explicitly and synchronize downstream artifacts only as a separate,
   verified artifact step.

## Invariants

- No layout selector lives under `scss/components/`.
- No foundation or utility import lives in `scss/_components.scss`.
- The public `./scss/components` path still resolves from a clean consumer.
- `moo-core.scss` and `moo-ui.scss` remain import-only public entrypoints.
- The full scoped build still contains the App shell, focus rules, and
  scroll-fade rules.
- Boundary and package checks remain fail-closed.

## Verification

The implementation is verified by the component, layout, catalog, package, and
workspace boundary checks. The final commands and their recorded results are:

- [x] `.venv/bin/python3 -m unittest tests.test_catalog.CatalogContractTests.test_app_main_does_not_own_vertical_scroll_below_the_page_header tests.test_layout_registry tests.test_blocks tests.test_layouts tests.test_sidebar tests.test_style_equivalence` — 99 tests pass (`OK`).
- [x] `python3 scripts/verify_package_contents.py` — the package manifest matches
  the approved package boundary.
- [x] From the workspace root, `python3 .agent/tools/verify_moo_odoo_boundaries.py --workspace-root .` — the workspace Moo/Odoo boundary gate reports
  `OK`.
- [x] `git diff --check` — no whitespace errors.

For broader context, `.venv/bin/python3 -m unittest tests.test_catalog` reports
`Ran 206 tests` with `2 failures` and `1 skipped`: the existing
`sidebar-account-menu__header` ownership contract and the legacy
`id="sidebar"` Layout anchor contract. No issue references are attached to
those failures; they are outside this Sass aggregate change and are not
included in the focused verification command above.

The public Sass entrypoints remain import-only, and the normalized `moo.css` and
`moo-ui.css` baselines are recorded in the test fixtures after the intentional
layer-order refactor.

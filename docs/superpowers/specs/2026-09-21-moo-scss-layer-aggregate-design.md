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

- Add a RED ownership test before changing the aggregate.
- Run the component/layout/foundation contract tests and package tests.
- Build `moo.css` and `moo-ui.css`; compare selector/content output with the
  pre-change artifacts and record any intentional ordering-only hash change.
- Run the UI package verifier and workspace boundary gate.

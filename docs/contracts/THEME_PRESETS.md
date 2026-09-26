# Theme Preset Contract

Moo UI theme presets are additive CSS custom-property overrides loaded after
`moo-ui.css`. They do not require JavaScript at runtime, and exported preset CSS
must never use catalog-only selectors such as `data-moo-catalog-*`.

The JSON sidecar stores the normalized choices that produced the CSS. It is a
portable handoff format for future adapters and tooling, not a runtime
dependency for applying a preset.

Presets complement a resolved Moo UI owner; they do not create a second theme
source on `html` or `body`, and they never replace Bootstrap's
`data-bs-theme="light|dark"` attribute.

## Schema Fields

<!-- theme-preset-schema-fields:start -->
```json
[
  "schemaVersion",
  "mooUiVersion",
  "baseColor",
  "themeColor",
  "chartColor",
  "headingFont",
  "bodyFont",
  "radius"
]
```
<!-- theme-preset-schema-fields:end -->

## Schema Enums

<!-- theme-preset-schema-enums:start -->
```json
{
  "baseColor": ["neutral", "stone", "zinc", "mauve", "olive", "mist", "taupe"],
  "themeColor": ["neutral", "blue", "azure", "indigo", "purple", "orange", "pink", "red", "yellow", "lime", "green", "teal", "cyan"],
  "chartColor": ["neutral", "blue", "azure", "indigo", "purple", "orange", "pink", "red", "yellow", "lime", "green", "teal", "cyan"],
  "headingFont": ["default", "geist", "system"],
  "bodyFont": ["default", "geist", "system"],
  "radius": ["default", "none", "small", "medium", "large"]
}
```
<!-- theme-preset-schema-enums:end -->

## Schema Decisions

Schema version `1` treats sidecars with `"radius": "compact"` as legacy input
and normalizes that value to `"small"`. The normalized sidecar preserves
`"small"`; `"compact"` is not emitted and stays outside the public radius enum.
Adapters must apply this `"compact"` -> `"small"` migration before the generic
unknown-enum fallback, so a legacy `"compact"` resolves to `"small"` and never
falls through to the default radius. This adapter migration takes precedence
over unknown-enum handling; there is no known drift between the documented
guidance and committed behavior. This normalization lives in
`normalizeThemeBuilderState()` in `site/src/js/catalog/theme-builder-schema.js`
and is locked by the focused normalization and export tests in
`tests/test_catalog_js.py`.

## Owner Boundary And Export Scopes

A resolved owner is exactly
`.moo-ui[data-bs-theme="light"], .moo-ui[data-bs-theme="dark"]`. For a full
document, one such owner is the first application element in `body`; `lang`
and the document default `dir` stay on `html`. An embedded host may put the
same owner at its fragment boundary and may use `dir` on that owner for a
subtree override. Nested resolved owners are independent token contexts.

A class-only `.moo-ui`, including a direct child carrying the private
`data-moo-overlay-host` marker, is not a resolved owner. It inherits
the nearest resolved owner's tokens and direction. The generic portal host is
private implementation plumbing, not a preset selector or public root option.

`serializeThemeBuilderPresetCss()` accepts only two scopes:

- `owner` requires a runtime-generated `data-moo-theme-builder-owner` marker
  on a resolved `.moo-ui` owner and emits rules only for that owner and its
  dark-mode variant. It rejects arbitrary selector input and a missing or
  invalid marker.
- `standalone` is the portable export profile. It emits the explicit
  `:root`/`[data-bs-theme="light"]` and `[data-bs-theme="dark"]` compatibility
  selectors for a host that deliberately owns its whole document theme.

Owner-scoped preview styles are appended beneath the resolved owner and must
not alter sibling or nested owners. Standalone preset CSS belongs after
`moo-ui.css`; a host must choose the profile that matches its ownership
boundary rather than applying a standalone export indiscriminately inside an
embedded page.

## First Paint And Persistence

The server always emits a resolved `light` or `dark` `data-bs-theme` value on
the owner. The public owner bootstrap applies `stored > server > fallback`,
resolves a stored `system` preference before it writes that owner attribute,
and finishes with `data-moo-state="ready"` on the owner. The default shared
`moo:theme`/`moo:direction` keys are valid only for a document with one
top-level owner; independent nested or sibling owners need explicit
`data-moo-theme-key` and `data-moo-direction-key` values.

There are two supported first-paint profiles:

- A full static document that must restore browser-only preference without a
  visible mismatch renders the canonical `state.js` source inline as
  the owner's first child, before visible Moo content. A strict CSP must
  authorize those exact bytes with a nonce or hash. The renderer must use the
  canonical source rather than maintain a second theme resolver.
- An embedded host, or a full document whose strict CSP disallows inline
  bootstrap, server-resolves the owner attribute and may use the external,
  non-deferred `state.js` asset as an owner-local fallback. An
  external fetch cannot guarantee zero flash when the only differing value is
  in browser storage, so the server value is the deterministic fallback for
  this profile.

Neither profile mirrors Bootstrap theme state to `html` or `body`. The
bootstrap updates `html[dir]` only for the complete-document owner and uses an
owner `dir` only for embedded subtree overrides. `blocking="render"` is not a
portable replacement: it is a head-only render-blocking mechanism and is not
the owner-local bootstrap contract.

The catalog's persisted Theme Builder prepaint is private site behavior. It
normalizes storage into private `data-moo-catalog-theme-builder-*` attributes
on the owner and applies the generated catalog stylesheet; it is neither a
package export nor a cross-host theme API.

## Public Token Allow-List

<!-- theme-preset-public-token-allow-list:start -->
```json
[
  "--bs-body-bg",
  "--bs-body-color",
  "--bs-body-font-family",
  "--bs-border-color",
  "--bs-border-radius",
  "--bs-border-radius-lg",
  "--bs-border-radius-sm",
  "--bs-border-radius-xl",
  "--bs-border-radius-xxl",
  "--bs-card-bg",
  "--bs-card-border-color",
  "--bs-focus-ring-color",
  "--bs-link-color",
  "--bs-link-hover-color",
  "--bs-primary",
  "--bs-primary-rgb",
  "--bs-secondary-bg",
  "--bs-secondary-color",
  "--bs-tertiary-bg",
  "--moo-border",
  "--moo-chart-1",
  "--moo-chart-2",
  "--moo-chart-3",
  "--moo-chart-4",
  "--moo-chart-5",
  "--moo-foreground",
  "--moo-heading-font-family",
  "--moo-muted-foreground",
  "--moo-muted-surface",
  "--moo-primary",
  "--moo-primary-foreground",
  "--moo-primary-foreground-dark",
  "--moo-ring",
  "--moo-sidebar",
  "--moo-sidebar-accent",
  "--moo-sidebar-border",
  "--moo-sidebar-foreground",
  "--moo-surface"
]
```
<!-- theme-preset-public-token-allow-list:end -->

The allow-list above is the current implementation surface, not a promise that
every related Bootstrap companion token is covered. `--moo-surface`,
`--moo-sidebar-*`, chart, radius, and font tokens remain included because the
current exporter emits them directly and the catalog/runtime tests guard that
behavior.

## Maturity

The Theme Preset contract and newly public preset tokens are post-1.0.0
provisional until a later API-freeze contract promotes them. Current RC.4
implementation covers only the schema axes above; surface style, sidebar
style, chart style, spacing, shadow, contrast, motion, and density remain
deferred and must not be advertised as shipped preset fields.

Font export is intentionally narrow. `--bs-body-font-family` is directly
consumed by Bootstrap. `--moo-heading-font-family` is provisional and must stay
documented with any required font asset loading before a standalone preset can
claim complete heading typography behavior.

## RGB Companion Limitation

The current preset exporter emits `--bs-primary-rgb` for action color because
the schema owns that RGB seed. Base color presets do not emit
`--bs-body-bg-rgb`, `--bs-secondary-bg-rgb`, `--bs-tertiary-bg-rgb`,
`--bs-body-color-rgb`, or `--bs-secondary-color-rgb`; Bootstrap utilities that
rely on those companion variables continue to use the compiled Moo UI defaults.
Promote those companions only after the base color scale stores RGB-compatible
values.

## Chart Defaults

The default chart palette is the neutral Moo chart ramp (`--moo-chart-1`
through `--moo-chart-5`). Earlier runtime fallback behavior used Bootstrap
semantic colors when these variables were absent; RC.4 treats the neutral ramp
as the intended default so Theme Builder exports, catalog preview, and package
CSS agree.

## Catalog Boundary

Catalog settings may use `data-moo-catalog-*` attributes to hold preview state
and suppress transitions while a choice changes. Those attributes are private
to `ui.wpmoo.org`. A standalone export emits only the allow-listed tokens under
`:root`, `[data-bs-theme="light"]`, and `[data-bs-theme="dark"]`; an
owner-scoped preview instead targets only its generated private marker on a
resolved `.moo-ui` owner.
Neither profile emits catalog selectors or an inline style attribute on a host
document element.

`--moo-primary-foreground-dark` is retained for compatibility with hosts that
already distinguish dark-mode action foregrounds. RC.4 action colors are
mode-independent, so it intentionally matches `--moo-primary-foreground`.

## Adapter Guidance

Adapters should store the JSON sidecar fields exactly as documented, normalize
unknown enum values to defaults, and render CSS from the public token allow-list
only. They keep `lang` and a full-document default `dir` on `html`, place a
resolved `.moo-ui[data-bs-theme]` owner at the full-page or embedded-fragment
boundary, and keep triggered overlays in that owner's direct private portal.
Odoo and other hosts should load generated preset CSS after `moo-ui.css` and
must not depend on catalog JavaScript or `data-moo-catalog-*` attributes.

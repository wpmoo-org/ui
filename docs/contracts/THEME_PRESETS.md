# Theme Preset Contract

Moo UI theme presets are additive CSS custom-property overrides loaded after
`moo-ui.css`. They do not require JavaScript at runtime, and exported preset CSS
must never use catalog-only selectors such as `data-moo-catalog-*`.

The JSON sidecar stores the normalized choices that produced the CSS. It is a
portable handoff format for future adapters and tooling, not a runtime
dependency for applying a preset.

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
This normalization lives in `normalizeThemeBuilderState()` in
`site/src/js/catalog/theme-builder-schema.js` and is locked by the focused
normalization and export tests in `tests/test_catalog_js.py`.

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
to `ui.wpmoo.org`; exported presets emit only the tokens above under `:root`,
`[data-bs-theme="light"]`, and `[data-bs-theme="dark"]`.

`--moo-primary-foreground-dark` is retained for compatibility with hosts that
already distinguish dark-mode action foregrounds. RC.4 action colors are
mode-independent, so it intentionally matches `--moo-primary-foreground`.

## Adapter Guidance

Adapters should store the JSON sidecar fields exactly as documented, normalize
unknown enum values to defaults, and render CSS from the public token allow-list
only. Odoo and other hosts should load generated preset CSS after `moo-ui.css`
and should not depend on catalog JavaScript or `data-moo-catalog-*` attributes.

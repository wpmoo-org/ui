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

The catalog uses the external profile. It preloads its versioned `state.js`
URL in the head and invokes that same classic asset as the first child of both
the document owner and keyed Sidebar wrapper. The Jinja `app` macro accepts
`state_src` for this external integration; omitting it retains the canonical
inline profile. Neither invocation uses `async`, `defer`, or `type="module"`.
Visible content is parsed after state restoration; a cold request can still
delay content and show the server background while it loads.

Neither profile mirrors Bootstrap theme state to `html` or `body`. The
bootstrap updates `html[dir]` only for the complete-document owner and uses an
owner `dir` only for embedded subtree overrides. `blocking="render"` is not a
portable replacement: it is a head-only render-blocking mechanism and is not
the owner-local bootstrap contract.

The catalog's persisted Theme Builder state is private site behavior. It
normalizes storage into private `data-moo-catalog-theme-builder-*` attributes
on the owner and applies the generated catalog stylesheet; it is neither a
package export nor a cross-host theme API. Its formatted
unminified `catalog-theme-state.js` asset is generated from the same
configuration as the token stylesheet and preloaded in the head. It reads
`document.currentScript.parentElement`, so its invocation must stay classic
and non-deferred inside the owner, after the public owner bootstrap. Its
configuration and executable code stay outside the HTML document and npm
inventory.

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
  "--moo-primary-active",
  "--moo-primary-foreground",
  "--moo-primary-foreground-dark",
  "--moo-primary-hover",
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
already distinguish dark-mode action foregrounds. Brand action colors set by a
preset (or a host theme) are mode-independent, so it intentionally matches
`--moo-primary-foreground`. Moo's compiled default neutral primary is not a
mode-independent brand color: it inverts in dark mode (the light `#171717`
primary would be about 1.1:1 on the `#0a0a0a` dark surface), so a preset must
not assume the default behaves like a brand color in dark mode.

## Primary Hover and Active

`--moo-primary-hover` and `--moo-primary-active` are optional public tokens for
the fills of `.btn-primary` in its hover and active states. Bootstrap declares
`--bs-btn-hover-bg` on `.btn-primary` itself, so a theme owner cannot set it
from outside; the tokens are the supported override point. Moo does not declare
them on the owner. When absent, the button falls back to
`color-mix(in srgb, var(--moo-primary) 80%, var(--moo-surface))` (72% for
active), derived from `--moo-primary` where the button is used, in light and
dark, so a descendant `--moo-primary` override still re-derives both fills.

Floor rule: a preset that overrides the pair must keep the label
(`--moo-primary-foreground`) at WCAG 2.1 AA 4.5:1 against both fills. A fixed
mix toward the surface lowers contrast on mid-tone brand colors (`#016db7`
with a white label: base 5.42:1, 80% mix 3.76:1, 72% mix 3.23:1), so the
exporter derives the pair as follows. Inputs and outputs are `#rrggbb`; every
sRGB mix rounds each channel to 8 bits; contrast is the WCAG 2.1 relative
luminance ratio; `surface` defaults to `#ffffff`.

1. `hover0` = mix(primary 80%, surface 20%); `active0` = mix(primary 72%,
   surface 28%).
2. `anchor` is `#000000` when the label is lighter than the primary (relative
   luminance), else `#ffffff`.
3. If contrast(`hover0`, label) >= 4.5, `hover` = `hover0`. Otherwise `hover` =
   mix(primary, anchor, t) for the smallest t in 0.08, 0.16, ..., 0.96 that
   reaches 4.5; if no step passes, t = 0.96.
4. If `hover` kept `hover0` and contrast(`active0`, label) >= 4.5, `active` =
   `active0`. Otherwise `active` = mix(primary, anchor, t) for the smallest t
   from t_hover + 0.08 (t_hover is 0 when `hover0` was kept) in 0.08 steps,
   capped at 0.96, that reaches 4.5; if none passes, t = 0.96. When `hover`
   already sits at 0.96, `active` therefore equals `hover`.

When the primary itself cannot reach 4.5:1 against the label, the search can
end at t = 0.96 without reaching the floor; the base color keeps its existing
best-effort selection and the floor is not guaranteed.

Owner reset: every resolved Moo owner (light and dark block) declares both
tokens as `initial`, so a preset set on an outer owner is not inherited by an
independent nested owner with its own primary and label; that owner's button
uses the fallback. A preset that targets the nested owner overrides the reset
at the same selector scope as its `--moo-primary`.

Test vectors (label `#ffffff` unless noted):

| Primary | Label | Hover (ratio) | Active (ratio) |
| --- | --- | --- | --- |
| `#171717` | `#ffffff` | `#454545` (9.59) | `#585858` (7.11) |
| `#016db7` | `#ffffff` | `#0164a8` (6.20) | `#015c9a` (7.00) |
| `#2563eb` | `#ffffff` | `#225bd8` (5.91) | `#1f53c5` (6.77) |
| `#a8d1f0` | `#0a0a0a` | `#b9daf3` (13.56) | `#c0def4` (14.14) |
| `#4a90d9` | `#ffffff` | `#3e79b6` (4.55) | `#386da5` (5.39) |
| `#7aa7d9` | `#ffffff` | `#537294` (5.00) | `#496482` (6.13) |
| `#767676` | `#777777` | `#050505` (4.55) | `#050505` (4.55) |
| `#ffffff` | `#ffffff` | `#ffffff` (1.00) | `#ffffff` (1.00) |

The exporter's link color (`--bs-link-color`, `--bs-link-hover-color`) is
unchanged and does not follow these tokens.

## Adapter Guidance

Adapters should store the JSON sidecar fields exactly as documented, normalize
unknown enum values to defaults, and render CSS from the public token allow-list
only. They keep `lang` and a full-document default `dir` on `html`, place a
resolved `.moo-ui[data-bs-theme]` owner at the full-page or embedded-fragment
boundary, and keep triggered overlays in that owner's direct private portal.
Odoo and other hosts should load generated preset CSS after `moo-ui.css` and
must not depend on catalog JavaScript or `data-moo-catalog-*` attributes.

# Body Typography Token Contract (development candidate)

The nearest resolved `.moo-ui[data-bs-theme]` owner defines Body typography.
Its Body text consumes `--bs-body-font-family`, `--bs-body-font-size`,
`--bs-body-font-weight`, and `--bs-body-line-height`. Descendant `small` and
`.small` consume `--moo-small-font-size`; paragraphs consume
`--moo-paragraph-margin-top` and `--moo-paragraph-margin-bottom`.

Core resets every token on each resolved owner, so an embedded child owner does
not inherit its parent owner's typography. Defaults are 14 px Body, 12 px
Small, weight 400, line height 1.5, 0 px top and 16 px bottom paragraph margin.
Administrators enter whole pixels; adapters emit `rem` values using a 16 px
reference. Line height stays unitless. All token values are validated by the
host adapter; consumers never pass raw CSS or selectors.

This contract is limited to Body typography. Heading level overrides and font
variant delivery are separate work.

Heading weight follows the same owner rule. Each resolved owner resets
`--moo-heading-font-weight` (default 600, Sass `$moo-heading-font-weight`).
Bootstrap's `$headings-font-weight` consumes the token with that default as
fallback, so h1–h6, `.h1`–`.h6`, Display headings, `.card-title`,
`.alert-heading`, `.empty-state-title` and the `page-title` Typography role
follow an owner override, together with the existing
`--moo-heading-font-family`. Explicit utilities such as
`fw-semibold` still win. Font files are delivered by the host, not by Core.

Sass consumers can configure Small through `$moo-small-font-size` and paragraph
top spacing through `$moo-paragraph-margin-top`, both `!default` settings. The
bottom spacing consumes Bootstrap's `$paragraph-margin-bottom`. Default output
is unchanged; runtime owner overrides continue to use the tokens above.

## Website Typography Profile (opt-in)

The compact app profile above is the default. A document that wants marketing
typography sets `data-moo-typography="website"` on its resolved owner, the same
element that carries `data-bs-theme`. Absent the attribute, compiled output for
every default selector is unchanged; the profile adds only rules whose
selectors start at `.moo-ui[data-moo-typography="website"]` (see
`scss/foundations/_typography_website.scss`, imported before the owner scope).

Nested resolved owners inside the attributed owner (for example a dark header
owner) inherit the profile: the owner token rule is also emitted for
`.moo-ui[data-moo-typography="website"] .moo-ui[data-bs-theme]`, whose higher
specificity beats the nested owner's own token reset, and element rules are
written as descendants of the attributed owner. The attribute is therefore set
once, on the document owner. There is no `app` value; remove the attribute to
return to the app profile.

Values (all Sass `!default` knobs in `scss/settings/_palette.scss`):

| Knob | Default |
| --- | --- |
| `$moo-website-font-size` (`--bs-body-font-size`) | `1rem` |
| `$moo-website-line-height` (`--bs-body-line-height`) | `1.6` |
| `$moo-website-small-font-size` (`--moo-small-font-size`) | `0.875rem` |
| `$moo-website-lead-font-size` (`.lead`) | `1.25rem` |
| `$moo-website-heading-line-height` | `1.2` |
| `$moo-website-heading-fluid-sizes` | h1 `2rem`-`3rem`, h2 `1.75rem`-`2.25rem`, h3 `1.375rem`-`1.75rem` |
| `$moo-website-heading-fixed-sizes` | h4 `1.25rem`, h5 `1.125rem`, h6 `1rem` |
| `$moo-website-display-fluid-sizes` | display-1 `2.75rem`-`4.5rem`, 2 `2.5rem`-`4rem`, 3 `2.25rem`-`3.5rem`, 4 `2rem`-`3rem`, 5 `1.75rem`-`2.5rem`, 6 `1.5rem`-`2rem` |

Fluid sizes are `(min max)` pairs in rem; `moo-fluid-size()` emits
`clamp(min, A rem + B vw, max)` so the size equals `min` at a 320 px viewport
and `max` at 1400 px (16 px root): `B = (max - min) / (1400 - 320) * 100` with
min and max in px, and `A = (min - B / 100 * 320) / 16`. Compiled values:

| Size | min / max | clamp |
| --- | --- | --- |
| h1 | 2 / 3rem | `clamp(2rem, 1.7037rem + 1.4815vw, 3rem)` |
| h2 | 1.75 / 2.25rem | `clamp(1.75rem, 1.6019rem + 0.7407vw, 2.25rem)` |
| h3 | 1.375 / 1.75rem | `clamp(1.375rem, 1.2639rem + 0.5556vw, 1.75rem)` |
| display-1 | 2.75 / 4.5rem | `clamp(2.75rem, 2.2315rem + 2.5926vw, 4.5rem)` |
| display-2 | 2.5 / 4rem | `clamp(2.5rem, 2.0556rem + 2.2222vw, 4rem)` |
| display-3 | 2.25 / 3.5rem | `clamp(2.25rem, 1.8796rem + 1.8519vw, 3.5rem)` |
| display-4 | 2 / 3rem | `clamp(2rem, 1.7037rem + 1.4815vw, 3rem)` |
| display-5 | 1.75 / 2.5rem | `clamp(1.75rem, 1.5278rem + 1.1111vw, 2.5rem)` |
| display-6 | 1.5 / 2rem | `clamp(1.5rem, 1.3519rem + 0.7407vw, 2rem)` |

Zoom (WCAG 1.4.4): every fluid size keeps `max <= 2.5 x min`, which guarantees
a 200% enlargement with a `rem + vw` clamp. Text-only resize scales the rem
parts of the clamp (and the rem min and max); the vw part follows the viewport,
so browser zoom, which shrinks the CSS viewport, enlarges text as well. A test
asserts the rule for every fluid entry.

Headings (`h1`-`h6`, `.h1`-`.h6`, `.display-*`) use `text-wrap: balance`;
paragraphs use `text-wrap: pretty` (ignored where unsupported). Element rules
use `:where()` on the owner, so component-owned sizes such as card titles keep
winning ties.

German hyphenation: `p, li, dd, blockquote, figcaption` matching `:lang(de)`
(which includes `de-AT`, `de-CH`) get `hyphens: auto` and
`overflow-wrap: break-word`. The language comes from `html` or any ancestor
`lang`. Both properties inherit, so a following profile rule resets
`hyphens: manual` and `overflow-wrap: normal` on any `[lang]` descendant of such
an element that is not German (an English span or a nested English blockquote);
text elements that merely inherit German stay hyphenated.

Readable measure: the `.text-measure` utility (`max-inline-size`, Sass knob
`$moo-text-measure`, default `68ch`) works in either profile and is documented
on the Text Measure utility page. The profile does not cap every paragraph,
because cards, columns, tables and full-width sections already own their width
and a global cap would fight them; authors apply the utility to running text.

Catalog: the Typography page has a "Website profile" example
(`/components/typography/#website-profile`); the utility page is
`/utils/text-measure/`.

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

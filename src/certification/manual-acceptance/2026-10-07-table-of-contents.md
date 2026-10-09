# Table of Contents preview acceptance

Date: 2026-10-07
Status: Accepted appearance, source-mode independent HTML preview.

The maintainer accepted the revised result with “Tmm çok güzel” after reviewing
`http://127.0.0.1:4331/conformance/table-of-contents/light-ltr.html#languages`.
The acceptance covers the shared Core TOC preview: compact full-width panel,
header/bar remaining above scrolling content, active-section status, a wide
aside list and ordinary supporting content following the article on narrow
screens. It is not a package release or adapter certification.

## Source and runtime

- Canonical Core checkout, existing `dev`, baseline `772b045229413e1363061f10c2cd71541d92aa8a` plus the TOC source changes.
- Plain host: `conformance/table-of-contents/index.html.jinja`, using public
  Button, Dropdown Menu, Navigation and App composition; no component CSS.
- Bootstrap 5.3.3; explicit source ESM initialization.
- Browser inspection covered light/LTR and dark/RTL, native selection, long
  labels, stationary header/bar and supporting content after the article.
- Requested 390/1440px browser overrides corresponded to approximately
  354/1309 CSS pixels at the current browser zoom, below/above `xl`.
- No warning/error console entries were observed in the inspected tabs.
- The unpublished hooks were then aligned with Core's component-owned
  convention (`data-toc*`); the accepted presentation and behavior are unchanged.

## Preserved images

The original PNG bytes are retained with hashes in
[`evidence/manifest.json`](../../../conformance/table-of-contents/evidence/manifest.json).

- [Mobile light/LTR open panel](../../../conformance/table-of-contents/evidence/mobile-light-ltr-open.png)
- [Mobile dark/RTL open panel](../../../conformance/table-of-contents/evidence/mobile-dark-rtl-open.png)
- [Mobile dark/RTL supporting aside](../../../conformance/table-of-contents/evidence/mobile-dark-rtl-aside-after.png)
- [Wide light/LTR list](../../../conformance/table-of-contents/evidence/desktop-light-ltr.png)
- [Wide dark/RTL list](../../../conformance/table-of-contents/evidence/desktop-dark-rtl.png)

## Positive regression contracts

After human acceptance, the focused browser class gained observable checks for
equal panel/bar width and fixed header position, ordinary aside after article,
and a single visible presentation across the `xl` breakpoint. These protect
the accepted geometry rather than incidental class spelling or screenshot
pixels. The rendering and browser classes pass all 20 tests in the existing
project environment.

Real-device testing, a complete accessibility audit, the supported browser/
Bootstrap matrix and immutable package/adapter intake are separate evidence.
Historical stable freezes and previous acceptance records remain unchanged.

## Subsequent requested list outline

The maintainer later approved an exact three-rule Core CSS exception for a
neutral inline-start rail below the label and a primary-token active segment.
The renderer adds only native `p-0` to align the rail in RTL. Locally verified
candidate identities and Astro adapter intake are recorded in the private host
workspace, outside this Core acceptance record.
The new browser geometry contract protects that explicit direction across
both themes and directions, including primary customization during scrolling.
It does not regenerate the historical image manifest or stable certification.


## Accepted outline and sliding-marker follow-up

The maintainer accepted the refined title/rail/text-height outline and sliding
primary marker on 2026-10-07. One Core pseudo-element moves through Bootstrap's
200-ms transition; reduced motion disables animation. The optional tracker
restores authored marker state on disposal. Native fragment behavior is retained.
Internal sources now use `toc.html.jinja` and `_toc.scss`; public names do not
change. Thirty-one focused rendering/browser/Navigation/package methods pass,
including intermediate motion positions, reduced motion, wrapped labels,
LTR/RTL primary customization, responsive remeasurement and disposal restoration.
The final private Core revision7 and Astro revision14 identities, user approval
and gap-5 aside evidence are recorded separately in the host workspace.
Historical stable certifications and their image manifest retain their original
identity.


The Moo UI catalog also consumes the same public macro and lazy tracker for
ordinary docs, component examples and utility examples. Catalog-specific TOC
colors, typography, rail and spacing CSS are removed; sticky column layout and
existing host scroll/hash/history handling remain. Nine focused catalog methods
pass, including native document/component tracking, initial hash alignment and
minimum touch targets. The native 4173 preview confirms the shared 200-ms marker
and zero list gap, with no warning/error logs. Its observed image is retained in
the host workspace; no stable certification manifest was regenerated.

## Accepted gallery recognition artwork

On 2026-10-09 the maintainer approved the original monochrome, hand-drawn TOC
illustration on light and dark surfaces. The transparent 1536 x 1024 source
is retained in the private host workspace. The public catalog uses the
[optimized WebP](../../../site/static/images/components/table-of-contents.webp),
converted through the existing preview pipeline with its alpha preserved.
Its SHA-256 is `85584ec2c7178e639e081fd36f4e74ee34e11a092a9c8ecc83a675b0cc9ba3b4`.
The existing ready-component preview gate passes with this asset; no placeholder
exception or stable certification update is introduced.

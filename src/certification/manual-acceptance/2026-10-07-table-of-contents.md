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

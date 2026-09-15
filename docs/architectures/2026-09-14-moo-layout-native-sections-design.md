# Moo UI Layout Native Sections

## Context

The catalog already has a single public `/layout/` document and a shared
component-example pattern. The next iteration should make Layout discoverable
as its own sidebar section without creating a second Bootstrap documentation
site. Moo UI owns the application and page contracts; Bootstrap remains the
native layout vocabulary used by catalog examples.

This work is intentionally additive to the current layout guide and does not
restore the removed `/layouts/...` public pages or redirects.

## Goals

- Place a `Layout` sidebar group immediately after `Catalog` and before
  `Resources`.
- Keep one canonical public Layout page at `/layout/`.
- Give the page a stable, scrollable TOC with `App`, `Page`, and the eight
  Bootstrap-native layout topics: `Breakpoints`, `Containers`, `Grid`,
  `Columns`, `Gutters`, `Utilities`, `Z-index`, and `CSS Grid`.
- Explain native topics only through Moo UI usage contracts and one practical
  example per topic; link to Bootstrap for exhaustive API/reference material.
- Render every example with the existing component-document pattern: live
  preview followed by an expandable, copyable HTML source block.
- Keep Catalog examples authored with real Bootstrap layout classes so users
  can transfer the markup directly to a Bootstrap-native host.

## Navigation and page model

The sidebar groups will be ordered as:

1. Getting Started
2. Catalog
3. Layout
4. Resources

The Layout group contains one `Layout` link to `/layout/`. Its subsections are
anchors on that page rather than additional routes. The page header and local
TOC remain the source of deep links, while section-page pagination continues
to treat Layout as one canonical document.

## Content contract

The page keeps a short Moo-specific introduction, then the following sections:

### App

Document the application-shell contract: direct App/Page composition, optional
Sidebar ownership, viewport versus contained shell mode, scroll ownership,
responsive collapse, and the existing Moo layout macro boundaries. Include a
minimal rendered shell example and its markup where it clarifies the contract.

### Page

Document semantic `header`, `main`, and optional `footer` regions, the shared
Bootstrap content rail, width choices, and how a Page participates in the App
shell. Include a rendered page-surface example and markup.

### Bootstrap-native integration sections

Each section contains only:

1. a concise statement of the Moo UI decision or usage contract;
2. one live example using native Bootstrap classes;
3. the exact example markup below the preview; and
4. a link to the corresponding official Bootstrap page for complete details.

The examples are intentionally representative rather than exhaustive:

- Breakpoints: a compact Moo responsive matrix and a visible breakpoint-driven
  change.
- Containers: fixed, responsive, and fluid rails with a small width comparison.
- Grid: the canonical `container` → `row` → `col` composition and a responsive
  variant.
- Columns: explicit spans, auto-width columns, and a mixed row.
- Gutters: horizontal, vertical, and all-axis gutter utilities.
- Utilities: a practical responsive spacing/display/flex composition.
- Z-index: a small layered surface showing the intended stacking relationship.
- CSS Grid: a native CSS-grid example using Bootstrap’s documented grid
  utilities.

No Bootstrap prose, exhaustive API tables, or copied documentation sections
are introduced. Tables appear only when they explain a Moo-specific contract
or make the example observable.

## Implementation boundaries

Expected site changes are limited to the existing Layout page, catalog
sidebar/navigation data, and focused documentation tests. The implementation
should reuse `render_example` (or a narrowly scoped companion macro only if
needed) so preview/source behavior, copy affordances, highlighting, and
accessibility stay consistent with component pages. No Core runtime layout
template, package entrypoint, or public compatibility route changes are part
of this design.

Catalog example templates remain the native markup source. Layout prose may
reference those examples, but it must not introduce Moo-only aliases that
hide or replace Bootstrap classes.

## Accessibility and responsive behavior

Every section gets a unique heading ID and appears in the local TOC. Preview
surfaces must remain readable at desktop and mobile widths, code blocks keep
keyboard focus and copy/status announcements, and no example may rely on
color alone to communicate a layout change. Sidebar active state must identify
the Layout page while the user scrolls its sections.

## Verification

Focused verification will cover:

- sidebar group order and the single canonical `/layout/` link;
- all required section IDs and TOC labels;
- one preview/source pair and required native classes per topic;
- generated metadata, sitemap, and command-palette inclusion for `/layout/`;
- absence of `/layouts/` compatibility output and redirects;
- desktop/mobile browser rendering without horizontal overflow;
- unchanged Core `src/layouts/app.html.jinja` and `src/layouts/page.html.jinja`.

The existing path-driven quick test tier remains the default check; broader
tiers are not required for this site-only documentation change.

## Non-goals

- Reproducing the Bootstrap Layout documentation locally.
- Adding separate `/layout/<topic>/` public routes.
- Restoring or redirecting legacy `/layouts/...` routes without a new explicit
  approval.
- Changing the Core layout runtime or its public package contract.

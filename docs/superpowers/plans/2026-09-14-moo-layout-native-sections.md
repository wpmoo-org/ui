# Moo UI Layout Native Sections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the single canonical `/layout/` document with Moo-specific App/Page guidance and one Bootstrap-native preview/source example for every layout topic, while placing Layout after Catalog in the sidebar.

**Architecture:** Keep `/layout/` as the only public Layout route. Move its link into a dedicated sidebar group after Catalog, then add stable anchor sections to the existing Jinja page. Reuse the component-document `render_example` macro so each section has one rendered preview and one expandable, copyable source block; no Core runtime API or legacy route is added.

**Tech Stack:** Python/Jinja site builder, Bootstrap 5.3 layout/utility classes, existing Moo catalog Sass/ESM, Python `unittest`, Playwright browser harness, and generated `site-dist` verification output. Release baselines are owned by the parent layout plan's Task 8.

**Spec:** `docs/superpowers/specs/2026-09-14-moo-layout-native-sections-design.md`

## Global Constraints

- Keep one canonical public Layout page at `/layout/`.
- Explain native topics only through Moo UI usage contracts and one practical example per topic; link to Bootstrap for exhaustive API/reference material.
- Render every example with the existing component-document pattern: live preview followed by an expandable, copyable HTML source block.
- Keep Catalog examples authored with real Bootstrap layout classes so users can transfer the markup directly to a Bootstrap-native host.
- Do not reproduce the Bootstrap Layout documentation locally.
- Do not add separate `/layout/<topic>/` public routes.
- Do not restore or redirect legacy `/layouts/...` routes without a new explicit approval.
- The native-section work in this plan does not change
  `src/layouts/app.html.jinja`, package entrypoints, or public runtime
  contracts. A separate completed-lane review fix may remove the undocumented
  `page(main_class)` parameter; do not duplicate that change in these native
  section tasks.
- Do not add Tabler references or aliases that hide Bootstrap classes.
- Use `apply_patch`, run focused tests after each logical change, and stage only task files around pre-existing worktree edits.

## File Map

- Modify `site/src/shell/sidebar.html.jinja`: move Layout out of Getting Started and add a dedicated group after Catalog.
- Modify `site/src/pages/layout.html.jinja`: retain App/Page guidance and add the eight native integration sections.
- Modify `tests/test_catalog.py`: lock sidebar ordering, the single Layout link, and the Catalog native-class boundary.
- Modify `tests/test_layouts.py`: lock all Layout anchors, previews, source panels, and single-page routing.
- Modify `tests/test_catalog_browser.py` or `tests/test_layouts_browser.py`: verify responsive public-page behavior.
- Do not update `tests/fixtures/boundary-baseline.json` in this child plan; review generated site-only changes and defer baseline/hash refresh to the parent layout plan's Task 8.
- Do not modify `site/src/registry/sections.json` or `site/src/shell/navbar.html.jinja` unless a focused test proves it is required; the canonical section and navbar metadata already exist.

---

### Task 1: Establish failing Layout and sidebar contracts

**Files:**
- Modify: `tests/test_catalog.py` near `CatalogContractTests.test_sidebar_navigation_groups_examples_with_catalog_before_components`
- Modify: `tests/test_layouts.py` near `LayoutCatalogTests.test_layout_guide_is_canonical_without_legacy_routes`

**Interfaces:**
- Consumes: generated `site-dist/index.html` and `site-dist/layout/index.html` from `CatalogTestCase.run_build()`.
- Produces: deterministic contracts for group order, route count, ten section IDs, ten preview/source IDs, and native class markers.

- [ ] **Step 1: Replace the old sidebar expectation with the new group-order assertion.**

Use this exact slice logic in the existing test:

```python
catalog_start = sidebar.index(">Catalog<")
layout_start = sidebar.index(">Layout<")
resources_start = sidebar.index(">Resources<")
getting_started = sidebar[:catalog_start]
catalog_group = sidebar[catalog_start:layout_start]
layout_group = sidebar[layout_start:resources_start]

self.assertLess(catalog_start, layout_start)
self.assertLess(layout_start, resources_start)
self.assertNotIn('href="layout/"', getting_started)
self.assertIn('href="layout/"', layout_group)
self.assertEqual(layout_group.count('href="layout/"'), 1)
self.assertNotIn('href="layouts/"', sidebar)
self.assertLess(catalog_group.index('href="examples/"'), catalog_group.index('data-bs-target="#shell-components-menu"'))
```

- [ ] **Step 2: Add the Layout guide contract test before changing the template.**

Add these constants and assertions to `LayoutCatalogTests`:

```python
LAYOUT_GUIDE_SECTIONS = (
    ("app", "App", "layout-app-example"),
    ("page", "Page", "layout-page-example"),
    ("breakpoints", "Breakpoints", "layout-breakpoints-example"),
    ("containers", "Containers", "layout-containers-example"),
    ("grid", "Grid", "layout-grid-example"),
    ("columns", "Columns", "layout-columns-example"),
    ("gutters", "Gutters", "layout-gutters-example"),
    ("utilities", "Utilities", "layout-utilities-example"),
    ("z-index", "Z-index", "layout-z-index-example"),
    ("css-grid", "CSS Grid", "layout-css-grid-example"),
)

def test_layout_guide_has_one_native_example_and_source_per_section(self) -> None:
    result = self.run_build()
    self.assertEqual(result.returncode, 0, result.stderr)
    page = self.read_output("layout/index.html")
    self.assertIn('class="moo-doc-layout"', page)
    self.assertIn('aria-label="On this page"', page)
    for slug, label, example_id in LAYOUT_GUIDE_SECTIONS:
        with self.subTest(slug=slug):
            self.assertIn(f'href="#{slug}"', page)
            self.assertIn(f'id="{slug}"', page)
            self.assertIn(f'>{label}</a>', page)
            self.assertEqual(page.count(f'data-example="{example_id}"'), 1)
            self.assertIn(f'id="{example_id}-code"', page)
    for native_class in (
        "container", "container-fluid", "row", "col", "gx-4", "gy-3",
        "d-flex", "z-1", "z-3", "grid", "g-col-6",
    ):
        self.assertIn(native_class, page)
    self.assertNotIn("Bootstrap comes with", page)
    self.assertNotIn('href="/layout/breakpoints/"', page)
    self.assertNotIn('href="layout/breakpoints/"', page)
```

- [ ] **Step 3: Run only these tests and confirm intentional failures.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 -m unittest \
  tests.test_catalog.CatalogContractTests.test_sidebar_navigation_groups_examples_with_catalog_before_components \
  tests.test_layouts.LayoutCatalogTests.test_layout_guide_has_one_native_example_and_source_per_section \
  -v
```

Expected: the sidebar test sees Layout in Getting Started and the guide test
sees missing native sections. Do not edit production templates until both
failures are observed.

- [ ] **Step 4: Commit only the red tests.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
git add tests/test_catalog.py tests/test_layouts.py
git commit -m "test: define Moo layout native section contracts"
```

### Task 2: Move Layout into its dedicated sidebar group

**Files:**
- Modify: `site/src/shell/sidebar.html.jinja`
- Test: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `layout_page`, the existing Catalog entries, and sidebar macros.
- Produces: `Getting Started → Catalog → Layout → Resources`, with exactly one active-aware `/layout/` link in the Layout group.

- [ ] **Step 1: Add the Layout group data and remove its Getting Started entry.**

Insert this before `nav_groups`:

```jinja
{% set layout_items = [{
  "kind": "link",
  "label": layout_page.label,
  "href": layout_page.href,
  "icon": layout_page.icon,
  "active": current_section == "sections" and current_slug == layout_page.slug
}] %}
```

Delete the Layout object from the Getting Started `entries` list and insert:

```jinja
{"label": "Layout", "entries": layout_items},
```

immediately after the Catalog group and before Resources. Keep all Catalog
entry order, component submenu IDs, and active-state expressions unchanged.

- [ ] **Step 2: Run the sidebar and pagination contracts.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 -m unittest \
  tests.test_catalog.CatalogContractTests.test_sidebar_navigation_groups_examples_with_catalog_before_components \
  tests.test_catalog.CatalogContractTests.test_section_pages_render_page_actions_and_pagination \
  -v
```

Expected: PASS; Installation still links to Layout, Layout still links to
Examples, and no legacy path is emitted.

- [ ] **Step 3: Commit the sidebar change selectively.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
git add site/src/shell/sidebar.html.jinja tests/test_catalog.py
git commit -m "docs: place Layout after Catalog in sidebar"
```

### Task 3: Expand the single Layout page with Moo-specific native examples

**Files:**
- Modify: `site/src/pages/layout.html.jinja`
- Test: `tests/test_layouts.py`

**Interfaces:**
- Consumes: `render_example`, `render_doc_toc`, page header, and pagination macros.
- Produces: stable IDs `app`, `page`, `breakpoints`, `containers`, `grid`, `columns`, `gutters`, `utilities`, `z-index`, and `css-grid`; each has one `data-example="layout-<slug>-example"` and one `<slug>-example-code` source panel.

- [ ] **Step 1: Import `render_example` and add App/Page structure previews.**

Add this import beside the existing Layout page imports:

```jinja
{% from "includes/example.html.jinja" import render_example %}
```

Keep the current App/Page explanatory subsections and add one static semantic
preview to each (do not nest the `app` macro inside the Catalog shell):

```jinja
{% set app_example %}
<div class="border rounded overflow-hidden">
  <div class="d-flex flex-column flex-md-row">
    <aside class="border-bottom border-md-end p-3 flex-shrink-0" aria-label="Example navigation"><strong class="small">Sidebar</strong><div class="small text-body-secondary mt-2">Owns route navigation</div></aside>
    <main class="flex-grow-1 p-3"><strong class="small">Page</strong><div class="small text-body-secondary mt-2">Owns the current screen</div></main>
  </div>
</div>
{% endset %}
{{ render_example("layout-app-example", "App topology", "Keep Sidebar and Page as direct App siblings when the route owns navigation.", app_example) }}

{% set page_example %}
<div class="border rounded overflow-hidden">
  <header class="border-bottom p-3">Page header</header>
  <main class="p-3"><div class="container-xl px-0">Page content rail</div></main>
  <footer class="border-top p-3">Optional page footer</footer>
</div>
{% endset %}
{{ render_example("layout-page-example", "Page regions", "Semantic regions stay full width while content aligns to one native container rail.", page_example) }}
```

- [ ] **Step 2: Add the eight native sections in the specified order.**

For each section, create a `<section class="mt-5" aria-labelledby="<slug>">`,
render `typography("<label>", variant="section-title", id="<slug>")`, write
one Moo-specific paragraph, call `render_example` once, and add the official
Bootstrap link. Use these exact preview bodies and identifiers:

```jinja
{% set breakpoints_example %}<div class="table-responsive"><table class="table table-sm align-middle mb-0"><thead><tr><th scope="col">Moo tier</th><th scope="col">Native infix</th><th scope="col">Live rule</th></tr></thead><tbody><tr><th scope="row">Base</th><td>none</td><td><span class="d-inline d-sm-none">visible below sm</span><span class="d-none d-sm-inline">hidden from sm</span></td></tr><tr><th scope="row">Medium</th><td>md</td><td><span class="d-inline d-md-none">visible below md</span><span class="d-none d-md-inline">visible from md</span></td></tr></tbody></table></div>{% endset %}
{{ render_example("layout-breakpoints-example", "Responsive tiers", "Choose mobile-first Bootstrap infixes for Moo responsive changes.", breakpoints_example) }}

{% set containers_example %}<div class="vstack gap-3"><div class="container border rounded p-3">.container — responsive max-width</div><div class="container-md border rounded p-3">.container-md — full width until md</div><div class="container-fluid border rounded p-3">.container-fluid — full width</div></div>{% endset %}
{{ render_example("layout-containers-example", "Native rails", "Use the Bootstrap container that matches the Page width contract.", containers_example) }}

{% set grid_example %}<div class="container text-center"><div class="row g-3"><div class="col"><div class="border rounded p-3">Column</div></div><div class="col"><div class="border rounded p-3">Column</div></div><div class="col"><div class="border rounded p-3">Column</div></div></div><div class="row g-3 mt-1"><div class="col-12 col-md-8"><div class="border rounded p-3">8 columns from md</div></div><div class="col-12 col-md-4"><div class="border rounded p-3">4 columns from md</div></div></div></div>{% endset %}
{{ render_example("layout-grid-example", "Container, row, and columns", "Compose page content with Bootstrap's native grid primitives.", grid_example) }}

{% set columns_example %}<div class="container text-center"><div class="row g-2 align-items-center"><div class="col-12 col-md-3"><div class="border rounded p-3">col-md-3</div></div><div class="col"><div class="border rounded p-3">col</div></div><div class="col-auto"><div class="border rounded p-3">auto</div></div></div></div>{% endset %}
{{ render_example("layout-columns-example", "Column sizing", "Use explicit spans, flexible columns, and auto-width actions in one native row.", columns_example) }}

{% set gutters_example %}<div class="container overflow-hidden"><div class="row gx-4 gy-3"><div class="col-6"><div class="border rounded p-3">gx-4 / gy-3</div></div><div class="col-6"><div class="border rounded p-3">gx-4 / gy-3</div></div><div class="col-6"><div class="border rounded p-3">gx-4 / gy-3</div></div><div class="col-6"><div class="border rounded p-3">gx-4 / gy-3</div></div></div></div>{% endset %}
{{ render_example("layout-gutters-example", "Gutter rhythm", "Keep horizontal and vertical spacing on the native row.", gutters_example) }}

{% set utilities_example %}<div class="d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-3 p-3 border rounded"><div><strong>Responsive utility composition</strong><div class="text-body-secondary small">Stacks on mobile and aligns inline from md.</div></div><div class="d-flex gap-2"><button class="btn btn-primary btn-sm" type="button">Primary</button><button class="btn btn-outline-secondary btn-sm" type="button">Secondary</button></div></div>{% endset %}
{{ render_example("layout-utilities-example", "Utility composition", "Prefer Bootstrap display, flex, spacing, and sizing utilities for local adjustments.", utilities_example) }}

{% set z_index_example %}<div class="position-relative p-5 border rounded"><div class="position-absolute top-0 start-0 p-3 bg-secondary-subtle border rounded z-1">Base surface</div><div class="position-absolute top-50 start-50 translate-middle p-3 bg-primary text-white border rounded z-3">Raised surface</div></div>{% endset %}
{{ render_example("layout-z-index-example", "Layered surfaces", "Use native z-index utilities only for a documented stacking relationship.", z_index_example) }}

{% set css_grid_example %}<div class="grid gap-3"><div class="g-col-6 border rounded p-3">g-col-6</div><div class="g-col-6 border rounded p-3">g-col-6</div><div class="g-col-6 g-col-md-4 border rounded p-3">g-col-6 g-col-md-4</div><div class="g-col-6 g-col-md-8 border rounded p-3">g-col-6 g-col-md-8</div></div>{% endset %}
{{ render_example("layout-css-grid-example", "CSS Grid utilities", "Use Bootstrap's CSS Grid utility layer when explicit placement is clearer than flex rows.", css_grid_example) }}
```

Use official links ending in `/layout/breakpoints/`, `/layout/containers/`,
`/layout/grid/`, `/layout/columns/`, `/layout/gutters/`, `/layout/utilities/`,
`/layout/z-index/`, and `/layout/css-grid/`; set `target="_blank"` and
`rel="noopener noreferrer"`. Do not copy Bootstrap’s prose or exhaustive
tables.

- [ ] **Step 3: Extend the TOC while retaining App/Page detail links.**

Pass this exact ordered list to `render_doc_toc`:

```jinja
{{ render_doc_toc([
  {"id": "layout", "label": "Layout"},
  {"id": "app", "label": "Application shell"},
  {"id": "app-topology", "label": "App topology"},
  {"id": "page", "label": "Page surface"},
  {"id": "page-regions", "label": "Page regions"},
  {"id": "widths", "label": "Width choices"},
  {"id": "shell-mode", "label": "Shell mode"},
  {"id": "breakpoints", "label": "Breakpoints"},
  {"id": "containers", "label": "Containers"},
  {"id": "grid", "label": "Grid"},
  {"id": "columns", "label": "Columns"},
  {"id": "gutters", "label": "Gutters"},
  {"id": "utilities", "label": "Utilities"},
  {"id": "z-index", "label": "Z-index"},
  {"id": "css-grid", "label": "CSS Grid"}
]) }}
```

- [ ] **Step 4: Run the Layout contracts and commit the page.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 -m unittest \
  tests.test_layouts.LayoutCatalogTests \
  tests.test_catalog.CatalogContractTests.test_section_pages_render_page_actions_and_pagination \
  -v
git add site/src/pages/layout.html.jinja tests/test_layouts.py
git commit -m "docs: add Moo-native layout guide examples"
```

Expected: all Layout guide tests pass and the Core macro tests remain green.

### Task 4: Lock the Catalog Bootstrap-native example boundary

**Files:**
- Modify: `tests/test_catalog.py`
- Read-only inputs: `site/src/pages/examples/index.html.jinja`, `site/src/pages/examples/auth/sign-in.html.jinja`, `site/src/pages/examples/settings/profile.html.jinja`

**Interfaces:**
- Consumes: generated Examples HTML and existing example templates.
- Produces: regression coverage that Catalog examples keep real Bootstrap layout classes without banning component-specific visual classes.

- [ ] **Step 1: Add the boundary test without refactoring Catalog examples.**

```python
def test_catalog_examples_keep_bootstrap_native_layout_classes(self) -> None:
    result = self.run_build()
    self.assertEqual(result.returncode, 0, result.stderr)
    examples_index = self.read_output("examples/index.html")
    sign_in = self.read_output("examples/auth/sign-in.html")
    profile = self.read_output("examples/settings/profile.html")
    self.assertIn('class="d-grid gap-4"', examples_index)
    self.assertIn('class="d-flex align-items-center justify-content-between"', sign_in)
    self.assertIn('class="d-grid gap-4"', sign_in)
    self.assertIn('class="d-grid gap-4"', profile)
    self.assertNotIn("bootstrap-grid", examples_index)
    self.assertNotIn("moo-grid", examples_index)
```

- [ ] **Step 2: Run and commit the boundary test.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 -m unittest \
  tests.test_catalog.CatalogContractTests.test_catalog_examples_keep_bootstrap_native_layout_classes \
  -v
git add tests/test_catalog.py
git commit -m "test: preserve Bootstrap-native Catalog examples"
```

Expected: PASS with no changes to the example page markup.

### Task 5: Verify public rendering without owning release baselines

**Files:**
- Modify: `tests/test_catalog_browser.py` or `tests/test_layouts_browser.py`
- Read-only: generated `site-dist/` output and the parent-plan baseline status

**Interfaces:**
- Consumes: `serve_repository`, `new_case_context`, `prepare_page`, generated `/site-dist/layout/`, and Tasks 1–4 contracts.
- Produces: desktop/mobile evidence for the sidebar, TOC, ten examples, source panels, clean responses, and no horizontal overflow.

- [ ] **Step 1: Add a public Layout browser test before running it.**

Use the existing browser setup and assert the same ten example IDs at 1280×900
and 390×844:

```python
for viewport in ((1280, 900), (390, 844)):
    context = new_case_context(self.browser, CERTIFICATION_CASES[0])
    page = context.new_page()
    evidence = BrowserEvidence(page)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    try:
        response = page.goto(f"{self.base_url}/site-dist/layout/", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertTrue(response.ok)
        prepare_page(page, CERTIFICATION_CASES[0])
        expect(page.get_by_role("heading", name="Layout", level=1)).to_be_visible()
        self.assertLessEqual(
            page.evaluate("document.documentElement.scrollWidth"),
            page.evaluate("document.documentElement.clientWidth"),
        )
        for example_id in (
            "layout-app-example", "layout-page-example", "layout-breakpoints-example",
            "layout-containers-example", "layout-grid-example", "layout-columns-example",
            "layout-gutters-example", "layout-utilities-example", "layout-z-index-example",
            "layout-css-grid-example",
        ):
            example = page.locator(f'[data-example="{example_id}"]')
            expect(example).to_have_count(1)
            expect(example.locator(".moo-example__preview")).to_be_visible()
            expect(example.locator(".moo-example__source")).to_have_count(1)
        evidence.assert_clean()
    finally:
        context.close()
```

- [ ] **Step 2: Run the browser test at both viewports.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 -m unittest \
  tests.test_catalog_browser.CatalogBrowserTests.test_layout_guide_native_sections_render_at_desktop_and_mobile \
  -v
```

Expected: PASS with no failed responses, console errors, or horizontal scroll.
If a table clips, add only `table-responsive`, existing scroll-fade, or a
native responsive utility to that example.

- [ ] **Step 3: Build and assert the public path boundary.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 build.py --core
.venv/bin/python3 build.py --site
git diff --check
test -f site-dist/layout/index.html
test ! -e site-dist/layout/breakpoints/index.html
test ! -e site-dist/layout/grid/index.html
test ! -e site-dist/layout/containers/index.html
test ! -e site-dist/layouts/index.html
test ! -e site-dist/layouts/app/index.html
test ! -e site-dist/layouts/page/index.html
```

- [ ] **Step 4: Review generated output without writing a baseline.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
git diff -- site-dist tests/fixtures/boundary-baseline.json
```

Accept only intentional site HTML/asset changes. Do not run
`scripts/record-boundary-baseline.py --write` and do not modify any baseline or
hash file here; the parent layout plan's Task 8 owns that release decision.

- [ ] **Step 5: Commit browser coverage only.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
git add tests/test_catalog_browser.py
git commit -m "test: verify responsive Moo layout guide"
```

### Task 6: Run completed-lane checks and defer release gates

**Files:**
- Read-only review: all files changed by Tasks 1–5 plus `src/layouts/app.html.jinja` and `src/layouts/page.html.jinja`

- [ ] **Step 1: Run completed-lane checks without the release tier.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
.venv/bin/python3 -m unittest \
  tests.test_catalog tests.test_layouts tests.test_layouts_browser -v
```

Expected: the completed Layout/catalog contracts pass. The parent layout
plan's Task 8 remains the owner of `run-test-tier.py`,
`tests.test_core_docs_boundary`, dependency/release gates, and boundary hashes;
do not invoke the quick/release tier here while those baselines are deferred.

- [ ] **Step 2: Verify immutable runtime and legacy boundaries.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
git diff --name-only -- src/layouts/app.html.jinja src/layouts/page.html.jinja
git diff --name-only -- site/src/pages/layouts site/public/_redirects
rg -n "Tabler|bootstrap-grid|moo-grid" site/src/pages/layout.html.jinja site/src/shell/sidebar.html.jinja site/src/pages/examples || true
```

Expected: no runtime/legacy paths and no forbidden reference; `/layout/` is the
only public Layout document and `/layouts/` remains a 404 in the dev handler.
These checks do not refresh a release baseline.

- [ ] **Step 3: Review status and diff before any optional review tool.**

```bash
cd /Users/cng/wpmoo/workspace/projects/ui/html
git status --short
git diff --stat
git diff --check
```

Confirm the parent `.agent/memory/episodic/AGENT_LEARNINGS.jsonl`, parent
submodule pointer, and unrelated user changes are untouched. Run CodeRabbit only
if the user explicitly authorizes it and authentication is available.

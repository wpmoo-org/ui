# Package Surface Decisions

This file records package-surface decisions that are intentionally broader
than one component page.

## 1.4.2 Compatible Fixes

Field Description and Field Error consume the existing owner-resolved
`--moo-small-font-size` token, matching Typography Small's default0.75rem and
runtime customization in full and scoped stylesheets. Feedback colours, zero
top margin, Field spacing, native validation, markup and ARIA associations
remain unchanged. There is no new token, component prop, dependency, export,
ESM behavior or adapter-specific override. This compatible visual correction
is a patch to1.4.1, not a new public component or API release.

New catalog CodePen exports deliberately follow npm's stable `@latest` tag for
Moo CSS and Moo ESM, including inline DataTable/Chart demo imports. The shared
demo loader already derives its Moo runtime version from the linked stylesheet;
that preserves explicitly pinned saved Pens while new exports follow `latest`.
This is a catalog delivery policy, not a package export/lifecycle change or
permission to float installation docs, adapter locks or production dependencies.
Updates take effect on reload subject to CDN caching; independent tag requests
are not an atomic asset snapshot during publication. Stored markup and inline
demo logic do not update automatically. Pin both CSS and explicit module imports
when an immutable reproduction is needed. Existing saved versioned URLs are not
retroactively rewritten, and Bootstrap's existing compatibility policy is unchanged.
The live tag can advance across major versions; it is not a compatibility pin.

The accepted appearance is protected by the Field parity browser contract in
16 stylesheet/theme/direction/viewport profiles, with a visible error linked
to its invalid control and both feedback roles following owner customization.
Certification stays in preview. Release-specific validation is still required;
merging the version bump to main starts the existing automatic release chain.

## 1.4.1 Compatible Fixes

Field applies its existing medium label weight to nested composite-control
labels without changing label association or spacing defaults. Enabled form
prompts use the existing secondary-text token instead of the disabled tone.
Native Select callers explicitly annotate prompt options with
`data-placeholder="true"`; ordinary empty/zero values, disabled options and
multiple/listbox modes keep their native meaning. Native `:checked` owns colour
updates, including direct value assignment and form reset; no Select runtime is
added. Date Picker exposes `data-datepicker-empty="true|false"` on its existing
visible label and synchronizes it through its existing controller lifecycle.
A valid start date makes a partial range selected, not empty. Prompt and selected
date text use normal Input weight; interactive/invalid/disabled Button colours
retain ownership.

These opt-in annotations correct empty-selection presentation without replacing
existing markup, value semantics, exports, peers, dependencies or default
interaction behavior. This is a compatible patch to 1.4.0, not a new component
release. Jinja producer options remain outside the npm API; their rendered
state hooks are documented on the public component pages. Host adapters adopt
the annotations independently through identified artifact intake.

The accepted appearance is protected by the Field parity browser contracts,
Select and Date Picker rendering/state tests, and accepted stylesheet baselines.
Release-specific checks remain required. Certification stays in preview;
merging to main starts the existing automatic tag/publish/release chain.

## 1.4.0 Compatible Additions

The release target adds `@wpmoo/ui/overlay-scrollbar.js`, its aggregate
`OverlayScrollbar` export and documented opt-in Sass styling. The document or
same-owner element remains the native scrollport; initialization is explicit
and paired with disposal. Forced colors, printing and horizontal overflow keep
native scrollbars. Existing exports, component defaults, peers and dependencies
remain compatible with 1.3.0. This additive public surface requires a minor
release rather than reusing the already published 1.3.0 version.

Logical `text-start`/`text-end` utilities share one standalone/scoped definition.
The catalog consumes the shared scrollbar, fades compact TOC and Separator
together, preserves native fragments and input, removes the competing Charts
navigator and wraps long Installation URLs with Bootstrap utilities.

Theme token restoration remains owner-local. Separate catalog direction
bootstrap owns document-direction observation and physical Sidebar placement;
it does not change public Core Sidebar ownership.

The explicit document-scroll option has one native-visibility bridge outside
the owner: `html.scrollbar-overlay-native` controls only `scrollbar-width`,
with `::-webkit-scrollbar` controlling only `display`. Exact print/forced-color
fallback restores native visibility. This exception does not permit document
theme tokens, typography or layout rules. Contract tests constrain the exact
selectors, property/value/priority pairs and media context, with mutation cases
rejecting wider selectors, extra declarations and theme/layout leakage.

Candidate gate definitions: [scrollbar browser contracts](../../tests/test_overlay_scrollbar_browser.py),
[catalog reading chrome](../../tests/test_catalog_reading_chrome_browser.py),
[direction/first-paint browser contracts](../../tests/test_catalog_browser.py),
[native visibility boundary/mutation checks](../../tests/test_css_contract.py),
[package verification](../../tests/test_package.py) and
[tarball identity checks](../../tests/test_package_release.py).
These define required verification; they are not a final passing release attestation.
Verification remains release-specific. Component certification stays in preview;
unexecuted browser/device checks are not inferred from the version increment.
Merging this version to main starts the existing automatic tag/publish/release
chain, so release readiness must be established before the maintainer merges.

## 1.3.0 Compatible Additions

Accordion gains an optional plus/minus indicator through the additive
`data-accordion-indicator="plus-minus"` and `data-accordion-plus` markup hooks.
The default chevron, Bootstrap Collapse ownership, existing classes and
ARIA relationships remain compatible. The shared Accordion Panels recipe
composes those hooks with Bootstrap utilities for separate bordered panels,
neutral action labels, stable heading fragments and single/multiple-open modes.
Its catalog examples retain their authored SVG paths and render at native size.

Jinja recipe signatures are catalog producer inputs and are excluded from npm.
The additive indicator CSS/HTML contract is distributed; this meaningful public
surface addition makes the release minor. Public exports, file globs, peers,
dependencies and optional ESM lifecycle remain unchanged from 1.2.2.

Alert preserves explicit SVG width and height independently, applying its 1rem
defaults only to unspecified dimensions. Existing default icons retain their size.
This compatible correction accompanies the Accordion additions.

Verification: [Accordion contracts](../../tests/test_accordion.py),
[Panels contracts](../../tests/test_accordion_panels.py),
[Panels browser checks](../../tests/test_accordion_panels_browser.py) and
[Alert browser checks](../../tests/test_alert_browser.py) cover the accepted
markup, indicator interaction, themes, direction, containment and sizing.
Component certification remains in preview; this release does not promote
the accepted catalog examples to certified components.

## 1.2.2 Compatible Fixes

Navigation preserves parent hover throughout a submenu, resolves active fill
within each navigation group, and excludes disabled controls from hover
ownership. Existing Bootstrap active-background variables carry this correction;
no new public class or selector contract, token, ESM lifecycle or export is introduced.

The catalog's internal DataTable Jinja producer preserves readable column
minimums and native percentage widths. Its optional `min_width` input is not an
npm API: Jinja templates and their signatures are outside the distributed package
and public compatibility boundary. The rendered table uses existing header width
declarations and the existing responsive frame. This release preserves the
1.2.1 package contract and is a patch release.

Verification: [Navigation hover contracts](../../tests/test_navigation_hover_browser.py)
cover submenu ownership, disabled controls, themes and directions;
[DataTable browser contracts](../../tests/test_datatable_browser.py) cover
readable minimums, opt-out, rem scaling, percentage sizing and contained scrolling.
The [DataTable template contracts](../../tests/test_datatable.py) also verify
escaped width attributes and rejection of percentage minimums. These inputs
remain trusted application CSS lengths, not an untrusted CSS sanitizer API.

Development-only updates combine the accessibility checker from dependency PR
#98 (`axe-core` 4.14.0) with the newer catalog toolchain from #102 (`wrangler`
4.149.0 and transitive `sharp` 0.35.5). Both remain dev-only, and the Wrangler
manifest range is unchanged. The existing Node 22 development/CI runtime meets
the updated tools' requirements. Public peers, exports and distributed file
inventory are unchanged; these updates retain the patch classification.

Verification: comparison with `6733da1` confirms unchanged manifest exports,
file globs, side effects, peer dependencies, scripts and Wrangler range; the
combined lock marks axe-core, Wrangler and Sharp as dev-only. The existing
boundary recorder builds the candidate and confirms the same 103 approved npm
inventory paths. The package metadata and inventory contracts in
[test_core_docs_boundary.py](../../tests/test_core_docs_boundary.py) protect
these checks, and the release gate revalidates the prepared tarball itself.

## 1.2.1 Compatible Fixes

DataTable composes the existing Empty presentation while retaining its own
live region, visibility, result messages and filter-reset action. Legacy empty
title and description hooks remain supported. Catalog release notes show one
current version and link earlier releases to GitHub. Export paths and explicit
ESM lifecycle contracts are unchanged; this is a patch release.
Unchecked checkbox borders inside semantic Alerts inherit the Alert foreground
while checked, indeterminate, invalid and keyboard-focus states retain their
existing control behavior.

## 1.2.0 Compatible Additions

The next minor release adds the public Empty surface and optional Tabs content
height while preserving the frozen 1.1.0 package exports and runtime contracts.
Empty supplies a standard dashed boundary, text, icon and action presentation;
Bootstrap utilities remain caller-controlled overrides. Tabs retains stable
height by default and permits content height through an optional argument.

App container sizing, release job budgets and initial-branch scan ranges are
compatible fixes in the same release. Empty remains a source-only certification
candidate; its catalog availability does not promote release certification.
Historical API inventories and published source archive hashes remain intact.

The source-only boundary is verified by the certification-candidate checks in
[test_empty.py](../../tests/test_empty.py). The released 1.1.0 TOC/API surface
is protected by `test_1_1_api_freeze_preserves_the_released_toc_surface` in
[test_certification_contract.py](../../tests/test_certification_contract.py).
A separate 1.2.0 export inventory is not planned for this additive release:
the exported paths and ESM lifecycle contracts are unchanged, so the immutable
1.1.0 inventory remains their compatibility guard.

## 1.0.0 Stable Public Contract

The stable package preserves RC11's exports, packed file inventory, public Sass
configuration, CSS hooks and optional runtime lifecycle. The current inventory
is `src/certification/api-freeze-1.0.0.json`; the RC11 inventory is unchanged as a
historical removal guard. The version promotion adds no component or behavior.

Compatible additions after this freeze belong to 1.1.0. Removing or incompatibly
changing a documented public contract requires a new major release. Package
stability does not promote component certification: the manifest remains
`preview`, with manual accessibility and browser/device evidence still governed
by SUPPORT.md. Consumer release pins follow publication and their own validation.

## 1.0.0-rc.11 Entrypoints and Feature Freeze

RC11 preserves the RC10 package exports, public Sass configuration and runtime
contracts. Connected Steps navigation uses `nav_menu(style="steps")` and the
item's independent `completed` state. Its public CSS hooks are `.nav-steps` and
`data-nav-completed="true"`; the current route does not imply completion.

The scoped `.border-dashed` utility changes only border style. Surfaces with
borders declared on all four sides, such as Card or an element with `.border`,
keep their border width, color and radius. A directional border alone does not
meet that precondition; use `.border` first when a full outline is intended.
Its Sass partial is packaged through the
existing source glob and included by both full and scoped CSS entrypoints;
there is no additional stylesheet or JavaScript entrypoint. The catalog groups
Border and Scroll Fade under Utilities.

The RC11 inventory established the feature freeze for stable 1.0.0. Work toward
that checkpoint is limited to necessary bug fixes, verification and release
preparation; new capabilities belong to 1.1.0. Historical inventories stay
unchanged as removal guards. Preview certification remains explicit until the
separate certification gates are satisfied. Adapter release pins follow
publication and their own consumer validation.

## 1.0.0-rc.10 Entrypoints

RC10 preserves the RC9 state bootstrap and release manifest. It adds the public,
side-effect-free `./sheet.js` ESM entrypoint and the aggregate's named
`initSheets(root)` export. Initialization is explicit and delegates opening to
Bootstrap Offcanvas; importing the module never scans the document.

On 2026-10-03 the maintainer approved deferring Chart dependencies until use.
The aggregate replaces its synchronous named/default-namespace `Chart` export
with `loadChart()`, which returns a promise for the standalone Moo Chart
constructor. Both aggregate variants dynamically import the adjacent
`chart.js`; repeated calls use the native ESM module cache and share the direct
module's instance registry. Hosts must keep that asset beside the aggregate and
handle any rejected loading promise. The standalone `chart.js`/`chart.min.js`
APIs and package file/export paths remain unchanged. Chart.js and its color
dependency are bundled only into the standalone Chart assets, retaining their
license notices there. Historical aggregate records describe the earlier
synchronous API; the current RC10 freeze records this approved migration.

The current API inventory records the exact package exports/files and runtime
exports. Historical freezes remain removal guards. Radio Group choice cards,
responsive DataTable behavior and Body typography consume the existing CSS/Sass
entrypoints without introducing another runtime or stylesheet export.

Release-facing links use RC10 in the candidate commit. Adapter release pins
must follow publication and consumer validation; local release preparation does
not establish a published artifact or a certified component set.

## 1.0.0-rc.9 Entrypoints

RC9 replaces the public classic browser export
`./theme-prepaint.js` with `./state.js`. The script restores Theme and
Direction on a resolved Moo owner, or Sidebar state on a keyed Sidebar wrapper,
when invoked as the first child of that owner. The release manifest hashes the
new script bytes. This is a breaking export rename; no alias is shipped.
Adapter release pins must be updated after RC9 publication and consumer tests.
Release-facing documentation links, including third-party notices and the CDN
example, point at RC9 in the release commit. The release flow accepts the
short propagation window and requires no second merge to repoint those links.

## 1.0.0-rc.8 Entrypoints

RC8 carries the RC7 public package surface forward and adds two deliberately
small release-facing contracts: `./theme-prepaint.js` is the classic,
placement-dependent browser prepaint script, and `./release-manifest.json` is
the metadata entrypoint that records SHA-256 hashes for the adapter-facing
`./moo.css`, `./moo-ui.css`, and `./theme-prepaint.js` bytes. The prepaint file
is not an ESM runtime entrypoint and must be placed before the first themed
content; hosts must consume the published bytes rather than copying source.
Catalog CodePen URLs intentionally use the active `package.json` version,
including the RC8 release candidate. The release flow accepts the brief CDN
propagation window after the release tag is created; a second synchronization
merge solely to change CodePen URLs is not required. This is a conscious
release policy, not an accidental unpublished-package reference. The RC8 API
freeze and tarball verifier continue to protect the package surface itself.

### CodePen release-policy verification

The catalog contract test
[`test_codepen_payloads_use_the_active_package_version`](../../tests/test_catalog.py#L1117-L1140)
rebuilds the generated catalog and asserts that every `@wpmoo/ui@...` token in
each CodePen CSS/JS payload resolves to the active `package.json` version. The
same contract runs in the quick tier and is included in the release gate before
publish ([`npm-publish.yml`](../../.github/workflows/npm-publish.yml#L58-L63)).
This is the verification record for accepting the short CDN propagation window;
it does not require a second synchronization merge.

## 1.0.0-rc.7 Entrypoints

RC7 carries forward the RC6 public export and package-file inventory without
adding or removing an entrypoint. The direct `app`/`page` layout contract is
documentation-only and introduces no runtime export. The current API freeze
revalidates the CSS, ESM, Sass, metadata, and artifact-variant surface against
`package.json` and `certification.json`; changes to that surface require an
explicit freeze update.

## 1.0.0-rc.6 Entrypoints

RC6 carries forward the RC5 public export and package-file inventory without
adding or removing an entrypoint. The current API freeze revalidates the CSS,
ESM, Sass, metadata, and artifact-variant surface against `package.json` and
`certification.json`; changes to that surface require an explicit freeze
update.

## 1.0.0-rc.5 Entrypoints

RC5 carries forward the RC4 public export and package-file inventory without
adding or removing an entrypoint. The current API freeze revalidates the CSS,
ESM, Sass, metadata, and artifact-variant surface against `package.json` and
`certification.json`; changes to that surface require an explicit freeze
update.

## 1.0.0-rc.4 Entrypoints

Schema version `0.1` permits additive optional properties under
`publicEntrypoints`. The `metadata` entrypoint group is optional so older
`0.1` manifests that only declare `css`, `esm`, and `sass` remain valid. New
manifests should include `metadata` when `certification.json` and
`package.json` are part of the public package contract. This stays guarded by
`tests/test_certification_contract.py`, which accepts the optional metadata
schema property and validates the lifecycle records against package exports.

The aggregate ESM bundle, `./moo-ui.js` and `./moo-ui.min.js`, is published as
a side-effect-free convenience namespace. Importing it exposes the same
lifecycle classes as the individual component modules; it must not scan or
initialize the document automatically.

The Sass source entrypoints, `./scss/config`, `./scss/moo-ui`,
`./scss/moo-core`, `./scss/components`, and `./scss/settings`, are published
as documented source facades. `./scss/config` is the public variable allow-list;
the other entries let hosts compile the full or scoped Moo UI layer without
importing private partial paths. `tests/test_package.py` verifies aggregate
imports, export parity, and package-read side effects for this public surface.

The full `./moo-ui.css` build emits Moo UI's standalone root/body theme bridge
before Bootstrap's reboot body rules. This keeps the full replacement path
self-contained for pages that set `data-bs-theme` synchronously before loading
the stylesheet, without adding a second public CSS entrypoint to the scoped
`./moo.css` migration contract.

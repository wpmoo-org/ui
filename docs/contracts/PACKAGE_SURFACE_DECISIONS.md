# Package Surface Decisions

This file records package-surface decisions that are intentionally broader
than one component page.

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

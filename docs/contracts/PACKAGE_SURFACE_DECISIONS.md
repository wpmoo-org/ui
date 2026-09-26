# Package Surface Decisions

This file records package-surface decisions that are intentionally broader
than one component page.

## 1.0.0-rc.9 Development Candidate

The local RC9 candidate replaces the public classic browser export
`./theme-prepaint.js` with `./state.js`. The script restores Theme and
Direction on a resolved Moo owner, or Sidebar state on a keyed Sidebar wrapper,
when invoked as the first child of that owner. The release manifest hashes the
new script bytes. This is a breaking export rename; no alias is shipped in the
candidate. RC8 remains the published registry release, and release-mode adapter
pins remain on RC8 until RC9 is actually published.
Release-facing documentation links, including third-party notices and the CDN
example, point at the active package version before tagging. The release flow
accepts the short propagation window and requires no second merge to repoint
those links.

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

# Package Surface Decisions

This file records package-surface decisions that are intentionally broader
than one component page.

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

# Moo UI 1.0.0-rc.1 Clean Install Rehearsal

Generated: 2026-08-06
Status: Pass with documented limitations (rehearsal against the packed 0.9.0 tarball; repeat verbatim against the final RC tarball before tagging)
Scope: Clean-room installation of `@wpmoo/ui` in an empty consumer project following the documented install path (catalog Installation page), plus the documented scoped gradual-adoption path.

## Environment

- Host: macOS 26.5.2
- Node: v26.5.0, npm 11.17.0
- Tarball: `wpmoo-ui-0.9.0.tgz` packed from the dev checkout (`npm pack`)
  - sha256: `d61172626484771e195d85d610ebaca92a65a66b5ec00c6e0f61d3b9a27db091`
  - Source commit: not recorded — this rehearsal predates the
    `--source-commit` provenance binding added to the certification
    generators later in Phase 6. The final RC re-run must capture the
    checkout's exact commit alongside the tarball sha256.
- Registry substitution: `@wpmoo/ui` is not published yet, so the consumer
  installed the local tarball in place of the registry package
  (`npm install ../wpmoo-ui-0.9.0.tgz bootstrap` instead of
  `npm install @wpmoo/ui bootstrap`). Everything downstream of the package
  boundary is identical; the published RC must repeat this rehearsal.

## Steps Executed

1. Fresh empty directory; `npm init -y`.
2. `npm install <tarball> bootstrap` — installed cleanly, 0 vulnerabilities.
   - Bootstrap resolved to 5.3.8 (`^5.3.8`), the latest lane of the
     `>=5.3.0 <5.4` peer range — matches bootstrap-compatibility.json.
3. Verified every documented package export resolves from the consumer:
   - `@wpmoo/ui/moo-ui.css`, `@wpmoo/ui/moo.css`
   - `@wpmoo/ui/combobox.js`, `@wpmoo/ui/sidebar.js`,
     `@wpmoo/ui/context-menu.js`, `@wpmoo/ui/datatable.js`
   - `@wpmoo/ui/certification.json`
4. Full-build consumer page (`moo-ui.css` + Bootstrap bundle + optional ESM
   import), served from the consumer directory, loaded in headless Chromium:
   - `btn btn-primary` receives Moo UI styling (background rgb(24, 24, 27)).
   - Bootstrap dropdown opens via its data API (`aria-expanded` → `true`).
   - `Combobox.getOrCreateInstance` and `DataTable.getOrCreateInstance` are
     functions after a side-effect-free ESM import.
   - Console and page errors: none.
5. Scoped-adoption consumer page (Bootstrap CSS first, then `moo.css`,
   migrated markup inside `.moo-ui`):
   - Inside `.moo-ui`: button styled by the Moo layer.
   - Outside `.moo-ui`: button keeps stock Bootstrap styling
     (rgb(108, 117, 125)) — the boundary is respected, matching the
     Installation page's "Scoped Gradual Adoption" guidance.

## Migration Path Cross-Check

SUPPORT.md's migration guidance is the SemVer policy (patch releases never
intentionally break public contracts; breaking changes only in a minor with
an explicit migration note). `1.0.0-rc.1` has no predecessor 1.x line, so no
1.x-to-1.x migration note applies; the 0.x → 1.0 surface is frozen by
`src/certification/api-freeze-0.9.0.json` (Task 7 confirmed no drift since).
The documented gradual path from a plain Bootstrap 5.3 app is the scoped
adoption path verified above.

## Doc Drift Found

None. The Installation page's npm command, stylesheet paths, Bootstrap
bundle usage, optional-ESM module names, and the `getOrCreateInstance` /
`dispose` lifecycle all match the installed package. CDN URL shapes
(unpkg/jsdelivr with `/dist/assets/css/...`) match the package layout but
cannot be verified until the package is published — re-check at the real RC.

## Result

- [ ] Pass
- [X] Pass with documented limitations
- [ ] Fail

Final notes: Re-run against the actual 1.0.0-rc.1 tarball (same steps) and
record its sha256 and source commit in the release attestation evidence. The
sole limitation on this rehearsal is the missing source commit above; every
functional check (install, exports, styling boundary, migration path) passed
cleanly.

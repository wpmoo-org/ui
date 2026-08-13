# Moo UI 1.0.0-rc.2 Manual Acceptance

Generated: 2026-08-12
Status: Accepted - 420/420
Scope: Release-candidate visual and interaction acceptance for Moo UI Core
`1.0.0-rc.2` after the post-rc1 catalog polish and rc2 review follow-up
commits.

## Build Under Review

- HTML repository commit: `5b5ca9e2207b829ffc9bff9bad49a3f6d434c722`
- Root workspace commit at evidence transfer: `7bfb263fba3ff579625a4bd4bffaef5c5f771c0c`
- Package version: `1.0.0-rc.2`
- Package tarball sha256: `af4807d4cdc0f7f7e94fd371b30afee85e784f03151c18f9046def43201b77a4`
- Conformance kit sha256: `969550911564fe24797ba67bce26f003adb9c6245dea7c311d205b9705c33328`
- Certification manifest sha256: `1ed562c90906bf791b674970e4b9222259b597039b08b627f5f31c636b3f4f88`
- Certification attestation sha256: `2d4e400c74d17e82dd04ff6ec2a6f233bd42226023e4a87aea5c4cd283102ec1`
- Catalog URL: `http://localhost:4174/`
- Acceptance portal: `http://localhost:4174/acceptance/rc2/`
- Reviewer: Ahmet Cangir
- Acceptance export generated at (UTC, ISO-8601): `2026-08-12T22:34:20.510Z`
- Build metadata captured at (UTC, ISO-8601): `2026-08-13T07:59:26Z`

## Rehearsal Artifacts

These hashes were produced by `python3 scripts/rehearse-rc.py` from the clean
`5b5ca9e2207b829ffc9bff9bad49a3f6d434c722` build-under-review commit.

- Package: `/Users/cng/WPMoo/workspace/projects/ui/html/dist/rc-rehearsal/wpmoo-ui-1.0.0-rc.2.tgz`
- Conformance kit: `/Users/cng/WPMoo/workspace/projects/ui/html/dist/rc-rehearsal/conformance-kit/moo-ui-conformance-kit-1.0.tar.gz`
- Manifest: `/Users/cng/WPMoo/workspace/projects/ui/html/dist/rc-rehearsal/certification-manifest.json`
- Attestation: `/Users/cng/WPMoo/workspace/projects/ui/html/dist/rc-rehearsal/certification-attestation.json`

## Acceptance Source

The portal export was transferred from
`/Users/cng/.codex/attachments/0002ccc8-79be-4879-9a5e-8568263abb07/pasted-text.txt`.
The export reports:

- Result: `420/420`
- Components: `42`
- Safari checks: `42 components x 4 checks = 168`
- iPhone checks: `42 components x 3 checks = 126`
- Android checks: `42 components x 3 checks = 126`
- Mobile keyboard rows: `N/A`; they are intentionally excluded from the 420
  required checks.
- Unchecked rows: none

## Devices

- [x] macOS Safari
  - Device/model: MacBook
  - macOS version: Tahoe 26.5.2
  - Safari version: 26.5.2 (21624.2.5.11.8)
  - Package sha256: `af4807d4cdc0f7f7e94fd371b30afee85e784f03151c18f9046def43201b77a4`
  - Reviewer: Ahmet Cangir
  - Reviewed at (UTC, ISO-8601): `2026-08-12T22:34:20.510Z`
  - Result: passed
  - Checks covered: visual, fixture, voice, keyboard.
- [x] iOS Safari
  - Device/model: iPhone
  - iOS version: 26.5.2
  - Safari version: 26.5.2
  - Package sha256: `af4807d4cdc0f7f7e94fd371b30afee85e784f03151c18f9046def43201b77a4`
  - Reviewer: Ahmet Cangir
  - Reviewed at (UTC, ISO-8601): `2026-08-12T22:34:20.510Z`
  - Result: passed
  - Checks covered: visual, fixture, voice. Keyboard: N/A.
- [x] Android Chrome
  - Device/model: Samsung Tab S6 Lite
  - Android version: 14
  - Chrome version: 150.0.7871.186
  - Package sha256: `af4807d4cdc0f7f7e94fd371b30afee85e784f03151c18f9046def43201b77a4`
  - Reviewer: Ahmet Cangir
  - Reviewed at (UTC, ISO-8601): `2026-08-12T22:34:20.510Z`
  - Result: passed
  - Checks covered: visual, fixture, voice. Keyboard: N/A.

## Global Catalog Checks

- [x] Fixture URLs needed by this rc2 pass open without 404.
- [x] Each fixture matching a checked component opens cleanly.
- [x] Fixture behavior matches the catalog docs for keyboard, focus, state,
      dismissal, overlay behavior, and responsive behavior at the component's
      tier depth.
- [x] Dark, RTL, and responsive fixture cases render where provided.
- [x] No fixture uses stale markup from earlier component versions.
- [x] Safari keyboard checks are complete for every component.
- [x] iPhone voice-control checks are complete for every component where the
      interaction is applicable.
- [x] Android voice-access checks are complete for every component where the
      interaction is applicable.
- [x] Mobile keyboard rows are marked `N/A` because the manual pass used touch
      and voice-control flows on those devices.
- [x] Catalog shell is stable in light and dark themes.
- [x] Sidebar navigation, search, theme toggle, GitHub link, and page actions
      stay visually balanced.
- [x] Page action buttons are compact, aligned, and readable.
- [x] Previous/next page pagination follows the left navigation order.
- [x] Code blocks use the current theme instead of forcing dark mode.
- [x] Code line numbers are generated as presentation chrome and are not copied
      as source content.
- [x] Code copy buttons have visible button backgrounds, keep their icon
      visible, and show copied feedback with enough spacing.
- [x] Collapsed example source panels center the View Code button within the
      faded code area.
- [x] Inline code chips use the approved neutral chip style everywhere.
- [x] Component reference text appears inside the Component reference metadata
      table, including extra Bootstrap references on Data Table and Sidebar.
- [x] No component page shows duplicate intro/default examples created by the
      new intro pattern.
- [x] No obvious layout shift, text overlap, or clipped controls at desktop,
      tablet, and phone widths.
- [x] Console is clean on the reviewed pages.

## Targeted Re-Acceptance Notes

- Combobox keyboard delta: accepted on Mac Safari after the Phase 2B keyboard
  fix. The accepted path is `/components/combobox/` and
  `/tests/fixtures/certification/combobox.html`; ArrowDown/Enter keeps focus on
  the input and selects the expected option. This is tracked separately from
  the 420/420 portal total and was user-confirmed during the Safari keyboard
  pass.
- Navigation chevron finding: no row is excluded from the export. The live
  Navigation row remains accepted in the matrix below.

## Component Matrix

### Accordion

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Alert

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Alert Dialog

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Avatar

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Badge

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Breadcrumb

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Button

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Button Group

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Card

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Checkbox

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Close Button

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Collapsible

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Combobox

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Context Menu

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Data Table

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Dialog

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Dropdown Menu

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Field

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Form

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Input

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Input Group

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Kbd

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Menubar

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Navigation

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Pagination

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Popover

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Progress

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Radio Group

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Select

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Separator

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Sheet

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Sidebar

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Skeleton

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Spinner

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Switch

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Table

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Tabs

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Textarea

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Toast

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Toggle Group

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Tooltip

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

### Typography

| Device | Visual | Fixture | Voice | Keyboard |
| --- | --- | --- | --- | --- |
| Safari | [x] | [x] | [x] | [x] |
| iPhone | [x] | [x] | [x] | N/A |
| Android | [x] | [x] | [x] | N/A |

## Known Limitations

- None for rc2 manual acceptance.
- Mobile keyboard cells are `N/A` by review design; touch and voice-control
  checks cover iPhone and Android interaction acceptance.

## Acceptance Result

- [x] Pass
- [ ] Pass with documented limitations
- [ ] Fail

Final notes: Portal export is fully reconciled into this Markdown record.

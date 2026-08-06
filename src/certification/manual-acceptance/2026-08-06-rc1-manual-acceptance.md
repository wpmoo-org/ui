# Moo UI 1.0.0-rc.1 Manual Acceptance

Generated: 2026-08-06
Status: Draft — pending human execution against the final 1.0.0-rc.1 tarball
Scope: Release-candidate manual acceptance for all 42 Core components: real-device passes, manual keyboard/focus checks, and screen-reader smoke, per the certification plan's "Release candidate" cadence (exact tarball, local real devices, manual keyboard/focus/screen-reader checklist). Automated browser and Bootstrap-lane coverage is produced by the nightly matrix and is not repeated here.

## How to prepare

1. Build and install the exact RC tarball in a clean consumer project (Task 6
   rehearsal path), or serve the catalog from this checkout:
   `python3 dev.py --host 0.0.0.0` (catalog at `http://<host>:4173/`).
2. Record the exact browser and operating-system versions for every device —
   the release attestation's `realDevices` and `manualReviews` sections quote
   these verbatim (SUPPORT.md Browser Policy).
3. Execute against the RC package outputs, not against a mid-build tree.

## Test Devices

Fill in exact versions at execution time. The device set follows the
SUPPORT.md Browser Policy surfaces that automated CI cannot cover.

- [ ] MacBook (macOS, current and previous stable Safari majors)
  - macOS version:
  - Safari version:
  - Notes:
- [ ] iPhone (iOS, current and previous stable iOS Safari majors)
  - iOS version:
  - Safari version:
  - Notes:
- [ ] Android device (current stable Android Chrome)
  - Android version:
  - Chrome version:
  - Notes:

## URLs

- Catalog home: `/`
- Component page pattern: `/components/<slug>/`
- Certification fixture pattern: `/tests/fixtures/certification/<slug>.html`
- DataTable release-review preview: `/blocks/previews/datatable-release-review/`

## Component Matrix

Depth scales with the evidence-inventory profile (see
`src/certification/evidence-inventory.json`):

- **Visual**: catalog page in light + dark theme, LTR + RTL direction.
- **Interactive**: Visual plus keyboard operation (Tab / Shift+Tab,
  Enter/Space activation, arrow keys where documented), visible focus, focus
  return after dismissal.
- **Overlay**: Interactive plus trigger open/close, Escape, outside dismiss,
  focus trap (dialog family) and focus return.
- **Composite**: Overlay depth plus the documented end-to-end interaction and
  a screen-reader smoke pass.

### Tier 0 — static (Visual)

- [ ] avatar
- [ ] badge
- [ ] card
- [ ] kbd
- [ ] progress
- [ ] separator
- [ ] skeleton
- [ ] spinner
- [ ] table
- [ ] typography

### Tier 0 — interactive (Interactive)

- [ ] breadcrumb
- [ ] button
- [ ] button-group
- [ ] checkbox
- [ ] close-button
- [ ] field
- [ ] input
- [ ] input-group
- [ ] navigation
- [ ] pagination
- [ ] radio-group
- [ ] select
- [ ] switch
- [ ] textarea

### Tier 1 — Bootstrap data-API (Interactive)

- [ ] accordion
- [ ] alert
- [ ] collapsible
- [ ] dropdown-menu
- [ ] tabs

### Tier 1 — native state (Interactive)

- [ ] toggle-group

### Tier 2 — overlay (Overlay)

- [ ] dialog
- [ ] popover
- [ ] sheet
- [ ] toast
- [ ] tooltip

### Tier 3 — composites (Composite)

- [ ] alert-dialog
- [ ] combobox
- [ ] context-menu
- [ ] datatable
- [ ] menubar
- [ ] sidebar
- [ ] form

## Global Checks

Run once per device, across the catalog:

- [ ] Desktop Tab / Shift+Tab / Escape flow recorded
  - Notes:
- [ ] Focus is always visible and never trapped outside a dialog surface
  - Notes:
- [ ] Reduced-motion setting respected (no large non-essential animation)
  - Notes:
- [ ] 200% zoom: no clipped controls or lost content on key pages
  - Notes:
- [ ] Light + dark theme contrast spot check on each device
  - Notes:
- [ ] RTL direction spot check (at minimum: navigation, datatable, sidebar)
  - Notes:
- [ ] VoiceOver smoke on macOS Safari (dialog, combobox, datatable, toast)
  - Notes:
- [ ] VoiceOver smoke on iOS Safari (dialog, sidebar, datatable)
  - Notes:
- [ ] TalkBack smoke on Android Chrome (dialog, datatable)
  - Notes:
- [ ] Touch targets usable on phone/tablet (no hover-only interactions)
  - Notes:
- [ ] Console clean on every page visited (no errors, no deprecation noise)
  - Notes:
- [ ] Known limitations written down
  - Notes:

## Acceptance Result

- [ ] Pass
- [ ] Pass with documented limitations
- [ ] Fail

Final notes:

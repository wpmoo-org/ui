# Moo UI 1.0.0-rc.2 Manual Acceptance

Generated: 2026-08-12
Status: Draft — no manual pass is claimed until the reviewer fills the device
records, component matrix, global checks, known limitations, and final result.
Scope: Release-candidate visual and interaction acceptance for Moo UI Core
`1.0.0-rc.2` after the post-rc1 catalog polish and rc2 review follow-up
commits.

## How to use this form

1. Review the local catalog for visual acceptance while polish is still in
   progress.
2. For release evidence, repeat the final pass against the exact rc2 package
   output and record the package hash below.
3. Mark a checkbox only after the check is tested and passed. Leave failed or
   skipped checks unchecked and write the reason in the related notes line.
4. Do not mark the final result as `Pass` while any required row remains
   unchecked, unreconciled, or tested only against an exploratory dev build.

## Build Under Review

- HTML repository commit:
- Root workspace commit:
- Package version:
- Package sha256:
- Catalog URL:
- Reviewer:
- Reviewed at (UTC, ISO-8601):

## Acceptance Portal

- Portal: `/acceptance/rc2/`
- Scope: all component catalog pages and matching certification fixtures.
- Default behavior: select a checklist item on the left to open its catalog
  page or certification fixture in the right-side frame.
- The path shown above the frame is a normal link; right-click it if the page
  needs to be opened in a separate browser tab.
- Checkbox state is stored in the local browser only. Transfer the final
  results back into this Markdown record before using it as release evidence.

## Certification Fixtures

Use the portal when available, or open fixture URLs directly:
`/tests/fixtures/certification/<slug>.html`.

- [ ] Fixture URLs needed by this rc2 pass open without 404.
  - Notes:
- [ ] Each fixture matching a checked component opens cleanly.
  - Notes:
- [ ] Fixture behavior matches the catalog docs for keyboard, focus, state,
      dismissal, overlay behavior, and responsive behavior at the component's
      tier depth.
  - Notes:
- [ ] Dark, RTL, and responsive fixture cases render where provided.
  - Notes:
- [ ] No fixture uses stale markup from earlier component versions.
  - Notes:

## Interaction Checks

Use the portal's device tabs to record interaction checks per device.

- [ ] Safari keyboard checks are complete for every component.
  - Notes:
- [ ] iPhone voice-control checks are complete for every component where the
      interaction is applicable.
  - Notes:
- [ ] Android voice-access checks are complete for every component where the
      interaction is applicable.
  - Notes:
- [ ] Any component marked not applicable has a note explaining why.
  - Notes:

## Devices

- [ ] macOS Safari
  - Device/model:
  - macOS version:
  - Safari version:
  - Package sha256:
  - Reviewer:
  - Reviewed at (UTC, ISO-8601):
  - Result (passed/failed):
  - Notes:
- [ ] iOS Safari
  - Device/model:
  - iOS version:
  - Safari version:
  - Package sha256:
  - Reviewer:
  - Reviewed at (UTC, ISO-8601):
  - Result (passed/failed):
  - Notes:
- [ ] Android Chrome
  - Device/model:
  - Android version:
  - Chrome version:
  - Package sha256:
  - Reviewer:
  - Reviewed at (UTC, ISO-8601):
  - Result (passed/failed):
  - Notes:

## Global Catalog Checks

- [ ] Catalog shell is stable in light and dark themes.
  - Notes:
- [ ] Sidebar navigation, search, theme toggle, GitHub link, and page actions
      stay visually balanced.
  - Notes:
- [ ] Page action buttons are compact, aligned, and readable.
  - Notes:
- [ ] Previous/next page pagination follows the left navigation order.
  - Notes:
- [ ] Code blocks use the current theme instead of forcing dark mode.
  - Notes:
- [ ] Code line numbers are generated as presentation chrome and are not copied
      as source content.
  - Notes:
- [ ] Code copy buttons have visible button backgrounds, keep their icon
      visible, and show copied feedback with enough spacing.
  - Notes:
- [ ] Collapsed example source panels center the View Code button within the
      faded code area.
  - Notes:
- [ ] Inline code chips use the approved neutral chip style everywhere.
  - Notes:
- [ ] Component reference text appears inside the Component reference metadata
      table, including extra Bootstrap references on Data Table and Sidebar.
  - Notes:
- [ ] No component page shows duplicate intro/default examples created by the
      new intro pattern.
  - Notes:
- [ ] No obvious layout shift, text overlap, or clipped controls at desktop,
      tablet, and phone widths.
  - Notes:
- [ ] Console is clean on the reviewed pages.
  - Notes:

## Component Matrix

For each component, check the component page in light and dark themes, then spot
check RTL where the page provides an RTL example. Interactive components also
need keyboard/focus checks appropriate to the control.

### Intro, Usage, and Example Polish

- [ ] Accordion — three-item intro starts closed; Usage explains how to use the
      component; examples and reference look consistent.
  - Notes:
- [ ] Alert — intro title and description explain Alert; icon, variants, and
      reference are clean.
  - Notes:
- [ ] Alert Dialog — intro and Usage are end-user docs, not macro docs; dialog
      open/close and focus return work.
  - Notes:
- [ ] Avatar — Basic appears before fallback initials; labels use accepted
      copy such as `CNGR`; reference is folded into the metadata table.
  - Notes:
- [ ] Badge — intro and examples still read cleanly after the shared intro
      pattern.
  - Notes:
- [ ] Breadcrumb — page remains visually stable and navigation semantics are
      clear.
  - Notes:
- [ ] Button — intro replaces the old duplicated Default example; Primary
      appears before Outline; Sizes follow variants.
  - Notes:
- [ ] Button Group — intro uses the composition example; duplicate Composition
      section is removed; focus behavior matches accepted click/keyboard ring
      behavior.
  - Notes:
- [ ] Card — intro and Usage explain how to use Card markup, not only where it
      is useful.
  - Notes:
- [ ] Checkbox — intro label and description explain Checkbox; checked,
      description, invalid, and RTL examples remain balanced.
  - Notes:
- [ ] Close Button — intro copy explains Close Button and the button can
      dismiss the example surface when tested.
  - Notes:
- [ ] Collapsible — examples and reference remain consistent after the shared
      reference treatment.
  - Notes:
- [ ] Context Menu — intro matches the dashed Right click here pattern, has no
      unwanted background, and is vertically centered.
  - Notes:
- [ ] Data Table — main demo follows the page heading without duplicate example
      heading; Usage appears below; public docs do not expose template
      parameters.
  - Notes:
- [ ] Dialog — page action buttons are compact; modal trigger, focus, backdrop,
      and close behavior work.
  - Notes:
- [ ] Dropdown Menu — intro button says Dropdown Menu; menu opens and closes
      with Bootstrap behavior.
  - Notes:
- [ ] Field — intro label says Form Field, placeholder/copy are accepted, and
      helper text is attached cleanly.
  - Notes:
- [ ] Form — form examples still use fieldset/field/group structure and do not
      regress after intro changes.
  - Notes:
- [ ] Input — intro label says Input and no extra intro description appears.
  - Notes:
- [ ] Input Group — intro label is removed or component-specific; addons align
      cleanly.
  - Notes:
- [ ] Kbd — intro uses the accepted command-key combination and key chips are
      visually balanced.
  - Notes:
- [ ] Menubar — menu keyboard and hover behavior remain stable.
  - Notes:
- [ ] Navigation — sidebar-list item with chevron does not imply an unopened
      dropdown, or the fallback behavior is visually acceptable.
  - Notes:
- [ ] Pagination — page actions and pagination examples remain compact and
      readable.
  - Notes:
- [ ] Popover — intro trigger copy is accepted and popover opens with the
      expected Bootstrap behavior.
  - Notes:
- [ ] Progress — intro example has enough width/spacing and does not look
      cramped.
  - Notes:
- [ ] Radio Group — intro options explain Radio Group; RTL examples use
      balanced text length.
  - Notes:
- [ ] Select — label, description, and options explain Select; native menu
      behavior remains clear.
  - Notes:
- [ ] Separator — intro is vertically centered, copy explains Separator, and
      horizontal/vertical examples are balanced.
  - Notes:
- [ ] Sheet — trigger, focus, dismissal, and reduced-motion behavior remain
      acceptable.
  - Notes:
- [ ] Sidebar — page structure remains intentionally different from ordinary
      components; extra Bootstrap reference text is folded into Component
      reference.
  - Notes:
- [ ] Skeleton — examples remain visually stable; no new intro pattern work was
      required.
  - Notes:
- [ ] Spinner — spinner examples remain centered and reduced-motion behavior is
      acceptable.
  - Notes:
- [ ] Switch — intro, description, invalid, and RTL examples use the accepted
      field/fieldset pattern; dark invalid checked thumb remains visible.
  - Notes:
- [ ] Table — intro example uses simple table text without badges and explains
      Table context.
  - Notes:
- [ ] Tabs — hover does not make an inactive tab look active; cursor remains
      default; transitions are fade-only with no vertical jump; RTL uses card
      panels.
  - Notes:
- [ ] Textarea — intro and field examples remain consistent with Input/Field.
  - Notes:
- [ ] Toast — trigger, placement, dismissal, and live-region behavior remain
      acceptable.
  - Notes:
- [ ] Toggle Group — grouped toggle state remains visually distinct and
      keyboard reachable.
  - Notes:
- [ ] Tooltip — intro trigger says Hover; tooltip appears on hover/focus and
      stays readable in dark theme.
  - Notes:
- [ ] Typography — intro text is centered, `Readable portals feel calm` uses
      the accepted h5 scale, and heading/utility examples remain readable.
  - Notes:

## Accessibility Smoke

- [ ] Keyboard focus is visible across Button, Button Group, Inputs, Tabs,
      Dropdown Menu, Dialog, Popover, Tooltip, Sheet, Toast, and composites.
  - Notes:
- [ ] Escape closes dismissible overlays where Bootstrap owns that behavior.
  - Notes:
- [ ] Dialog, Alert Dialog, Sheet, Combobox, Context Menu, Data Table, Menubar,
      Sidebar, and Toast receive a screen-reader smoke pass at their tier depth.
  - Notes:
- [ ] Touch access works for mobile-only devices; no required workflow depends
      only on hover or right-click.
  - Notes:
- [ ] Reduced-motion behavior is documented if a device/browser setting changes
      transitions.
  - Notes:

## Known Limitations

- [ ] Known limitations are listed here or explicitly marked as none.
  - Notes:

## Acceptance Result

- [ ] Pass
- [ ] Pass with documented limitations
- [ ] Fail

Final notes:

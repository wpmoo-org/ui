# Moo UI Core Support Policy

Moo UI Core is an open-source Bootstrap component system. This document defines
the public support boundary for the Core package. It does not cover separate
platform integrations or commercial products.

Moo UI is currently in the `0.x` development series. Production certification
is being introduced incrementally; a component's presence in the catalog does
not by itself mean that it has completed certification.

## Supported Public Surfaces

Moo UI treats the following documented surfaces as public contracts:

- package export paths;
- documented HTML classes, `data-*` attributes, ARIA relationships, and
  trigger/content structure;
- documented component selectors, variants, runtime CSS custom properties, and
  scoped versus unscoped stylesheet behavior;
- documented exports, options, lifecycle methods, and events of public ESM
  modules;
- variables explicitly listed by the future public Sass facade;
- the certification manifest and support-policy formats once published.

The Jinja macros used to build the catalog are internal build tools and are not
part of the npm package API. Their documented rendered HTML is public.

Internal SCSS partial paths, undocumented Sass variables, catalog build
internals, private JavaScript helpers, and test-fixture organization may change
without notice.

## Component Maturity

Moo UI records three independent maturity states:

1. **Ready** means the internal component macro is implemented and safe for
   composition inside the catalog. It is not a production-support claim.
2. **Accepted** means browser review has approved the component's visual and
   behavioral result for the reviewed states.
3. **Certified** means a specific release has passed the automated and manual
   evidence required by the component's risk tier.

One state does not imply the next. The existing component registry continues to
record readiness only; certification evidence is maintained separately.

## Bootstrap Compatibility

Moo UI is built reproducibly against Bootstrap 5.3.3. The package currently
declares Bootstrap `>=5.3.0 <5.4` as an optional peer dependency.

The production-certification program verifies each release against:

1. Bootstrap 5.3.0 as the declared minimum;
2. Bootstrap 5.3.3 as the canonical build;
3. the latest Bootstrap 5.3.x available at release time.

Until the complete release attestation is published, the package manifest stays
in preview. If a supported fixture fails, Moo UI will either fix the
incompatibility or narrow the declared range. It will not retain a range that
evidence does not support.

Bootstrap 6 is outside the current contract and will require a separate
compatibility program.

## Browser Policy

The intended modern browser policy for certified releases is:

- the current and previous stable Chrome major versions;
- the current and previous stable Edge major versions;
- the current and previous stable Firefox major versions;
- the current and previous macOS Safari major versions;
- the current and previous iOS Safari major versions;
- the current stable Android Chrome version.

Release attestations will record the exact browser and operating-system
versions actually tested. This moving policy does not imply support for beta,
preview, embedded, or discontinued browser versions.

Static CSS components should remain usable when JavaScript is unavailable.
Components that require Bootstrap's plugins or Moo's optional ESM modules use
progressive enhancement within their documented behavior boundary.

## Accessibility

Certification combines automated and manual evidence appropriate to component
risk. It includes semantic output, accessible names and relationships, keyboard
operation, focus visibility and return, reduced motion, theme contrast, zoom,
responsive behavior, and screen-reader smoke checks for changed complex
surfaces.

Automated checks alone do not constitute an accessibility guarantee. Known
limitations are published with the affected release rather than hidden behind
a passing aggregate score.

## Right-to-Left and Themes

Documented components are designed for both LTR and RTL direction and for Moo
UI's light and dark theme surfaces. Certification records the combinations
actually reviewed. A component-specific limitation must be disclosed in the
release attestation.

## Versioning Before 1.0

Although Semantic Versioning permits greater instability during `0.x`, Moo UI
uses a stricter policy:

- patch releases do not intentionally break public contracts;
- a necessary breaking change occurs only in a minor release;
- breaking changes include an explicit migration note;
- a compatibility or deprecation path remains for at least one full minor line
  where practical;
- production browser consoles remain free of deprecation noise.

For example, a contract deprecated in `0.5.0` remains compatible throughout the
`0.6.x` line and is removed no earlier than `0.7.0`, unless a security or data-
loss issue makes that unsafe.

After `1.0.0`, removal or incompatible change of a public contract requires a
new major release.

## What Counts as Breaking

Examples of breaking changes include:

- removing or renaming a documented package export;
- removing a required documented class, selector, `data-*` attribute, or ARIA
  relationship;
- changing a public ESM lifecycle in an incompatible way;
- removing or changing the meaning of a supported Sass variable;
- narrowing the supported browser or Bootstrap range;
- changing keyboard, focus, or dismissal behavior incompatibly.

Compatible additions include new components, optional entrypoints, variants,
public Sass variables, and behavior that does not invalidate an existing
contract. Accessibility and security corrections may produce small visual or
behavioral differences without being treated as breaking when the previous
behavior was unsafe or inaccessible.

## Certification Evidence

The certification program publishes two complementary artifacts:

1. a small immutable manifest distributed with the npm package, containing
   Core version, source revision, verified compatibility, certified component
   status, public entrypoints, and known-limitations references;
2. a detailed GitHub Release attestation containing exact test versions,
   automated and manual results, real-device sign-off, package hashes, waivers,
   and limitations.

A catalog component may be implemented and available before it completes this
release-specific certification process. Certification claims always identify
the package version they apply to.

## Generic Host Conformance

Moo UI will publish a host-neutral conformance contract and fixture bundle as a
language-neutral, hash-locked GitHub Release artifact. It will test concerns
such as CSS resets, asset order, scoping, direction, themes, focus, overlays,
plugin lifecycle, Content Security Policy, and console health.

Passing the generic contract does not automatically grant an “official
integration” designation. Platform-specific implementation, support, and
compatibility remain the responsibility of the integration that consumes it.

## Reporting Problems

Report reproducible Core issues through the repository issue tracker:

https://github.com/wpmoo-org/ui/issues

Include the Moo UI version, Bootstrap version, browser and operating system,
reduced test case, expected behavior, and actual behavior. For accessibility
issues, include the input method or assistive technology when available.

Security-sensitive reports should not include secrets, credentials, customer
data, or private production content in a public issue. Use the repository's
published security-reporting channel when one is available.

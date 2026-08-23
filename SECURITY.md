# Security Policy

Moo UI is primarily a CSS-first Bootstrap component system with optional public
ESM modules for documented gaps such as Combobox and Sidebar.

## Supported Versions

Security review covers the current `1.0.0-rc.3` release-candidate line. Older
tags remain available for source inspection, but fixes are prepared against the
current development branch.

## Reporting A Vulnerability

Please do not open a public issue for a suspected vulnerability.

Use GitHub's private vulnerability reporting flow when it is available for this
repository. If that flow is unavailable, contact the maintainer through the
private contact method listed on the WPMoo organization profile and include:

- affected package version;
- the public entrypoint or rendered page involved;
- a minimal reproduction;
- expected and observed impact;
- any logs, browser versions, or host-framework details that matter.

The maintainer will acknowledge credible reports, scope the affected surface,
and coordinate a fix or mitigation before public disclosure when appropriate.

## Out Of Scope

- Issues caused only by an application's private backend, authentication, or
  deployment configuration.
- Reports that require social engineering or physical access.
- Denial-of-service claims without a practical impact path.
- Vulnerabilities in third-party dependencies that have not been shown to affect
  Moo UI's published package or catalog.

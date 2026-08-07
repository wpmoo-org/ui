#!/usr/bin/env python3
"""Rehearse a `1.0.0-rc.1`-style release without publishing or tagging.

Mirrors `npm-publish.yml`'s real build/pack steps (catalog build, package
boundary check, the tested install-and-smoke sequence) and collects every
RC-required artifact — the npm tarball, the conformance-kit archive, the
certification manifest, and the release attestation — into
`dist/rc-rehearsal/`, printing their versions, source commit, and hashes so
a human can confirm they agree before cutting a real RC. Exits non-zero on
any failure; never runs `npm publish`, `npm version`, or creates a tag.

Usage:
    python scripts/rehearse-rc.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "dist" / "rc-rehearsal"
DEFAULT_TIMEOUT_SECONDS = 600

MANIFEST_SCRIPT = ROOT / "scripts" / "build-certification-manifest.py"
ATTESTATION_SCRIPT = ROOT / "scripts" / "build-certification-attestation.py"


class RehearsalError(RuntimeError):
    pass


def run(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT_SECONDS)
    result = subprocess.run(
        cmd, cwd=ROOT, check=False, capture_output=True, text=True, **kwargs
    )
    if result.returncode != 0:
        raise RehearsalError(
            f"command failed ({' '.join(cmd)}):\n{result.stderr}"
        )
    return result


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_commit() -> str:
    return run(["git", "rev-parse", "HEAD"]).stdout.strip()


def assert_worktree_is_clean() -> None:
    # step_attestation's own generator refuses a dirty worktree too (the
    # evidence inventory it reads is not pinned to the commit it claims
    # otherwise); checking here as well means a dirty tree fails before the
    # full build/pack/install cycle runs, not after it.
    status = run(["git", "status", "--porcelain"]).stdout
    if status.strip():
        raise RehearsalError(
            "the checkout has uncommitted changes; the attestation step "
            "will refuse to run against a dirty worktree, so failing here "
            "instead of after the full rehearsal"
        )


def package_version() -> str:
    return json.loads((ROOT / "package.json").read_text())["version"]


def step_build_catalog() -> None:
    print("== build catalog (python build.py) ==")
    run([sys.executable, "build.py"])
    print("ok")


def step_verify_package_boundary() -> None:
    print("== package boundary check (npm pack --dry-run --json | verify_package_contents.py) ==")
    pack = run(["npm", "pack", "--dry-run", "--json"])
    verify = subprocess.run(
        [sys.executable, "scripts/verify_package_contents.py"],
        cwd=ROOT,
        input=pack.stdout,
        capture_output=True,
        text=True,
    )
    if verify.returncode != 0:
        raise RehearsalError(f"package boundary check failed:\n{verify.stderr}")
    print(verify.stdout.strip())


def step_install_and_smoke() -> None:
    print("== install + smoke sequence (existing clean-consumer tests) ==")
    run(
        [
            sys.executable,
            "-m",
            "unittest",
            (
                "tests.test_package.PackageMetadataTests."
                "test_real_tarball_resolves_from_a_clean_consumer"
            ),
            (
                "tests.test_package.PackageMetadataTests."
                "test_sass_facade_compiles_from_a_clean_consumer"
            ),
            "-v",
        ]
    )
    print("ok")


def step_collect_tarball() -> Path:
    print("== collect a persistent tarball for inspection ==")
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pack = run(
        [
            "npm",
            "pack",
            "--json",
            "--pack-destination",
            str(OUT_DIR),
        ]
    )
    payload = json.loads(pack.stdout)
    tarball = OUT_DIR / payload[0]["filename"]
    if not tarball.is_file():
        raise RehearsalError(f"expected tarball not found: {tarball}")
    print(f"{tarball} ({sha256_of(tarball)})")
    return tarball


def step_conformance_kit() -> Path:
    print("== conformance kit archive (Phase 5) ==")
    contract = json.loads(
        (ROOT / "conformance/contract/conformance-contract.json").read_text()
    )
    kit_version = contract["schemaVersion"]
    kit_out_dir = OUT_DIR / "conformance-kit"
    run(
        [
            sys.executable,
            "scripts/package-conformance-kit.py",
            "--version",
            kit_version,
            "--out-dir",
            str(kit_out_dir),
        ]
    )
    archive = kit_out_dir / f"moo-ui-conformance-kit-{kit_version}.tar.gz"
    if not archive.is_file():
        raise RehearsalError(f"expected conformance-kit archive not found: {archive}")
    print(f"{archive} ({sha256_of(archive)})")
    return archive


def step_manifest(tarball: Path) -> Path:
    print("== certification manifest ==")
    manifest_path = OUT_DIR / "certification-manifest.json"
    run(
        [
            sys.executable,
            str(MANIFEST_SCRIPT),
            "--package",
            str(tarball),
            "--output",
            str(manifest_path),
            "--status",
            "preview",
        ]
    )
    print(f"{manifest_path} ({sha256_of(manifest_path)})")
    return manifest_path


def evidence_uri() -> str:
    """A real CI run URL when running in GitHub Actions, otherwise an
    honest local marker — never a fabricated evidence link."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        server = os.environ["GITHUB_SERVER_URL"]
        repo = os.environ["GITHUB_REPOSITORY"]
        run_id = os.environ["GITHUB_RUN_ID"]
        return f"{server}/{repo}/actions/runs/{run_id}"
    return "urn:rehearsal:local-run"


def step_attestation(tarball: Path, commit: str) -> Path:
    print("== release attestation ==")
    attestation_path = OUT_DIR / "certification-attestation.json"
    # Rehearsal-honest values: no browser was actually driven by this
    # script, so the attestation says so rather than claiming a real
    # cross-browser run. The real automated evidence is ui-ci.yml's own
    # Chromium contract-test run, tracked separately.
    run(
        [
            sys.executable,
            str(ATTESTATION_SCRIPT),
            "--package",
            str(tarball),
            "--output",
            str(attestation_path),
            "--source-commit",
            commit,
            "--browser-name",
            "rehearsal",
            "--browser-version",
            "n/a",
            "--operating-system",
            platform.platform(),
            "--automated-evidence",
            evidence_uri(),
            "--limitation",
            "browsers",
            (
                "The 'rehearsal' browser entry above did not drive any real "
                "browser; it exists only to satisfy the attestation "
                "schema's browsers[] minItems requirement for this local "
                "rehearsal run. Real cross-browser evidence comes from the "
                "nightly certification matrix, not this script."
            ),
        ]
    )
    print(f"{attestation_path} ({sha256_of(attestation_path)})")
    return attestation_path


def main() -> int:
    try:
        commit = source_commit()
        assert_worktree_is_clean()
        step_build_catalog()
        step_verify_package_boundary()
        step_install_and_smoke()
        tarball = step_collect_tarball()
        kit_archive = step_conformance_kit()
        manifest = step_manifest(tarball)
        attestation = step_attestation(tarball, commit)
    except RehearsalError as error:
        print(f"\nREHEARSAL FAILED: {error}", file=sys.stderr)
        return 1

    print("\n== summary ==")
    print(f"package version: {package_version()}")
    print(f"source commit:   {commit}")
    print(f"tarball:         {tarball} ({sha256_of(tarball)})")
    print(f"conformance kit: {kit_archive} ({sha256_of(kit_archive)})")
    print(f"manifest:        {manifest} ({sha256_of(manifest)})")
    print(f"attestation:     {attestation} ({sha256_of(attestation)})")
    print("\nREHEARSAL OK (no publish, no tag)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

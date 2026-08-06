#!/usr/bin/env python3
"""Rehearse a `1.0.0-rc.1`-style release without publishing or tagging.

Mirrors `npm-publish.yml`'s real build/pack steps (catalog build, package
boundary check, the tested install-and-smoke sequence) and collects every
RC-required artifact — the npm tarball, the conformance-kit archive, and
(once Phase 6 Tasks 1/2 land) the certification manifest and release
attestation — into `dist/rc-rehearsal/`, printing their versions, source
commit, and hashes so a human can confirm they agree before cutting a real
RC. Exits non-zero on any failure; never runs `npm publish`, `npm version`,
or creates a tag.

Usage:
    python scripts/rehearse-rc.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "dist" / "rc-rehearsal"

# Stage B (Phase 6 Tasks 1/2) drop their generators here once they land;
# Stage A runs standalone and reports them as pending until then.
MANIFEST_SCRIPT = ROOT / "scripts" / "build-certification-manifest.py"
ATTESTATION_SCRIPT = ROOT / "scripts" / "build-certification-attestation.py"


class RehearsalError(RuntimeError):
    pass


def run(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, **kwargs
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
            "tests.test_package.PackageMetadataTests."
            "test_real_tarball_resolves_from_a_clean_consumer",
            "tests.test_package.PackageMetadataTests."
            "test_sass_facade_compiles_from_a_clean_consumer",
            "-v",
        ]
    )
    print("ok")


def step_collect_tarball() -> Path:
    print("== collect a persistent tarball for inspection ==")
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


def step_manifest_and_attestation() -> list:
    print("== certification manifest + attestation (Phase 6 Tasks 1/2) ==")
    collected = []
    for label, script in (
        ("manifest", MANIFEST_SCRIPT),
        ("attestation", ATTESTATION_SCRIPT),
    ):
        if not script.is_file():
            print(f"{label}: pending — {script.name} does not exist yet")
            continue
        print(f"{label}: {script.name} exists, but Stage B wiring is not implemented yet")
        collected.append(script)
    return collected


def main() -> int:
    try:
        step_build_catalog()
        step_verify_package_boundary()
        step_install_and_smoke()
        tarball = step_collect_tarball()
        kit_archive = step_conformance_kit()
        pending = step_manifest_and_attestation()
    except RehearsalError as error:
        print(f"\nREHEARSAL FAILED: {error}", file=sys.stderr)
        return 1

    print("\n== summary ==")
    print(f"package version: {package_version()}")
    print(f"source commit:   {source_commit()}")
    print(f"tarball:         {tarball} ({sha256_of(tarball)})")
    print(f"conformance kit: {kit_archive} ({sha256_of(kit_archive)})")
    if pending:
        print(
            "Stage B (manifest/attestation) not wired in yet — "
            f"{len(pending)} generator script(s) present but not integrated."
        )
    else:
        print(
            "Stage B (manifest/attestation) generators not found — "
            "waiting on Phase 6 Tasks 1/2."
        )
    print("\nREHEARSAL OK (no publish, no tag)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

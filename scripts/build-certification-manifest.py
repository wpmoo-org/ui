#!/usr/bin/env python3
"""Generate the Core-only certification manifest for a Moo UI release.

Produces a document conforming to ``src/certification/manifest.schema.json``
from the current evidence inventory plus the built npm tarball itself:
the Core version and Bootstrap facts are read from inside the tarball (the
same ``certification.json`` that ships in it), and every component listed
must carry real, on-disk evidence — a missing evidence file fails loudly
instead of producing a manifest that silently under-reports.

The generator never upgrades claims on its own: ``--status preview`` (the
default) emits the rehearsal manifest; ``--status certified`` additionally
requires ``--source-commit`` and ``--attestation`` and refuses to run
unless the shipped certification data already carries a verified Bootstrap
range.

Usage:
    python scripts/build-certification-manifest.py \
        --package dist/wpmoo-ui-0.9.0.tgz --output dist/certification-manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA_VERSION = "1.0"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SUPPORT_POLICY_URL = "https://github.com/wpmoo-org/ui/blob/main/SUPPORT.md"
PREVIEW_BROWSER_POLICY = (
    "Certification is in progress; see SUPPORT.md for the intended browser "
    "policy."
)
CERTIFIED_BROWSER_POLICY = (
    "Modern browsers per SUPPORT.md (current and previous stable Chrome, "
    "Edge, Firefox, macOS Safari, and iOS Safari majors, plus current "
    "stable Android Chrome); the attestation records the exact browser "
    "and operating-system versions actually tested."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Core-only certification manifest."
    )
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=ROOT / "src/certification/evidence-inventory.json",
        help="Evidence inventory to certify from.",
    )
    parser.add_argument(
        "--status",
        choices=("preview", "certified"),
        default="preview",
        help="Preview is the rehearsal default; certified requires the "
        "release attestation inputs below.",
    )
    parser.add_argument("--source-commit")
    parser.add_argument(
        "--attestation",
        help="Public URI of the release attestation (certified only). This "
        "is embedded as metadata; --attestation-file is what gets validated.",
    )
    parser.add_argument(
        "--attestation-file",
        type=Path,
        help="Local path to the release attestation JSON (certified only). "
        "Validated against attestation.schema.json and cross-checked "
        "against this manifest's own coreVersion, sourceCommit, and "
        "package hash before certified status is emitted.",
    )
    parser.add_argument(
        "--expected-package-sha256",
        help="When given, the tarball's hash must match exactly.",
    )
    return parser.parse_args()


def load_attestation_schema() -> dict:
    return json.loads(
        (ROOT / "src/certification/attestation.schema.json").read_text(
            encoding="utf-8"
        )
    )


def certified_attestation(
    attestation_file: Path,
    *,
    source_commit: str,
    core_version: str,
    package_sha256: str,
) -> dict:
    """Load and validate the attestation backing a certified manifest.

    A certified manifest's --attestation is only a public URI pointer; on
    its own that proves nothing. This loads the actual attestation document,
    validates it against its schema, and refuses certified status unless
    its sourceCommit, coreVersion, package hash, and result all agree with
    what this manifest run has independently established.
    """
    if not attestation_file.is_file():
        raise ValueError(
            f"--attestation-file does not exist: {attestation_file}"
        )
    attestation = json.loads(attestation_file.read_text(encoding="utf-8"))

    validator = Draft202012Validator(load_attestation_schema())
    errors = sorted(validator.iter_errors(attestation), key=str)
    if errors:
        raise ValueError(
            "attestation file does not conform to attestation.schema.json: "
            + "; ".join(error.message for error in errors)
        )

    if attestation.get("result") != "passed":
        raise ValueError(
            "attestation does not record a passing result; refusing to "
            "claim certified status"
        )
    if attestation.get("sourceCommit") != source_commit:
        raise ValueError(
            "attestation sourceCommit does not match --source-commit: "
            f"{attestation.get('sourceCommit')!r} vs {source_commit!r}"
        )
    if attestation.get("coreVersion") != core_version:
        raise ValueError(
            "attestation coreVersion does not match the package tarball: "
            f"{attestation.get('coreVersion')!r} vs {core_version!r}"
        )
    attested_package_sha256 = (attestation.get("package") or {}).get("sha256")
    if attested_package_sha256 != package_sha256:
        raise ValueError(
            "attestation package hash does not match the package tarball: "
            f"{attested_package_sha256!r} vs {package_sha256!r}"
        )
    return attestation


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tarball_json(archive: tarfile.TarFile, member_name: str) -> dict:
    member = archive.getmember(member_name)
    if not member.isfile():
        raise ValueError(f"Tarball member is not a file: {member_name}")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"Tarball member cannot be read: {member_name}")
    return json.loads(stream.read().decode("utf-8"))


def load_inventory(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"evidence inventory does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def certified_components(inventory: dict) -> list[dict]:
    """Every inventory component, with its evidence proven on disk.

    A component whose profile is undefined, whose tier is out of range,
    or whose evidence files are missing raises here — the manifest must
    never list a component whose evidence cannot be produced.
    """
    profiles = inventory.get("profiles") or {}
    components = []
    for component in inventory.get("components", []):
        slug = component.get("slug")
        profile = profiles.get(component.get("profile"))
        if profile is None:
            raise ValueError(
                f"component {slug!r} references undefined profile "
                f"{component.get('profile')!r}"
            )
        tier = profile.get("tier")
        if not isinstance(tier, int) or not 0 <= tier <= 3:
            raise ValueError(f"component {slug!r} has an invalid tier: {tier!r}")
        evidence_paths = component.get("evidence")
        if not isinstance(evidence_paths, list) or not evidence_paths:
            raise ValueError(f"component {slug!r} has no evidence")
        for evidence_path in evidence_paths:
            if not isinstance(evidence_path, str) or not evidence_path:
                raise ValueError(
                    f"component {slug!r} has an invalid evidence path: "
                    f"{evidence_path!r}"
                )
            resolved = (ROOT / evidence_path).resolve()
            if ROOT.resolve() not in resolved.parents:
                raise ValueError(
                    f"component {slug!r} evidence escapes the repository: "
                    f"{evidence_path}"
                )
            if not resolved.is_file():
                raise ValueError(
                    f"component {slug!r} is missing evidence: {evidence_path}"
                )
        components.append({"slug": slug, "tier": tier, "status": "certified"})
    if not components:
        raise ValueError("evidence inventory lists no components")
    return components


def build_manifest(args: argparse.Namespace) -> dict:
    if not args.package.is_file():
        raise ValueError(f"package tarball does not exist: {args.package}")

    package_sha256 = sha256_file(args.package)
    if args.expected_package_sha256:
        if package_sha256 != args.expected_package_sha256.lower():
            raise ValueError(
                "package hash mismatch: expected "
                f"{args.expected_package_sha256}, got {package_sha256}"
            )

    with tarfile.open(args.package, mode="r:gz") as archive:
        package = read_tarball_json(archive, "package/package.json")
        certification = read_tarball_json(archive, "package/certification.json")

    if package.get("name") != "@wpmoo/ui":
        raise ValueError("Tarball is not the canonical @wpmoo/ui package")
    if package.get("version") != certification.get("coreVersion"):
        raise ValueError("Package and certification Core versions do not match")

    bootstrap = certification.get("bootstrap") or {}
    target_range = (package.get("peerDependencies") or {}).get("bootstrap")
    if target_range != bootstrap.get("targetRange"):
        raise ValueError(
            "peerDependencies bootstrap range does not match the shipped "
            f"certification: {target_range!r} vs {bootstrap.get('targetRange')!r}"
        )

    components = certified_components(load_inventory(args.inventory))

    manifest = {
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "status": args.status,
        "coreVersion": package["version"],
        "bootstrap": {
            "canonicalVersion": bootstrap["canonicalVersion"],
            "targetRange": bootstrap["targetRange"],
            "verifiedRange": bootstrap.get("verifiedRange"),
            "testedVersions": bootstrap.get("testedVersions", []),
        },
        "browserPolicy": {
            "policy": PREVIEW_BROWSER_POLICY,
            "exactEvidenceInAttestation": False,
        },
        "certifiedComponents": components,
        "publicEntrypoints": certification["publicEntrypoints"],
        "supportPolicy": SUPPORT_POLICY_URL,
    }

    if args.status == "certified":
        if not args.source_commit or not COMMIT_PATTERN.fullmatch(args.source_commit):
            raise ValueError(
                "--source-commit must be a 40-character lowercase Git commit "
                "for a certified manifest"
            )
        if not args.attestation:
            raise ValueError("--attestation URI is required for a certified manifest")
        if not args.attestation_file:
            raise ValueError(
                "--attestation-file is required for a certified manifest; "
                "--attestation alone is an unvalidated pointer"
            )
        certified_attestation(
            args.attestation_file,
            source_commit=args.source_commit,
            core_version=package["version"],
            package_sha256=package_sha256,
        )
        if not bootstrap.get("verifiedRange"):
            raise ValueError(
                "shipped certification carries no verified Bootstrap range; "
                "refusing to claim certified status"
            )
        manifest["sourceCommit"] = args.source_commit
        manifest["attestation"] = args.attestation
        manifest["browserPolicy"] = {
            "policy": CERTIFIED_BROWSER_POLICY,
            "exactEvidenceInAttestation": True,
        }

    return manifest


def main() -> None:
    args = parse_args()
    if args.package.resolve() == args.output.resolve():
        raise ValueError(
            "--output must not name the package tarball; refusing to "
            "overwrite the release artifact"
        )
    manifest = build_manifest(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{sha256_file(args.output)}  {args.output}")


if __name__ == "__main__":
    main()

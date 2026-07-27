#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT_EVIDENCE = ROOT / "src/certification/pilot-evidence.json"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Moo UI Core preview certification attestation."
    )
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--browser-name", required=True)
    parser.add_argument("--browser-version", required=True)
    parser.add_argument("--operating-system", required=True)
    parser.add_argument("--automated-evidence", required=True)
    parser.add_argument(
        "--created-at",
        help="ISO-8601 timestamp; defaults to the current UTC time.",
    )
    return parser.parse_args()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_tarball_json(archive: tarfile.TarFile, member_name: str) -> tuple[dict, bytes]:
    member = archive.getmember(member_name)
    if not member.isfile():
        raise ValueError(f"Tarball member is not a file: {member_name}")
    stream = archive.extractfile(member)
    if stream is None:
        raise ValueError(f"Tarball member cannot be read: {member_name}")
    content = stream.read()
    return json.loads(content.decode("utf-8")), content


def normalize_created_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--created-at must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_attestation(args: argparse.Namespace) -> dict:
    if not args.package.is_file():
        raise ValueError(f"Package tarball does not exist: {args.package}")
    if not COMMIT_PATTERN.fullmatch(args.source_commit):
        raise ValueError("--source-commit must be a 40-character lowercase Git commit")

    with tarfile.open(args.package, mode="r:gz") as archive:
        package, _ = read_tarball_json(archive, "package/package.json")
        manifest, manifest_content = read_tarball_json(
            archive,
            "package/certification.json",
        )

    if package["name"] != "@wpmoo/ui":
        raise ValueError("Tarball is not the canonical @wpmoo/ui package")
    if package["version"] != manifest["coreVersion"]:
        raise ValueError("Package and certification Core versions do not match")
    if manifest["status"] != "preview":
        raise ValueError("Phase 0 generator accepts preview manifests only")

    pilot = json.loads(PILOT_EVIDENCE.read_text(encoding="utf-8"))
    preview_components = [
        component
        for component in pilot["components"]
        if component["status"] == "preview-passed"
    ]
    if len(preview_components) != 5:
        raise ValueError("Phase 0 preview requires all five pilot components")

    limitations = [
        {
            "surface": component["slug"],
            "description": limitation,
        }
        for component in preview_components
        for limitation in component["limitations"]
    ]
    limitations.insert(
        0,
        {
            "surface": "release",
            "description": (
                "This is Phase 0 preview evidence, not a complete release "
                "certification claim."
            ),
        },
    )

    return {
        "schemaVersion": "0.1",
        "status": "preview",
        "scope": "phase-0-pilot",
        "coreVersion": package["version"],
        "sourceCommit": args.source_commit,
        "createdAt": normalize_created_at(args.created_at),
        "result": "passed",
        "package": {
            "name": package["name"],
            "version": package["version"],
            "filename": args.package.name,
            "sha256": sha256_file(args.package),
            "manifestSha256": sha256_bytes(manifest_content),
        },
        "bootstrap": [
            {
                "lane": "canonical",
                "version": manifest["bootstrap"]["canonicalVersion"],
                "result": "passed",
                "evidence": args.automated_evidence,
            }
        ],
        "browsers": [
            {
                "name": args.browser_name,
                "version": args.browser_version,
                "operatingSystem": args.operating_system,
                "mode": "automated",
                "result": "passed",
                "evidence": args.automated_evidence,
            }
        ],
        "components": [
            {
                "slug": component["slug"],
                "tier": component["tier"],
                "result": "passed",
                "checks": component["evidence"]["existing"],
                "evidence": [args.automated_evidence],
            }
            for component in preview_components
        ],
        "automatedRuns": [
            {
                "name": "phase-0-pilot",
                "result": "passed",
                "evidence": args.automated_evidence,
            }
        ],
        "manualReviews": [],
        "realDevices": [],
        "waivers": [],
        "limitations": limitations,
    }


def main() -> None:
    args = parse_args()
    attestation = build_attestation(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(attestation, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

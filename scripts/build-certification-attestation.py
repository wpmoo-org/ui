#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_INVENTORY = ROOT / "src/certification/evidence-inventory.json"
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
# The attestation schema's components[].checks enum. Every category the
# evidence inventory reports as existing must map into this set; one that
# does not is a contract drift we fail on loudly rather than silently drop.
ALLOWED_CHECKS = {
    "contract",
    "markup",
    "theme",
    "rtl",
    "responsive",
    "keyboard",
    "focus",
    "lifecycle",
    "accessibility",
    "visual",
    "real-device",
    "host-conformance",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Core-only Moo UI release certification attestation."
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
    parser.add_argument(
        "--limitation",
        nargs=2,
        metavar=("SURFACE", "DESCRIPTION"),
        action="append",
        default=[],
        help=(
            "Append an extra limitations[] entry (may be repeated). Use this "
            "to disclose, e.g., that --browser-name did not drive a real "
            "browser, rather than letting the browsers[] entry's required "
            "'passed' result imply an evidence claim it cannot back."
        ),
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


def resolve_head_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ValueError(
            "cannot resolve the checkout HEAD; refusing to attest without "
            f"provenance ({completed.stderr.strip()})"
        )
    return completed.stdout.strip()


def assert_worktree_is_clean() -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ValueError(
            "cannot inspect the checkout status; refusing to attest without "
            f"provenance ({completed.stderr.strip()})"
        )
    if completed.stdout.strip():
        raise ValueError(
            "the checkout has uncommitted changes; refusing to attest, "
            "since the evidence inventory is read from the working tree "
            "and could diverge from --source-commit's committed state"
        )


def certified_components() -> list[dict]:
    """Every inventory component, with its evidence proven on disk.

    Derives each component's attested checks from its evidence profile's
    ``existing`` categories. A component whose profile is undefined, whose
    tier is out of range, whose checks fall outside the attestation
    contract, or whose evidence files are missing or escape the repository
    raises here rather than emitting an under-reported claim.
    """
    inventory = json.loads(EVIDENCE_INVENTORY.read_text(encoding="utf-8"))
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
        checks = list(profile.get("existing") or [])
        if not checks:
            raise ValueError(
                f"component {slug!r} has no existing evidence checks"
            )
        for check in checks:
            if check not in ALLOWED_CHECKS:
                raise ValueError(
                    f"component {slug!r} carries a check outside the "
                    f"attestation contract: {check!r}"
                )
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
        components.append(
            {
                "slug": slug,
                "tier": tier,
                "result": "passed",
                "checks": checks,
            }
        )
    if not components:
        raise ValueError("evidence inventory lists no components")
    return components


def build_attestation(args: argparse.Namespace) -> dict:
    if not args.package.is_file():
        raise ValueError(f"Package tarball does not exist: {args.package}")
    if not COMMIT_PATTERN.fullmatch(args.source_commit):
        raise ValueError("--source-commit must be a 40-character lowercase Git commit")

    # The evidence inventory (and the evidence files it references) is read
    # from the working checkout, not from the tarball — it is not shipped in
    # the package. Pin that evidence to the claimed commit: the checkout must
    # actually be at --source-commit, otherwise a caller could attest one
    # tarball with evidence drawn from a different checkout.
    head_commit = resolve_head_commit()
    if head_commit != args.source_commit:
        raise ValueError(
            "the evidence inventory is read from the working checkout, so "
            "--source-commit must match the checkout HEAD: got "
            f"{args.source_commit}, checkout is at {head_commit}"
        )
    assert_worktree_is_clean()

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
        raise ValueError(
            "This rehearsal generator accepts preview manifests only"
        )

    components = certified_components()

    limitations = [
        {
            "surface": "release",
            "description": (
                "Automated Core-only evidence for a release candidate; "
                "real-device and manual accessibility acceptance are "
                "recorded separately before final certification."
            ),
        },
        {
            "surface": "browsers",
            "description": (
                "This attestation records the single automated browser run "
                "supplied by the caller; the full cross-browser matrix is "
                "tracked by the nightly certification workflow."
            ),
        },
    ]
    limitations.extend(
        {"surface": surface, "description": description}
        for surface, description in args.limitation
    )

    return {
        "schemaVersion": "0.1",
        "status": "preview",
        "scope": "core",
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
        "components": components,
        "automatedRuns": [
            {
                "name": "core-certification",
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

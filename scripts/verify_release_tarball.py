#!/usr/bin/env python3
"""Verify the published RC8 package from the bytes in its npm tarball.

The verifier deliberately does not extract the archive.  It validates one
canonical member policy, reads only the required JSON/artifact members, and
checks every manifest digest against the packed bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import sys
import tarfile
from pathlib import Path
from typing import Any


PACKAGE_NAME = "@wpmoo/ui"
PACKAGE_VERSION = "1.0.0-rc.8"
MANIFEST_MEMBER = "package/dist/release-manifest.json"
PACKAGE_JSON_MEMBER = "package/package.json"
MANIFEST_LIMIT = 1 * 1024 * 1024
ARTIFACT_LIMIT = 10 * 1024 * 1024
AGGREGATE_REGULAR_FILE_LIMIT = 32 * 1024 * 1024
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_ARTIFACTS = {
    "./moo.css": "dist/assets/css/moo.css",
    "./moo-ui.css": "dist/assets/css/moo-ui.css",
    "./theme-prepaint.js": "dist/js/theme-prepaint.js",
}


class ReleaseTarballError(ValueError):
    """Raised when a tarball violates the release contract."""


def _canonical_path(name: str, *, context: str) -> str:
    if not isinstance(name, str) or not name:
        raise ReleaseTarballError(f"{context} path must be a non-empty string")
    if "\x00" in name:
        raise ReleaseTarballError(f"{context} path contains NUL: {name!r}")
    if "\\" in name:
        raise ReleaseTarballError(f"{context} path contains a backslash: {name!r}")
    if name.startswith("/") or name.startswith("//"):
        raise ReleaseTarballError(f"{context} path must not be absolute or UNC-like: {name!r}")

    segments = name.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ReleaseTarballError(
            f"{context} path contains an empty, dot, or dot-dot segment: {name!r}"
        )
    normalized = posixpath.normpath(name)
    if normalized != name:
        raise ReleaseTarballError(
            f"{context} path is not canonical: {name!r} (normalizes to {normalized!r})"
        )
    return normalized


def canonical_member_name(member: tarfile.TarInfo) -> str:
    """Validate and return a member's effective canonical POSIX name."""

    if member.pax_headers.get("path") is not None:
        raise ReleaseTarballError(
            f"archive member uses PAX path metadata: {member.name!r}"
        )
    if member.pax_headers.get("linkpath") is not None:
        raise ReleaseTarballError(
            f"archive member uses PAX link metadata: {member.name!r}"
        )

    name = _canonical_path(member.name, context="archive member")
    if name == "package":
        if not member.isdir():
            raise ReleaseTarballError("package root member must be a directory")
        return name
    if not name.startswith("package/"):
        raise ReleaseTarballError(
            f"archive member must be below package/: {member.name!r}"
        )
    return name


def read_archive_members(archive: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    """Apply the canonical member policy without extracting anything."""

    members: dict[str, tarfile.TarInfo] = {}
    normalized_names: dict[str, str] = {}
    aggregate_size = 0
    for member in archive.getmembers():
        name = canonical_member_name(member)
        if name in members:
            raise ReleaseTarballError(f"duplicate archive member: {name}")
        normalized = posixpath.normpath(name)
        previous = normalized_names.get(normalized)
        if previous is not None:
            raise ReleaseTarballError(
                f"duplicate normalized archive member: {previous!r} and {name!r}"
            )
        normalized_names[normalized] = name

        if not member.isdir() and not member.isfile():
            raise ReleaseTarballError(
                f"archive member must be a directory or regular file: {name}"
            )
        if member.isfile():
            if member.size < 0:
                raise ReleaseTarballError(f"archive member has a negative size: {name}")
            aggregate_size += member.size
            if aggregate_size > AGGREGATE_REGULAR_FILE_LIMIT:
                raise ReleaseTarballError(
                    "aggregate regular-file payload exceeds the 32 MiB limit"
                )
        members[name] = member
    return members


def _read_member_bytes(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    *,
    label: str,
    limit: int,
) -> bytes:
    if not member.isfile():
        raise ReleaseTarballError(f"required {label} member is not a regular file")
    if member.size > limit:
        raise ReleaseTarballError(
            f"{label} exceeds the {limit} byte size limit: {member.name}"
        )
    stream = archive.extractfile(member)
    if stream is None:
        raise ReleaseTarballError(f"unable to read {label} member: {member.name}")
    payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ReleaseTarballError(
            f"{label} exceeds the {limit} byte size limit: {member.name}"
        )
    return payload


def _parse_json(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReleaseTarballError(f"{label} is not valid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise ReleaseTarballError(f"{label} must contain a JSON object")
    return value


def _verify_manifest(
    archive: tarfile.TarFile,
    members: dict[str, tarfile.TarInfo],
    package: dict[str, Any],
) -> None:
    manifest_member = members.get(MANIFEST_MEMBER)
    if manifest_member is None:
        raise ReleaseTarballError(f"required member is missing: {MANIFEST_MEMBER}")
    manifest = _parse_json(
        _read_member_bytes(
            archive,
            manifest_member,
            label="release manifest",
            limit=MANIFEST_LIMIT,
        ),
        label="release manifest",
    )

    if manifest.get("schemaVersion") != 1:
        raise ReleaseTarballError("release manifest schemaVersion must be 1")
    manifest_package = manifest.get("package")
    if manifest_package != {
        "name": package.get("name"),
        "version": package.get("version"),
    }:
        raise ReleaseTarballError("release manifest package identity does not match package.json")
    if package.get("name") != PACKAGE_NAME:
        raise ReleaseTarballError(f"package name must be {PACKAGE_NAME!r}")
    if package.get("version") != PACKAGE_VERSION:
        raise ReleaseTarballError(f"package version must be {PACKAGE_VERSION!r}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ReleaseTarballError("release manifest artifacts must be an array")
    if len(artifacts) != len(EXPECTED_ARTIFACTS):
        raise ReleaseTarballError("release manifest must declare exactly the public artifacts")

    seen_exports: set[str] = set()
    seen_paths: set[str] = set()
    for index, entry in enumerate(artifacts):
        if not isinstance(entry, dict):
            raise ReleaseTarballError(f"release manifest artifact {index} must be an object")
        export = entry.get("export")
        path = entry.get("path")
        digest = entry.get("sha256")
        if not isinstance(export, str) or export not in EXPECTED_ARTIFACTS:
            raise ReleaseTarballError(f"release manifest has an unexpected export: {export!r}")
        if export in seen_exports:
            raise ReleaseTarballError(f"duplicate release manifest export: {export!r}")
        if not isinstance(path, str):
            raise ReleaseTarballError(f"release manifest artifact path must be a string: {path!r}")
        canonical_path = _canonical_path(path, context="release manifest artifact")
        if canonical_path != path or path in seen_paths:
            raise ReleaseTarballError(f"duplicate or non-canonical release manifest path: {path!r}")
        if path != EXPECTED_ARTIFACTS[export]:
            raise ReleaseTarballError(
                f"release manifest export {export!r} points at unexpected path: {path!r}"
            )
        if not path.startswith("dist/"):
            raise ReleaseTarballError(f"release manifest artifact must be below dist/: {path!r}")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise ReleaseTarballError(f"release manifest sha256 is not lowercase hex: {digest!r}")

        member_name = f"package/{path}"
        member = members.get(member_name)
        if member is None:
            raise ReleaseTarballError(f"release artifact member is missing: {member_name}")
        payload = _read_member_bytes(
            archive,
            member,
            label="release artifact",
            limit=ARTIFACT_LIMIT,
        )
        actual = hashlib.sha256(payload).hexdigest()
        if actual != digest:
            raise ReleaseTarballError(
                f"release artifact sha256 mismatch for {path}: expected {digest}, got {actual}"
            )
        seen_exports.add(export)
        seen_paths.add(path)

    if seen_exports != set(EXPECTED_ARTIFACTS):
        raise ReleaseTarballError("release manifest artifact exports are incomplete")


def verify_tarball(tarball: Path) -> None:
    if not tarball.is_file():
        raise ReleaseTarballError(f"tarball does not exist: {tarball}")
    try:
        with tarfile.open(tarball, mode="r:gz") as archive:
            members = read_archive_members(archive)
            package_member = members.get(PACKAGE_JSON_MEMBER)
            if package_member is None:
                raise ReleaseTarballError(f"required member is missing: {PACKAGE_JSON_MEMBER}")
            package = _parse_json(
                _read_member_bytes(
                    archive,
                    package_member,
                    label="package.json",
                    limit=MANIFEST_LIMIT,
                ),
                label="package.json",
            )
            _verify_manifest(archive, members, package)
    except (OSError, tarfile.TarError) as error:
        raise ReleaseTarballError(f"unable to read release tarball: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a Moo UI RC8 npm tarball.")
    parser.add_argument("--tarball", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        verify_tarball(args.tarball)
    except (ReleaseTarballError, json.JSONDecodeError) as error:
        print(f"Release tarball verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Release tarball verified: {args.tarball}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

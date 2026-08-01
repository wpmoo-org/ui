#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from typing import Any


APPROVED_TARBALL_FILES = {
    "ASSET_LICENSE.md",
    "LICENSE",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "certification.json",
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
    "dist/js/context-menu.js",
    "dist/js/data-table.js",
    "package.json",
}


def packed_file_paths(payload: Any) -> set[str]:
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("npm pack must return one package manifest")

    files = payload[0].get("files") if isinstance(payload[0], dict) else None
    if not isinstance(files, list):
        raise ValueError("npm pack manifest must contain a files list")

    paths = [entry.get("path") for entry in files if isinstance(entry, dict)]
    if len(paths) != len(files) or not all(isinstance(path, str) for path in paths):
        raise ValueError("npm pack manifest files must have string paths")
    if len(paths) != len(set(paths)):
        raise ValueError("npm pack manifest must not contain duplicate paths")

    return set(paths)


def validate_package_manifest(payload: Any) -> None:
    packed_files = packed_file_paths(payload)
    if packed_files == APPROVED_TARBALL_FILES:
        return

    missing = sorted(APPROVED_TARBALL_FILES - packed_files)
    unexpected = sorted(packed_files - APPROVED_TARBALL_FILES)
    details = []
    if missing:
        details.append(f"missing: {', '.join(missing)}")
    if unexpected:
        details.append(f"unexpected: {', '.join(unexpected)}")
    raise ValueError("npm pack contents do not match the package boundary; " + "; ".join(details))


def main() -> int:
    try:
        validate_package_manifest(json.load(sys.stdin))
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Package manifest validation failed: {error}", file=sys.stderr)
        return 1

    print("Package manifest matches the approved package boundary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

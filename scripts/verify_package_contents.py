#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


APPROVED_TARBALL_FILES = {
    "ASSET_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
    "LICENSE",
    "README.md",
    "certification.json",
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
    "dist/js/context-menu.js",
    "dist/js/datatable.js",
    "dist/js/slider.js",
    "dist/js/chart.js",
    "dist/js/chart.min.js",
    "dist/js/datepicker.js",
    "dist/js/datepicker.min.js",
    "scss/_config.scss",
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


def npm_env() -> dict[str, str]:
    env = os.environ.copy()
    cache = env.get("npm_config_cache")
    if not cache or not npm_cache_is_writable(Path(cache)):
        env["npm_config_cache"] = os.path.join(
            tempfile.gettempdir(),
            "wpmoo-npm-cache",
        )
    return env


def npm_cache_is_writable(cache: Path) -> bool:
    try:
        probe_dir = cache / "_cacache" / "tmp"
        probe_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=probe_dir):
            pass
    except OSError:
        return False
    return True


def load_manifest_payload() -> Any:
    stdin_payload = "" if sys.stdin.isatty() else sys.stdin.read()
    if stdin_payload.strip():
        return json.loads(stdin_payload)

    result = subprocess.run(
        ["npm", "pack", "--dry-run", "--json"],
        check=False,
        capture_output=True,
        text=True,
        env=npm_env(),
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "npm pack --dry-run --json failed")
    return json.loads(result.stdout)


def main() -> int:
    try:
        validate_package_manifest(load_manifest_payload())
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Package manifest validation failed: {error}", file=sys.stderr)
        return 1

    print("Package manifest matches the approved package boundary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

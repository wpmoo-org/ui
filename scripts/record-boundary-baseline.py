#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIST = ROOT / "dist"
SITE_DIST = ROOT / "site-dist"
CORE_OUTPUTS = {
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_files(root: Path, base: Path) -> list[str]:
    return sorted(
        path.relative_to(base).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )


def record_boundary_baseline(root: Path = ROOT) -> dict:
    root = Path(root).resolve()
    package_dist = root / "dist"
    site_dist = root / "site-dist"

    run([sys.executable, "build.py"], root)
    pack = json.loads(
        run(["npm", "pack", "--dry-run", "--json"], root).stdout
    )[0]
    package = read_json(root / "package.json")
    package_dist_files = relative_files(package_dist, root)
    site_dist_files = relative_files(site_dist, root)
    package_hashes = {
        relative: sha256(root / relative)
        for relative in package_dist_files
    }
    site_hashes = {
        relative: sha256(root / relative)
        for relative in site_dist_files
    }
    missing_core_outputs = sorted(CORE_OUTPUTS - set(package_hashes))
    if missing_core_outputs:
        raise FileNotFoundError(
            "Build did not produce Core outputs: "
            + ", ".join(missing_core_outputs)
        )

    return {
        "package": {
            "name": package["name"],
            "version": package["version"],
            "files": sorted(package["files"]),
            "exports": package["exports"],
            "sideEffects": package["sideEffects"],
            "peerDependencies": package["peerDependencies"],
        },
        "npmPackFiles": sorted(entry["path"] for entry in pack["files"]),
        "distFiles": package_dist_files,
        "siteDistFiles": site_dist_files,
        "coreOutputs": {
            relative: package_hashes[relative]
            for relative in sorted(CORE_OUTPUTS)
        },
        "siteOutputs": site_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write tests/fixtures/boundary-baseline.json.",
    )
    args = parser.parse_args()
    payload = record_boundary_baseline(ROOT)
    output = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.write:
        target = ROOT / "tests/fixtures/boundary-baseline.json"
        target.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()

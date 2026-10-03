"""Prepare the npm release tarball without rewriting checkout sources."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.style_comments import (
    css_comments,
    is_license_comment,
    strip_scss_line_comments,
)
from scripts.verify_package_contents import (
    npm_env,
    validate_package_manifest,
    validate_release_tarball,
)


def pack_release(destination: Path, *, root: Path = ROOT) -> list:
    root = root.resolve()
    destination = destination.resolve()
    inventory = subprocess.run(
        ["npm", "pack", "--dry-run", "--json", "--ignore-scripts"],
        cwd=root, env=npm_env(), check=True, capture_output=True, text=True,
    )
    payload = json.loads(inventory.stdout)
    validate_package_manifest(payload)
    with tempfile.TemporaryDirectory(prefix="moo-release-") as temporary:
        stage = Path(temporary)
        for entry in payload[0]["files"]:
            relative = entry["path"]
            source = root / relative
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if source.suffix == ".scss":
                target.write_text(
                    strip_scss_line_comments(source.read_text(encoding="utf-8")),
                    encoding="utf-8",
                )
            elif relative.endswith(".min.css"):
                if any(
                    not is_license_comment(token.value)
                    for token in css_comments(source.read_text(encoding="utf-8"))
                ):
                    raise ValueError(f"Non-license comment in {relative}; rebuild before packaging")
        destination.mkdir(parents=True, exist_ok=True)
        packed = subprocess.run(
            ["npm", "pack", "--json", "--ignore-scripts", "--pack-destination", str(destination)],
            cwd=stage, env=npm_env(), check=True, capture_output=True, text=True,
        )
        result = json.loads(packed.stdout)
        validate_package_manifest(result)
        validate_release_tarball(destination / result[0]["filename"])
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = pack_release(args.pack_destination)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f"Release packaging failed: {detail}", file=sys.stderr)
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

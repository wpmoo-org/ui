from __future__ import annotations

import hashlib
import io
import json
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.package_release import pack_release
from scripts.verify_package_contents import (
    APPROVED_TARBALL_FILES,
    validate_release_tarball,
)
from tests.helpers import npm_env


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, "build.py", "--core"], cwd=ROOT,
            env=npm_env(), check=True, capture_output=True, text=True,
        )

    def test_publish_workflow_dry_run_uses_the_prepared_tarball(self) -> None:
        workflow = (ROOT / ".github/workflows/npm-publish.yml").read_text()
        version = json.loads((ROOT / "package.json").read_text())["version"]
        commands = [
            line.strip().removeprefix("run: ")
            for line in workflow.splitlines()
            if line.strip().startswith((
                "run: python scripts/verify_package_contents.py --package",
                "run: npm publish ",
            ))
        ]
        self.assertEqual(len(commands), 2)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            payload = pack_release(destination)[0]
            tarball = destination / payload["filename"]
            before = hashlib.sha256(tarball.read_bytes()).hexdigest()
            for command in commands:
                command = command.replace(
                    "${{ steps.package.outputs.version }}", version,
                ).replace(
                    "${{ steps.package.outputs.npm_tag }}", "rc",
                ).replace("./dist/rc-rehearsal/", f"{destination}/")
                args = shlex.split(command)
                if args[0] == "python":
                    args[0] = sys.executable
                else:
                    args.extend([
                        "--dry-run", "--json", "--ignore-scripts",
                        "--registry", "http://127.0.0.1:9",
                    ])
                result = subprocess.run(
                    args, cwd=ROOT, env=npm_env(), check=False,
                    capture_output=True, text=True, timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            published = json.loads(result.stdout)
            self.assertEqual(published["version"], version)
            self.assertEqual(published["shasum"], payload["shasum"])
            self.assertEqual(published["integrity"], payload["integrity"])
            self.assertEqual(hashlib.sha256(tarball.read_bytes()).hexdigest(), before)

    def test_release_verification_rejects_comment_and_asset_tampering(self) -> None:
        cases = (
            ("scss/components/_radio_group.scss", b"\n// Private note\n"),
            ("dist/assets/css/moo.min.css", b"/* Private note */"),
            ("dist/assets/css/moo.css", b"\n.changed { color: red; }\n"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            payload = pack_release(destination)[0]
            tarball = destination / payload["filename"]
            for path, addition in cases:
                with self.subTest(path=path):
                    altered = destination / "altered.tgz"
                    with tarfile.open(tarball, "r:gz") as source:
                        with tarfile.open(altered, "w:gz") as output:
                            for member in source.getmembers():
                                content = source.extractfile(member).read()
                                if member.name == f"package/{path}":
                                    content += addition
                                    member.size = len(content)
                                output.addfile(member, io.BytesIO(content))
                    with self.assertRaisesRegex(ValueError, path):
                        validate_release_tarball(altered)

    def test_failed_pack_preserves_source_files_and_creates_no_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            for relative in APPROVED_TARBALL_FILES:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            invalid = root / "dist/assets/css/moo.min.css"
            invalid.write_bytes(invalid.read_bytes() + b"/* Private note */")
            before = {
                relative: (root / relative).read_bytes()
                for relative in APPROVED_TARBALL_FILES
            }
            destination = Path(temporary) / "release"
            with self.assertRaisesRegex(ValueError, "Non-license comment"):
                pack_release(destination, root=root)
            self.assertFalse(destination.exists())
            self.assertEqual(before, {
                relative: (root / relative).read_bytes()
                for relative in APPROVED_TARBALL_FILES
            })


if __name__ == "__main__":
    unittest.main()

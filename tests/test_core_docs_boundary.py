from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

import build


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/boundary-baseline.json"
CORE_OUTPUTS = {
    "dist/assets/css/moo-ui.css",
    "dist/assets/css/moo-ui.min.css",
    "dist/assets/css/moo.css",
    "dist/assets/css/moo.min.css",
    "dist/js/combobox.js",
    "dist/js/sidebar.js",
}


def load_recorder():
    module_path = ROOT / "scripts/record-boundary-baseline.py"
    spec = importlib.util.spec_from_file_location(
        "record_boundary_baseline",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CoreDocsBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        result = subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise AssertionError(result.stderr)

    def test_core_outputs_match_recorded_hashes(self) -> None:
        self.assertEqual(set(self.fixture["coreOutputs"]), CORE_OUTPUTS)
        for relative_path, expected_hash in self.fixture["coreOutputs"].items():
            with self.subTest(relative_path=relative_path):
                output = ROOT / relative_path
                self.assertTrue(output.is_file(), relative_path)
                self.assertEqual(sha256(output), expected_hash)

    def test_npm_pack_files_match_recorded_baseline(self) -> None:
        result = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        packed_files = sorted(entry["path"] for entry in payload[0]["files"])
        self.assertEqual(packed_files, self.fixture["npmPackFiles"])

    def test_package_metadata_matches_recorded_baseline(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        expected = self.fixture["package"]

        self.assertEqual(package["version"], "0.7.0")
        self.assertEqual(sorted(package["files"]), expected["files"])
        self.assertEqual(package["exports"], expected["exports"])
        self.assertEqual(package["sideEffects"], expected["sideEffects"])
        self.assertEqual(
            package["peerDependencies"],
            expected["peerDependencies"],
        )

    def test_site_public_assets_are_site_owned(self) -> None:
        metadata_files = (
            "favicon.svg",
            "favicon.ico",
            "apple-touch-icon.png",
            "icon-192.png",
            "icon-512.png",
            "site.webmanifest",
            "llms.txt",
        )

        for name in metadata_files:
            with self.subTest(name=name):
                self.assertFalse((ROOT / name).exists())
                self.assertTrue((ROOT / "site/public" / name).is_file())

    def test_site_static_assets_are_not_package_owned(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        protected_paths = {
            "site/static",
            "static",
            "site",
            "site-dist",
            "dist/assets/images",
        }

        self.assertFalse((ROOT / "static").exists())
        self.assertTrue((ROOT / "site/static").is_dir())
        self.assertTrue(protected_paths.isdisjoint(package["files"]))

    def test_site_templates_are_under_site_src(self) -> None:
        self.assertFalse((ROOT / "src/pages").exists())
        self.assertTrue((ROOT / "site/src/pages").is_dir())
        self.assertTrue((ROOT / "site/src/layouts").is_dir())
        self.assertTrue((ROOT / "site/src/shell").is_dir())
        self.assertTrue((ROOT / "site/src/blocks").is_dir())

    def test_site_templates_are_in_source_snapshot(self) -> None:
        snapshot_paths = {path for path, _ in build.source_snapshot()}
        template = ROOT / "site/src/pages/index.html.jinja"

        self.assertIn(str(template), snapshot_paths)

    def test_public_asset_prose_uses_site_static_source_path(self) -> None:
        source_paths = (
            ROOT / "README.md",
            ROOT / "ASSET_LICENSE.md",
            ROOT / "THIRD_PARTY_NOTICES.md",
            ROOT / "site/src/pages/license.html.jinja",
        )

        for path in source_paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                source = path.read_text(encoding="utf-8")
                self.assertIn("site/static/images/", source)
                self.assertNotIn(
                    "static/images/",
                    source.replace("site/static/images/", ""),
                )

    def test_recorder_reproduces_stable_baseline_sections(self) -> None:
        recorder = load_recorder()
        payload = recorder.record_boundary_baseline(ROOT)

        for section in ("package", "npmPackFiles", "coreOutputs"):
            with self.subTest(section=section):
                self.assertEqual(payload[section], self.fixture[section])


if __name__ == "__main__":
    unittest.main()

"""Chart's external peer boundary and catalog vendor delivery contracts."""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import npm_env

ROOT = Path(__file__).resolve().parents[1]
VENDOR_FILES = {
    "chart.js/auto/auto.js": "chart.js/auto/auto.js",
    "chart.js/dist/chart.js": "chart.js/dist/chart.js",
    "chart.js/dist/chunks/index.js": "chart.js/dist/chunks/index.js",
    "chart.js/LICENSE.md": "chart.js/LICENSE.md",
    "@kurkle/color/dist/color.esm.js": "@kurkle/color/dist/color.esm.js",
    "@kurkle/color/LICENSE.md": "@kurkle/color/LICENSE.md",
}


class ChartVendorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [sys.executable, "build.py"], cwd=ROOT, capture_output=True,
            text=True, env=npm_env(),
        )
        if result.returncode:
            raise AssertionError(result.stderr)

    def test_chart_adapters_import_external_peer_without_vendor_implementation(self):
        package = json.loads((ROOT / "package.json").read_text())
        self.assertEqual(package["peerDependencies"]["chart.js"], ">=4.6.1 <5")
        self.assertTrue(package["peerDependenciesMeta"]["chart.js"]["optional"])
        for filename in ("chart.js", "chart.min.js"):
            with self.subTest(filename=filename):
                source = (ROOT / "dist/js" / filename).read_text()
                self.assertRegex(source, r'from\s*["\']chart\.js/auto["\']')
                self.assertNotIn("node_modules/chart.js/", source)
                self.assertNotIn("node_modules/@kurkle/color/", source)
                self.assertNotIn("Chart.js v4.", source)
                self.assertNotIn("@kurkle/color v", source)

    def test_catalog_vendors_are_exact_upstream_files_with_their_licenses(self):
        for target, source in VENDOR_FILES.items():
            with self.subTest(target=target):
                self.assertEqual(
                    (ROOT / "site-dist/vendor" / target).read_bytes(),
                    (ROOT / "node_modules" / source).read_bytes(),
                )
        for page in ("index.html", "components/chart/index.html"):
            html = (ROOT / "site-dist" / page).read_text()
            match = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
            self.assertIsNotNone(match)
            imports = json.loads(match.group(1))["imports"]
            for target in imports.values():
                self.assertRegex(target, r"^\.{1,2}/")
            self.assertTrue(imports["chart.js/auto"].endswith("vendor/chart.js/auto/auto.js"))
            self.assertTrue(imports["@kurkle/color"].endswith("vendor/@kurkle/color/dist/color.esm.js"))

    def test_npm_archive_excludes_visual_assets_and_vendor_files(self):
        result = subprocess.run(
            ["npm", "pack", "--dry-run", "--json"], cwd=ROOT,
            capture_output=True, text=True, env=npm_env(),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        files = {entry["path"] for entry in json.loads(result.stdout)[0]["files"]}
        self.assertNotIn("ASSET_LICENSE.md", files)
        self.assertFalse(any(path.startswith(("vendor/", "node_modules/", "site-dist/")) for path in files))

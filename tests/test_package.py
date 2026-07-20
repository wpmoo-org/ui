import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageMetadataTests(unittest.TestCase):
    def _read_package(self, relative_path: str = "package.json") -> dict:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def test_root_package_publishes_canonical_wpmoo_scope(self) -> None:
        package = self._read_package()

        self.assertEqual(package["name"], "@wpmoo/ui")
        self.assertEqual(package["license"], "MIT")
        self.assertFalse(package.get("private", True))
        self.assertEqual(package["repository"]["url"], "git+https://github.com/wpmoo-org/ui.git")
        self.assertEqual(package["scripts"]["build"], ".venv/bin/python build.py")
        self.assertEqual(package["scripts"]["dev"], ".venv/bin/python dev.py")
        self.assertNotIn("workspaces", package)

    def test_root_package_exports_built_css_without_protected_images(self) -> None:
        package = self._read_package()
        files = package["files"]

        self.assertIn("dist/assets/css/moo-ui.css", files)
        self.assertIn("dist/assets/css/moo-core.css", files)
        self.assertIn("dist/assets/js/bootstrap.bundle.min.js", files)
        self.assertNotIn("dist", files)
        self.assertNotIn("static", files)
        self.assertNotIn("dist/assets/images", files)
        self.assertNotIn("static/images", files)
        self.assertEqual(
            package["exports"]["./moo-ui.css"],
            "./dist/assets/css/moo-ui.css",
        )
        self.assertEqual(
            package["exports"]["./moo-core.css"],
            "./dist/assets/css/moo-core.css",
        )

    def test_moo_scope_alias_package_points_to_canonical_package(self) -> None:
        package = self._read_package()
        alias = self._read_package("packages/moo-ui-alias/package.json")

        self.assertEqual(alias["name"], "@moo/ui")
        self.assertEqual(alias["version"], package["version"])
        self.assertFalse(alias.get("private", True))
        self.assertEqual(alias["dependencies"]["@wpmoo/ui"], package["version"])
        self.assertEqual(alias["files"], ["README.md"])

    def test_alias_package_is_not_part_of_root_install(self) -> None:
        self.assertFalse((ROOT / "pnpm-workspace.yaml").exists())


if __name__ == "__main__":
    unittest.main()

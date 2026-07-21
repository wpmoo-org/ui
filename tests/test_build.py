from __future__ import annotations

from tests.helpers import DIST, CatalogTestCase


class BuildTests(CatalogTestCase):
    def test_build_creates_static_entrypoints(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "index.html").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.css").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.min.css").is_file())
        self.assertTrue((DIST / "assets/css/catalog.css").is_file())
        self.assertTrue((DIST / "assets/css/moo.css").is_file())
        self.assertTrue((DIST / "assets/css/moo.min.css").is_file())
        self.assertFalse((DIST / "assets/css/moo-core.css").exists())
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js").is_file()
        )
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js.map").is_file()
        )

    def test_build_uses_one_shared_catalog_shell(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        self.assertEqual(index.count('data-moo-shell="catalog"'), 1)
        self.assertEqual(index.count("<header"), 1)
        self.assertEqual(index.count("<footer"), 0)
        self.assertIn('href="components/button.html"', index)
        self.assertIn('href="components/card.html"', index)
        self.assertIn('id="main-content"', index)
        self.assertIn('href="#main-content"', index)
        self.assertIn('id="main-content" tabindex="-1"', index)

        introduction = self.read_output("introduction.html")
        self.assertEqual(introduction.count("<footer"), 1)

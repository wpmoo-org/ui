from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


class CatalogBuildTests(unittest.TestCase):
    def run_build(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def read_output(self, relative_path: str) -> str:
        return (DIST / relative_path).read_text(encoding="utf-8")

    def test_build_creates_static_entrypoints(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "index.html").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.css").is_file())
        self.assertTrue((DIST / "assets/css/catalog.css").is_file())
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js").is_file()
        )

    def test_build_uses_one_shared_catalog_shell(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        self.assertEqual(index.count('data-moo-shell="catalog"'), 1)
        self.assertEqual(index.count("<header"), 1)
        self.assertEqual(index.count("<footer"), 1)
        self.assertIn('href="components/button.html"', index)
        self.assertIn('id="main-content"', index)

        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            catalog,
            [{"slug": "button", "label": "Button", "status": "ready"}],
        )

    def test_button_examples_share_one_rendered_source(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        button_output = DIST / "components/button.html"
        self.assertTrue(button_output.is_file())

        page = button_output.read_text(encoding="utf-8")
        example_template = (
            ROOT / "src/components/example.html.jinja"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            example_template.count(
                "{% set rendered = content | dedent_html %}"
            ),
            1,
        )
        self.assertEqual(example_template.count("{{ rendered | safe }}"), 1)
        self.assertEqual(example_template.count("{{ rendered | e }}"), 1)
        self.assertGreater(page.count("moo-example__preview"), 0)
        self.assertEqual(
            page.count("moo-example__preview"),
            page.count("moo-example__source"),
        )
        self.assertIn('class="btn btn-primary"', page)
        self.assertIn('<button class="btn', page)
        self.assertIn('<a class="btn', page)
        self.assertIn('<input class="btn', page)
        self.assertIn('aria-disabled="true"', page)
        self.assertIn('aria-label="Pin dashboard"', page)


if __name__ == "__main__":
    unittest.main()

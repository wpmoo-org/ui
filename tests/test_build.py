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
        self.assertIn('href="#main-content"', index)
        self.assertIn('id="main-content" tabindex="-1"', index)

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

    def test_button_page_covers_approved_variants_and_states(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        for class_name in (
            "btn-primary",
            "btn-secondary",
            "btn-outline-secondary",
            "btn-ghost",
            "btn-danger",
            "btn-link",
            "btn-success",
            "btn-warning",
            "btn-info",
            "btn-light",
            "btn-dark",
            "btn-outline-primary",
            "btn-outline-success",
            "btn-outline-danger",
            "btn-sm",
            "btn-lg",
            "btn-icon",
            "w-100",
        ):
            self.assertIn(class_name, page)

        self.assertIn('data-bs-toggle="button"', page)
        self.assertIn('aria-pressed="false"', page)
        self.assertEqual(page.count('data-example="rtl-preview"'), 1)
        self.assertIn('dir="rtl"', page)

        for runtime_name in ("React", "Tailwind", "Vue", "customElements"):
            self.assertNotIn(runtime_name, page)
        for reference_label in (
            "Primary button",
            "Secondary button",
            "Large button",
            "Small button",
            "Toggle button",
            "Active toggle button",
            "New Branch",
            "Continue",
            "Login",
            "Docs",
            "Review",
        ):
            self.assertNotIn(reference_label, page)

    def test_button_supports_compact_text_and_icon_sizes(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        size_example = page.split(
            'data-example="button-sizes"', 1
        )[1].split("</section>", 1)[0]
        self.assertEqual(size_example.count("<button"), 8)
        for class_name in (
            "btn-xs",
            "btn-sm",
            "btn-lg",
            "btn-icon",
            "btn-icon-xs",
            "btn-icon-sm",
            "btn-icon-lg",
        ):
            self.assertIn(class_name, size_example)

        css = self.read_output("assets/css/moo-ui.css")
        for height in ("1.5rem", "1.75rem", "2rem", "2.25rem"):
            self.assertIn(f"--moo-button-height: {height};", css)

    def test_button_api_reference_documents_the_public_contract(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        reference = page.split('class="moo-component-reference"', 1)[1]
        self.assertIn(">API Reference</h2>", reference)
        for contract_text in (
            "btn btn-primary",
            "btn btn-ghost",
            "btn-icon-lg",
            "aria_label",
            "icon_start",
            "extra_class",
            'data-bs-toggle="button"',
            "Loading visuals remain deferred until Spinner",
        ):
            self.assertIn(contract_text, reference)
        self.assertNotIn("moo_ui.button", reference)
        self.assertNotIn("moo.button", reference)

    def test_button_focus_indicator_uses_high_contrast_outline(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn("outline: 2px solid var(--moo-ring);", css)
        self.assertIn("outline-offset: 2px;", css)
        self.assertNotIn("var(--moo-ring) 30%, transparent", css)

    def test_primary_outline_button_uses_theme_tokens(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        self.assertIn(".btn-outline-primary {", css)
        outline_primary = css.split(".btn-outline-primary {")[-1].split("}", 1)[0]
        self.assertIn("--bs-btn-color: var(--moo-foreground);", outline_primary)
        self.assertIn(
            "--bs-btn-border-color: var(--moo-foreground);",
            outline_primary,
        )
        self.assertIn("--bs-btn-hover-color: var(--moo-surface);", outline_primary)


if __name__ == "__main__":
    unittest.main()

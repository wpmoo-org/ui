from __future__ import annotations

from tests.helpers import DIST, ROOT, CatalogTestCase


PAGE = ROOT / "src/pages/index.html.jinja"


class IndexShellTests(CatalogTestCase):
    def test_index_composes_ready_macro_contracts(self) -> None:
        self.assertTrue(PAGE.is_file(), "Index page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        for import_name in (
            "avatar",
            "badge",
            "button",
            "card",
            "dropdown_menu",
            "input",
            "select",
            "separator",
            "typography",
        ):
            self.assertIn(f'from "components/{import_name}.html.jinja"', source)

        self.assertNotIn("API Reference", source)
        self.assertNotIn("style=", source)
        self.assertNotIn("--moo-", source)
        self.assertIn("href=\"components/\" ~ component.slug ~ \".html\"", source)
        self.assertIn("href=\"utils/\" ~ utility.slug ~ \".html\"", source)

    def test_index_shell_builds_admin_style_component_grid(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "index.html").read_text(encoding="utf-8")
        catalog = (ROOT / "src/catalog.json").read_text(encoding="utf-8")

        self.assertIn("<title>Components — Moo UI</title>", page)
        self.assertIn('class="moo-catalog__toolbar"', page)
        self.assertIn('type="search"', page)
        self.assertIn('class="form-select moo-catalog__status-select"', page)
        self.assertIn('class="dropdown moo-catalog__toolbar-menu"', page)
        self.assertIn('id="components"', page)
        self.assertIn('id="utilities"', page)
        self.assertEqual(page.count("moo-catalog__app-card"), catalog.count('"status": "ready"') + 1)
        self.assertIn('href="components/button.html"', page)
        self.assertIn('href="components/separator.html"', page)
        self.assertIn('href="utils/scroll-fade.html"', page)
        self.assertIn('class="badge border text-body-secondary"', page)
        self.assertIn('class="avatar moo-catalog__app-icon"', page)
        self.assertNotIn("API Reference", page)

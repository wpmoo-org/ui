from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/dropdown_menu.html.jinja"
PAGE = ROOT / "src/pages/components/dropdown-menu.html.jinja"


class DropdownMenuTests(CatalogTestCase):
    def render_template(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Dropdown Menu macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def test_dropdown_wraps_bootstrap_trigger_and_menu(self) -> None:
        output = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
            '{% call dropdown("Actions", align="end") %}'
            '{{ dropdown_item("Open", icon="folder-open") }}'
            '{{ dropdown_item("Delete", destructive=true) }}'
            "{% endcall %}"
        )

        self.assertIn('<div class="dropdown">', output)
        self.assertIn(
            '<button class="btn btn-outline-secondary dropdown-toggle" '
            'type="button" data-bs-toggle="dropdown" aria-expanded="false">',
            output,
        )
        self.assertIn('<ul class="dropdown-menu dropdown-menu-end">', output)
        self.assertIn('class="dropdown-item"', output)
        self.assertIn('class="dropdown-item text-danger"', output)
        self.assertIn('data-icon="inline-start"', output)

    def test_dropdown_fails_fast_for_unknown_contracts(self) -> None:
        invalid_templates = (
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown %}'
                '{% call dropdown("Actions", align="middle") %}x{% endcall %}',
                "Unknown dropdown alignment: middle",
            ),
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
                '{{ dropdown_item("   ") }}',
                "Dropdown item label is required",
            ),
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown_header %}'
                '{{ dropdown_header("") }}',
                "Dropdown header label is required",
            ),
        )

        for source, message in invalid_templates:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_template(source)

    def test_dropdown_page_uses_macro_contract(self) -> None:
        self.assertTrue(PAGE.is_file(), "Dropdown Menu catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"dropdown_menu"})
        self.assertIn(
            '{% from "includes/page-header.html.jinja" import render_page_header %}',
            source,
        )
        self.assertIn(
            '{% from "includes/example.html.jinja" import render_example %}',
            source,
        )
        self.assertIn(
            '{% from "includes/documentation-reference.html.jinja" import render_reference %}',
            source,
        )
        self.assertNotRegex(
            source,
            r"<(?:button|form|input|kbd|label|select|textarea|ul|li|a)\b",
        )
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-dropdown", source)
        self.assertNotIn("moo-dropdown", source)

    def test_dropdown_catalog_builds_native_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {
                "slug": "dropdown-menu",
                "label": "Dropdown Menu",
                "status": "ready",
            },
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/dropdown-menu.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 5)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="dropdown"', page)
        self.assertIn('class="dropdown-menu"', page)
        self.assertIn('class="dropdown-item"', page)
        self.assertIn('data-bs-toggle="dropdown"', page)
        self.assertIn('aria-expanded="false"', page)
        self.assertIn('class="dropdown-divider"', page)
        self.assertIn('class="dropdown-header"', page)
        self.assertIn("Bootstrap Dropdown documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-dropdown", page)

    def test_dropdown_styles_bridge_bootstrap_variables_only(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = (DIST / "assets/css/moo-ui.css").read_text(encoding="utf-8")
        self.assertIn("--bs-dropdown-bg: var(--moo-surface);", css)
        self.assertIn("--bs-dropdown-border-color: var(--moo-border);", css)
        self.assertIn("--bs-dropdown-box-shadow: var(--bs-box-shadow);", css)
        self.assertIn("box-shadow: var(--bs-dropdown-box-shadow);", css)
        self.assertNotIn("--moo-dropdown", css)

from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/navigation.html.jinja"
PAGE = ROOT / "src/pages/components/navigation.html.jinja"


class NavigationTests(CatalogTestCase):
    def render_navigation(self, template_source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Navigation macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/navigation.html.jinja" import nav_item, nav_menu %}'
            + template_source
        )
        return " ".join(template.render().split())

    def test_navigation_macro_outputs_native_bootstrap_nav(self) -> None:
        output = self.render_navigation(
            """
            {% call nav_menu("Primary sections", vertical=true) %}
              {{ nav_item("Dashboard", active=true, icon="layout-dashboard") }}
              {{ nav_item("Tasks") }}
              {{ nav_item("Inbox", badge_label="3") }}
              {{ nav_item("Settings", disabled=true) }}
            {% endcall %}
            """
        )

        self.assertIn('<nav aria-label="Primary sections">', output)
        self.assertIn('class="nav nav-pills flex-column gap-1"', output)
        self.assertIn('class="nav-link active"', output)
        self.assertIn('aria-current="page"', output)
        self.assertIn('class="badge text-bg-secondary rounded-pill ms-auto"', output)
        self.assertIn('aria-disabled="true" tabindex="-1"', output)
        self.assertNotIn("--moo-navigation", output)

    def test_navigation_macro_rejects_unknown_options(self) -> None:
        with self.assertRaisesRegex(ValueError, "Navigation aria_label is required"):
            self.render_navigation('{% call nav_menu("") %}{{ nav_item("A") }}{% endcall %}')

        with self.assertRaisesRegex(ValueError, "Unknown navigation style: tabs"):
            self.render_navigation(
                '{% call nav_menu("Tabs", style="tabs") %}{{ nav_item("A") }}{% endcall %}'
            )

        with self.assertRaisesRegex(ValueError, "Navigation item label is required"):
            self.render_navigation('{% call nav_menu("Nav") %}{{ nav_item("") }}{% endcall %}')

    def test_navigation_page_uses_navigation_contract_only(self) -> None:
        self.assertTrue(PAGE.is_file(), "Navigation catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"navigation"})
        self.assertNotRegex(source, r"<(?:button|form|input|kbd|label|select|textarea)\b")
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-navigation", source)

    def test_navigation_catalog_builds_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "navigation", "label": "Navigation", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/navigation.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 5)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="nav nav-pills"', page)
        self.assertIn('class="nav-link active"', page)
        self.assertIn('aria-current="page"', page)
        self.assertIn('class="badge text-bg-primary rounded-pill ms-auto"', page)
        self.assertIn('dir="rtl"', page)
        self.assertIn("Bootstrap Navs and tabs documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-navigation", page)

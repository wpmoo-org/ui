from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/separator.html.jinja"
PAGE = ROOT / "src/pages/components/separator.html.jinja"


class SeparatorTests(CatalogTestCase):
    def render_separator(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Separator macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/separator.html.jinja" import separator %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_separator_renders_native_horizontal_and_vertical_rules(self) -> None:
        self.assertEqual(self.render_separator("separator()"), '<hr aria-hidden="true">')
        self.assertEqual(
            self.render_separator('separator("vertical")'),
            '<div class="vr" aria-hidden="true"></div>',
        )
        self.assertEqual(
            self.render_separator('separator("vertical", decorative=false)'),
            '<div class="vr" role="separator" aria-orientation="vertical"></div>',
        )
        self.assertEqual(
            self.render_separator('separator(extra_class="my-4")'),
            '<hr class="my-4" aria-hidden="true">',
        )

    def test_separator_rejects_unknown_orientation(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown separator orientation: diagonal"):
            self.render_separator('separator("diagonal")')

    def test_separator_page_uses_ready_component_contracts_only(self) -> None:
        self.assertTrue(PAGE.is_file(), "Separator catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"separator"})
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
        self.assertNotRegex(source, r"<(?:a|button|form|hr|input|kbd|label|select|textarea)\b")
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-separator", source)
        self.assertNotIn("moo-separator", source)
        self.assertNotIn("style=", source)

    def test_separator_catalog_builds_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "separator", "label": "Separator", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/separator.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 3)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('<hr class="my-4" aria-hidden="true">', page)
        self.assertIn('<div class="vr" aria-hidden="true"></div>', page)
        self.assertIn('<hr>', page)
        self.assertIn("Bootstrap Vertical rule documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-separator", page)

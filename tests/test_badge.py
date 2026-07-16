from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/badge.html.jinja"
PAGE = ROOT / "src/pages/components/badge.html.jinja"


class BadgeTests(CatalogTestCase):
    def render_badge(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Badge macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/badge.html.jinja" import badge %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_badge_maps_variants_to_bootstrap_utilities(self) -> None:
        self.assertIn('class="badge text-bg-primary"', self.render_badge('badge("Default")'))
        self.assertIn(
            'class="badge text-bg-secondary rounded-pill"',
            self.render_badge('badge("Secondary", variant="secondary", pill=true)'),
        )
        self.assertIn(
            'class="badge text-bg-danger"',
            self.render_badge('badge("Delete", variant="destructive")'),
        )
        self.assertIn(
            'class="badge border text-body-secondary"',
            self.render_badge('badge("Outline", variant="outline")'),
        )

    def test_badge_requires_known_variant_and_visible_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown badge variant: ghost"):
            self.render_badge('badge("Ghost", variant="ghost")')
        with self.assertRaisesRegex(ValueError, "Badge label is required"):
            self.render_badge('badge("   ")')

    def test_badge_can_add_visually_hidden_context(self) -> None:
        output = self.render_badge(
            'badge("12", variant="secondary", visually_hidden="unread messages")'
        )

        self.assertIn("12", output)
        self.assertIn(
            '<span class="visually-hidden">unread messages</span>',
            output,
        )

    def test_badge_page_uses_macro_contract(self) -> None:
        self.assertTrue(PAGE.is_file(), "Badge catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"badge"})
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
        self.assertNotRegex(source, r"<(?:button|form|input|kbd|label|select|textarea)\b")
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-badge", source)
        self.assertNotIn("moo-badge", source)

    def test_badge_catalog_builds_native_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "badge", "label": "Badge", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/badge.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 4)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="badge text-bg-primary"', page)
        self.assertIn('class="badge text-bg-secondary"', page)
        self.assertIn('class="badge text-bg-danger"', page)
        self.assertIn('class="badge border text-body-secondary"', page)
        self.assertIn("rounded-pill", page)
        self.assertIn("visually-hidden", page)
        self.assertIn("Bootstrap Badge documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-badge", page)

from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/typography.html.jinja"
PAGE = ROOT / "src/pages/components/typography.html.jinja"


class TypographyTests(CatalogTestCase):
    def render_typography(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Typography macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/typography.html.jinja" import typography %}'
            f"{{{{ {call} }}}}"
        )
        return template.render().strip()

    def test_typography_macro_renders_only_the_catalog_text_roles(self) -> None:
        expected = {
            'typography("Catalog", variant="page-title", id="catalog")': (
                '<h1 class="fw-semibold" id="catalog">Catalog</h1>'
            ),
            'typography("Supporting copy", variant="page-description")': (
                '<p class="moo-page-description text-body-secondary mb-0">Supporting copy</p>'
            ),
            'typography("Section title", variant="section-title", id="section")': (
                '<h2 class="h3" id="section">Section title</h2>'
            ),
            'typography("Example", variant="example-title", id="example")': (
                '<h2 class="h4" id="example">Example</h2>'
            ),
            'typography("Quiet context", variant="muted")': (
                '<span class="text-body-secondary">Quiet context</span>'
            ),
            'typography("Section", variant="section-label")': (
                '<span class="small fw-semibold">Section</span>'
            ),
            'typography("<button>", variant="inline-code")': (
                '<code>&lt;button&gt;</code>'
            ),
        }

        for call, output in expected.items():
            with self.subTest(call=call):
                self.assertEqual(self.render_typography(call), output)

    def test_typography_rejects_unknown_variants(self) -> None:
        self.assertTrue(COMPONENT.is_file(), "Typography macro is not implemented")
        with self.assertRaisesRegex(
            ValueError,
            "Unknown typography variant: typo",
        ):
            self.render_typography('typography("Text", variant="typo")')

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
            'typography("Catalog", variant="page-title", id="catalog-title")': (
                '<h1 class="display-5 fw-semibold" id="catalog-title">Catalog</h1>'
            ),
            'typography("Supporting copy", variant="page-description")': (
                '<p class="lead text-body-secondary mb-0">Supporting copy</p>'
            ),
            'typography("Section title", variant="section-title", id="section-title")': (
                '<h2 class="h3" id="section-title">Section title</h2>'
            ),
            'typography("Example", variant="example-title", id="example-title")': (
                '<h2 class="h4" id="example-title">Example</h2>'
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

    def test_current_component_pages_use_shared_page_typography(self) -> None:
        paths = [
            ROOT / "src/pages/components/button.html.jinja",
            ROOT / "src/pages/components/button-group.html.jinja",
            ROOT / "src/pages/components/card.html.jinja",
            PAGE,
        ]

        for path in paths:
            with self.subTest(page=path.name):
                self.assertTrue(path.is_file(), f"Missing catalog page: {path.name}")
                source = path.read_text(encoding="utf-8")
                self.assertIn(
                    '{% from "components/typography.html.jinja" import typography %}',
                    source,
                )
                self.assertIn('variant="page-title"', source)
                self.assertIn('variant="page-description"', source)
                self.assertNotIn('<h1 class="display-5 fw-semibold">', source)
                self.assertNotIn(
                    '<p class="lead text-body-secondary mb-0">',
                    source,
                )

    def test_example_macro_uses_its_typography_role(self) -> None:
        example = (
            ROOT / "src/components/example.html.jinja"
        ).read_text(encoding="utf-8")
        typography_import = (
            '{% from "components/typography.html.jinja" import typography %}'
        )

        self.assertIn(typography_import, example)
        self.assertIn('variant="example-title"', example)
        self.assertNotIn('<h2 class="h4"', example)

    def test_typography_catalog_builds_shared_examples_and_source(self) -> None:
        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            {"slug": "typography", "label": "Typography", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = DIST / "components/typography.html"
        self.assertTrue(output.is_file())

        page = output.read_text(encoding="utf-8")
        for example in ("headings", "supporting-text", "inline-code"):
            self.assertIn(f'data-example="{example}"', page)
        for marker in (
            'class="display-5 fw-semibold"',
            'class="h3"',
            'class="h4"',
            'class="lead text-body-secondary mb-0"',
            'class="text-body-secondary"',
            'class="small fw-semibold"',
            "<code>",
        ):
            self.assertIn(marker, page)

        self.assertEqual(
            page.count('<div class="moo-example__preview'),
            page.count('class="moo-example__source"'),
        )
        self.assertEqual(page.count('<div class="moo-example__preview'), 3)
        active_labels = [
            re.sub(r"<[^>]+>", "", label).strip()
            for label in re.findall(
                r'<a\b[^>]*aria-current="page"[^>]*>(.*?)</a>',
                page,
                re.DOTALL,
            )
        ]
        self.assertIn("Typography", active_labels)

        headings = [
            re.sub(r"<[^>]+>", "", heading).strip()
            for heading in re.findall(r"<h1\b[^>]*>(.*?)</h1>", page, re.DOTALL)
        ]
        self.assertEqual(headings, ["Typography"])

    def test_typography_page_does_not_fake_future_components(self) -> None:
        self.assertTrue(PAGE.is_file(), "Typography catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"example", "typography"})
        self.assertNotRegex(
            source,
            r"<(?:button|form|input|kbd|select|textarea)\b",
        )
        self.assertNotRegex(
            source,
            r'class="[^"]*\b(?:avatar|badge|btn|dropdown|form-control|'
            r'form-label|input-group|nav|navbar|offcanvas|vr)(?:-|\b)',
        )

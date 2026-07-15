from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/kbd.html.jinja"
PAGE = ROOT / "src/pages/components/kbd.html.jinja"


class KbdTests(CatalogTestCase):
    def render_kbd(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Kbd macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/kbd.html.jinja" import kbd %}'
            f"{{{{ {call} }}}}"
        )
        return template.render().strip()

    def read_kbd_output(self) -> str:
        output = DIST / "components/kbd.html"
        self.assertTrue(output.is_file(), "Kbd catalog output is not implemented")
        return output.read_text(encoding="utf-8")

    def test_kbd_uses_native_markup_and_autoescapes_text(self) -> None:
        self.assertEqual(self.render_kbd('kbd("K")'), "<kbd>K</kbd>")
        self.assertEqual(
            self.render_kbd('kbd("<script>")'),
            "<kbd>&lt;script&gt;</kbd>",
        )

    def test_kbd_rejects_blank_text(self) -> None:
        self.assertTrue(COMPONENT.is_file(), "Kbd macro is not implemented")
        for call in ('kbd("")', 'kbd("   ")'):
            with self.subTest(call=call):
                with self.assertRaisesRegex(ValueError, "Kbd text is required"):
                    self.render_kbd(call)

    def test_kbd_page_uses_shared_catalog_contracts(self) -> None:
        self.assertTrue(PAGE.is_file(), "Kbd catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(
            imports,
            {"example", "kbd", "typography"},
        )
        self.assertIn('variant="page-title"', source)
        self.assertIn('variant="page-description"', source)
        self.assertIn("{{ render_example(", source)

    def test_kbd_catalog_builds_ready_page_with_generated_source(self) -> None:
        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            {"slug": "kbd", "label": "Kbd", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_kbd_output()
        preview_count = page.count('<div class="moo-example__preview')
        self.assertGreater(preview_count, 0)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn("<kbd>Ctrl</kbd>", page)
        self.assertIn("<kbd>K</kbd>", page)
        self.assertIn('<span class="token tag">kbd</span>', page)

        active_labels = [
            re.sub(r"<[^>]+>", "", label).strip()
            for label in re.findall(
                r'<a\b[^>]*aria-current="page"[^>]*>(.*?)</a>',
                page,
                re.DOTALL,
            )
        ]
        self.assertIn("Kbd", active_labels)

        headings = [
            re.sub(r"<[^>]+>", "", heading).strip()
            for heading in re.findall(r"<h1\b[^>]*>(.*?)</h1>", page, re.DOTALL)
        ]
        self.assertEqual(headings, ["Kbd"])

    def test_key_combination_has_accessible_surrounding_context(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_kbd_output()
        contexts = [
            paragraph
            for paragraph in re.findall(r"<p\b[^>]*>.*?</p>", page, re.DOTALL)
            if paragraph.count("<kbd>") == 2
        ]
        self.assertTrue(contexts, "Expected a two-key combination inside a sentence")
        context = contexts[0]
        self.assertRegex(context, r"<p\b[^>]*>\s*[A-Za-z][^<]*<kbd>")
        self.assertRegex(context, r"</kbd>[^<]*[A-Za-z][^<]*</p>")

    def test_kbd_page_does_not_fake_future_components(self) -> None:
        self.assertTrue(PAGE.is_file(), "Kbd catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertNotRegex(
            source,
            r"<(?:button|form|input|select|textarea)\b",
        )
        self.assertNotRegex(
            source,
            r'class="[^"]*\b(?:avatar|badge|btn|dropdown|form-control|'
            r'form-label|input-group|nav|navbar|offcanvas|vr)(?:-|\b)',
        )

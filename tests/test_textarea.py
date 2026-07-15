from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/textarea.html.jinja"
PAGE = ROOT / "src/pages/components/textarea.html.jinja"


class TextareaTests(CatalogTestCase):
    def render_textarea(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Textarea macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/textarea.html.jinja" import textarea %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_visible_label_is_linked_to_native_textarea(self) -> None:
        output = self.render_textarea(
            'textarea(label="<Message>", id="message", '
            'placeholder="<draft>", value="<hello>", rows=4)'
        )

        self.assertEqual(
            output,
            '<label class="form-label" for="message">&lt;Message&gt;</label> '
            '<textarea class="form-control" id="message" rows="4" '
            'placeholder="&lt;draft&gt;">&lt;hello&gt;</textarea>',
        )

    def test_textarea_requires_exactly_one_accessible_name_source(self) -> None:
        for call in (
            "textarea()",
            'textarea(label="   ", aria_label="")',
            'textarea(label="Message", aria_label="Message", id="message")',
            'textarea(placeholder="Message")',
        ):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    ValueError,
                    "Textarea requires exactly one of label or aria_label",
                ):
                    self.render_textarea(call)

    def test_textarea_validates_label_size_and_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "Visible textarea labels require id"):
            self.render_textarea('textarea(label="Message")')
        with self.assertRaisesRegex(ValueError, "Unknown textarea size: xl"):
            self.render_textarea('textarea(aria_label="Message", size="xl")')
        with self.assertRaisesRegex(ValueError, "Textarea rows must be positive"):
            self.render_textarea('textarea(aria_label="Message", rows=0)')

    def test_textarea_emits_native_states(self) -> None:
        output = self.render_textarea(
            'textarea(aria_label="Message", size="lg", aria_invalid=true, '
            'disabled=true, readonly=true)'
        )

        self.assertIn(" form-control-lg", output)
        self.assertIn(" is-invalid", output)
        self.assertIn(' aria-invalid="true"', output)
        self.assertIn(" disabled", output)
        self.assertIn(" readonly", output)

    def test_textarea_page_uses_shared_catalog_contracts(self) -> None:
        self.assertTrue(PAGE.is_file(), "Textarea catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"button", "textarea"})
        self.assertIn(
            '{% from "includes/page-header.html.jinja" import render_page_header %}',
            source,
        )
        self.assertIn(
            '{% from "includes/example.html.jinja" import render_example %}',
            source,
        )
        self.assertIn("{{ render_page_header(", source)
        self.assertIn("{{ render_example(", source)

    def test_textarea_catalog_builds_ready_page_with_generated_source(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "textarea", "label": "Textarea", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/textarea.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertGreater(preview_count, 0)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="form-control"', page)
        self.assertIn("<textarea", page)
        self.assertIn(" disabled", page)
        self.assertIn('aria-invalid="true"', page)
        self.assertIn('<span class="token tag">textarea</span>', page)
        self.assertIn('class="btn btn-primary w-100"', page)

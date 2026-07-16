from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/input.html.jinja"
PAGE = ROOT / "src/pages/components/input.html.jinja"


class InputTests(CatalogTestCase):
    def render_input(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Input macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/input.html.jinja" import input %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def read_input_output(self) -> str:
        output = DIST / "components/input.html"
        self.assertTrue(
            output.is_file(),
            "Input catalog output is not implemented",
        )
        return output.read_text(encoding="utf-8")

    def test_visible_label_is_linked_to_native_form_control(self) -> None:
        output = self.render_input(
            'input(label="<Name>", id="query", '
            'placeholder="<term>", value="<draft>")'
        )

        self.assertEqual(
            output,
            '<label class="form-label" for="query">&lt;Name&gt;</label> '
            '<input class="form-control" id="query" type="text" '
            'placeholder="&lt;term&gt;" value="&lt;draft&gt;">',
        )

    def test_aria_label_mode_supports_standalone_search_without_id(self) -> None:
        output = self.render_input(
            'input(aria_label="Search catalog", type="search", '
            'placeholder="Filter components")'
        )

        self.assertNotIn("<label", output)
        self.assertIn('class="form-control"', output)
        self.assertIn('type="search"', output)
        self.assertIn('placeholder="Filter components"', output)
        self.assertIn('aria-label="Search catalog"', output)
        self.assertNotIn(" id=", output)

    def test_input_requires_exactly_one_accessible_name_source(self) -> None:
        for call in (
            "input()",
            'input(label="   ", aria_label="")',
            'input(label="Search", aria_label="Search", id="search")',
            'input(placeholder="Search")',
        ):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    ValueError,
                    "Input requires exactly one of label or aria_label",
                ):
                    self.render_input(call)

    def test_visible_label_requires_id(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Visible input labels require id",
        ):
            self.render_input('input(label="Search")')

    def test_input_supports_only_approved_native_types(self) -> None:
        for input_type in ("text", "search", "file"):
            with self.subTest(input_type=input_type):
                output = self.render_input(
                    f'input(aria_label="Query", type="{input_type}")'
                )
                self.assertIn(f'type="{input_type}"', output)

        with self.assertRaisesRegex(
            ValueError,
            "Unknown input type: email",
        ):
            self.render_input('input(aria_label="Email", type="email")')

    def test_input_does_not_expose_bootstrap_size_variants(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "macro 'input' takes no keyword argument 'size'",
        ):
            self.render_input('input(aria_label="Search", size="lg")')

    def test_input_emits_native_disabled_and_readonly_states(self) -> None:
        disabled = self.render_input(
            'input(aria_label="Disabled query", disabled=true)'
        )
        readonly = self.render_input(
            'input(aria_label="Read-only query", readonly=true)'
        )

        self.assertIn(" disabled", disabled)
        self.assertNotIn(" readonly", disabled)
        self.assertIn(" readonly", readonly)
        self.assertNotIn(" disabled", readonly)

    def test_input_emits_validation_and_required_states(self) -> None:
        output = self.render_input(
            'input(label="Key", id="key", aria_invalid=true, required=true)'
        )

        self.assertIn(" is-invalid", output)
        self.assertIn(' aria-invalid="true"', output)
        self.assertIn(" required", output)

    def test_input_page_uses_shared_catalog_contracts(self) -> None:
        self.assertTrue(PAGE.is_file(), "Input catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(
            imports,
            {"input"},
        )
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

    def test_input_catalog_builds_ready_page_with_generated_source(self) -> None:
        catalog = json.loads(
            (ROOT / "src/catalog.json").read_text(encoding="utf-8")
        )
        self.assertIn(
            {"slug": "input", "label": "Input", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_input_output()
        preview_count = page.count('<div class="moo-example__preview')
        self.assertGreater(preview_count, 0)
        self.assertEqual(
            preview_count,
            page.count('class="moo-example__source"'),
        )
        self.assertIn('class="form-label"', page)
        self.assertIn('class="form-control"', page)
        self.assertNotIn("form-control-sm", page)
        self.assertNotIn("form-control-lg", page)
        self.assertIn('type="file"', page)
        self.assertIn('aria-label=', page)
        self.assertIn(" disabled", page)
        self.assertNotIn(" required", page)
        self.assertNotIn('aria-invalid="true"', page)
        for marker in (
            'data-example="api-key"',
            'data-example="basic"',
            'data-example="disabled"',
            'data-example="file"',
        ):
            self.assertIn(marker, page)
        self.assertNotIn('data-example="invalid"', page)
        self.assertNotIn('data-example="required"', page)
        self.assertIn('<span class="token tag">input</span>', page)

        active_labels = [
            re.sub(r"<[^>]+>", "", label).strip()
            for label in re.findall(
                r'<a\b[^>]*aria-current="page"[^>]*>(.*?)</a>',
                page,
                re.DOTALL,
            )
        ]
        self.assertIn("Input", active_labels)

        headings = [
            re.sub(r"<[^>]+>", "", heading).strip()
            for heading in re.findall(r"<h1\b[^>]*>(.*?)</h1>", page, re.DOTALL)
        ]
        self.assertEqual(headings, ["Input"])

    def test_input_page_does_not_fake_future_components(self) -> None:
        self.assertTrue(PAGE.is_file(), "Input catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertNotRegex(
            source,
            r"<(?:button|form|input|kbd|label|select|textarea)\b",
        )
        self.assertNotRegex(
            source,
            r'class="[^"]*\b(?:avatar|badge|btn|dropdown|form-control|'
            r'form-label|input-group|nav|navbar|offcanvas|vr)(?:-|\b)',
        )

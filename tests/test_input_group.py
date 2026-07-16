from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/input_group.html.jinja"
PAGE = ROOT / "src/pages/components/input-group.html.jinja"


class InputGroupTests(CatalogTestCase):
    def render_template(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Input Group macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def test_input_group_wraps_native_bootstrap_markup(self) -> None:
        output = self.render_template(
            '{% from "components/input_group.html.jinja" import '
            "input_group, input_group_text %}"
            '{% call input_group(dir="rtl") %}'
            '{{ input_group_text("@", id="addon") }}'
            '<input class="form-control" aria-label="Username">'
            "{% endcall %}"
        )

        self.assertEqual(
            output,
            '<div class="input-group" dir="rtl"> <span class="input-group-text" '
            'id="addon">@</span><input class="form-control" '
            'aria-label="Username"> </div>',
        )

    def test_input_group_fails_fast_for_unknown_contracts(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "macro 'input_group' takes no keyword argument 'size'",
        ):
            self.render_template(
                '{% from "components/input_group.html.jinja" import input_group %}'
                '{% call input_group(size="lg") %}x{% endcall %}'
            )

        invalid_templates = (
            (
                '{% from "components/input_group.html.jinja" import input_group %}'
                '{% call input_group(dir="sideways") %}x{% endcall %}',
                "Unknown input group direction: sideways",
            ),
            (
                '{% from "components/input_group.html.jinja" import '
                "input_group_text %}"
                '{{ input_group_text("   ") }}',
                "Input group text content is required",
            ),
        )

        for source, message in invalid_templates:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_template(source)

    def test_input_group_page_uses_ready_component_macros_only(self) -> None:
        self.assertTrue(PAGE.is_file(), "Input Group catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(
            imports,
            {"button", "dropdown_menu", "input", "input_group", "kbd", "textarea"},
        )
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
        self.assertIn(
            '{% from "includes/field.html.jinja" import render_field %}',
            source,
        )
        self.assertNotRegex(
            source,
            r"<(?:button|form|input|kbd|label|select|textarea)\b",
        )
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-input-group", source)
        self.assertNotIn("moo-input-group", source)

    def test_input_group_catalog_builds_native_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "input-group", "label": "Input Group", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/input-group.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 11)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="input-group"', page)
        self.assertNotIn("input-group-sm", page)
        self.assertNotIn("input-group-lg", page)
        self.assertIn('class="input-group-text"', page)
        self.assertIn('class="form-control"', page)
        self.assertIn('class="btn btn-outline-secondary"', page)
        self.assertIn('class="dropdown-menu dropdown-menu-end"', page)
        self.assertIn('class="dropdown-item"', page)
        self.assertIn("<textarea", page)
        self.assertIn("⌘ K", page)
        self.assertIn('data-align="block-start"', page)
        self.assertIn('data-align="block-end"', page)
        for marker in (
            'data-example="icon-start"',
            'data-example="icon-end"',
            'data-example="search-results"',
            'data-example="text-addons"',
            'data-example="button-addon"',
            'data-example="kbd"',
            'data-example="dropdown"',
            'data-example="textarea"',
            'data-example="block-start"',
            'data-example="block-end"',
            'data-example="rtl"',
        ):
            self.assertIn(marker, page)
        self.assertIn('dir="rtl"', page)
        self.assertIn("Bootstrap Input group documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-input-group", page)

    def test_input_group_styles_use_one_surface_and_sized_icons(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        source = (ROOT / "scss/components/_input_group.scss").read_text(encoding="utf-8")
        css = self.read_output("assets/css/moo-ui.css")

        self.assertIn("padding-inline: $input-group-addon-padding-y;", source)
        self.assertNotIn("padding-inline: 0.25rem;", source)
        self.assertIn(
            "border: var(--bs-border-width) solid var(--moo-border);",
            css,
        )
        self.assertIn("border-radius: var(--bs-border-radius-lg);", css)
        self.assertIn("height: 2rem;", css)
        self.assertIn("padding-block: 0.25rem;", css)
        self.assertIn(".input-group-text > [data-icon]", css)
        self.assertIn("color: var(--bs-secondary-color);", css)
        self.assertIn('.input-group > [data-align="block-end"]', css)
        self.assertIn("width: 1rem;", css)
        self.assertIn("height: 1rem;", css)
        self.assertIn("border-color: #8b8b8b;", css)
        self.assertIn("box-shadow: 0 0 0 2px rgba(23, 23, 23, 0.25);", css)
        self.assertNotIn("color-mix(in srgb, var(--moo-ring) 50%, transparent)", css)

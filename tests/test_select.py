from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/select.html.jinja"
PAGE = ROOT / "src/pages/components/select.html.jinja"


class SelectTests(CatalogTestCase):
    def render_select(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Select macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/select.html.jinja" import select %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_visible_label_is_linked_to_native_select(self) -> None:
        output = self.render_select(
            'select(label="Workspace", id="workspace", '
            'options=[{"value": "ui", "label": "UI"}], selected="ui")'
        )

        self.assertIn(
            '<label class="form-label" for="workspace">Workspace</label>',
            output,
        )
        self.assertIn(
            '<select class="form-select" id="workspace" data-selected="ui">',
            output,
        )
        self.assertIn('<option value="ui" selected>UI</option>', output)

    def test_select_requires_accessible_name_and_options(self) -> None:
        invalid_calls = (
            ("select()", "Select requires exactly one of label or aria_label"),
            (
                'select(label="Workspace", aria_label="Workspace", id="workspace")',
                "Select requires exactly one of label or aria_label",
            ),
            (
                'select(label="Workspace", options=[{"value": "ui", "label": "UI"}])',
                "Visible select labels require id",
            ),
            (
                'select(aria_label="Workspace")',
                "Select options are required",
            ),
        )

        for call, message in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_select(call)

    def test_select_supports_native_size_state_and_direction_contracts(self) -> None:
        output = self.render_select(
            'select(aria_label="Workspace", '
            'options=[{"value": "ui", "label": "UI", "selected": true}], '
            'size="lg", multiple=true, rows="4", disabled=true, '
            'required=true, dir="rtl")'
        )

        self.assertIn('class="form-select form-select-lg"', output)
        self.assertIn(" multiple", output)
        self.assertIn(' size="4"', output)
        self.assertIn(" disabled", output)
        self.assertIn(" required", output)
        self.assertIn(' dir="rtl"', output)

        with self.assertRaisesRegex(ValueError, "Unknown select size: xl"):
            self.render_select(
                'select(aria_label="Workspace", '
                'options=[{"value": "ui", "label": "UI"}], size="xl")'
            )
        with self.assertRaisesRegex(ValueError, "Unknown select direction: sideways"):
            self.render_select(
                'select(aria_label="Workspace", '
                'options=[{"value": "ui", "label": "UI"}], dir="sideways")'
            )

    def test_select_page_uses_ready_component_contracts_only(self) -> None:
        self.assertTrue(PAGE.is_file(), "Select catalog page is not implemented")
        source = PAGE.read_text(encoding="utf-8")
        imports = set(
            re.findall(
                r'{%\s*from\s+"components/([^"/]+)\.html\.jinja"\s+import',
                source,
            )
        )

        self.assertEqual(imports, {"select"})
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
            r"<(?:button|form|input|kbd|label|select|textarea)\b",
        )
        self.assertNotIn("API Reference", source)
        self.assertNotIn("--moo-select", source)
        self.assertNotIn("moo-select", source)

    def test_select_catalog_builds_native_ready_page(self) -> None:
        catalog = json.loads((ROOT / "src/catalog.json").read_text(encoding="utf-8"))
        self.assertIn(
            {"slug": "select", "label": "Select", "status": "ready"},
            catalog,
        )

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = (DIST / "components/select.html").read_text(encoding="utf-8")
        preview_count = page.count('<div class="moo-example__preview')
        self.assertEqual(preview_count, 6)
        self.assertEqual(preview_count, page.count('class="moo-example__source"'))
        self.assertIn('class="form-select"', page)
        self.assertIn('class="form-select form-select-sm"', page)
        self.assertIn('class="form-select form-select-lg"', page)
        self.assertIn(" multiple", page)
        self.assertIn('size="4"', page)
        self.assertIn(" disabled", page)
        self.assertIn('dir="rtl"', page)
        self.assertIn("Bootstrap Select documentation", page)
        self.assertNotIn("API Reference", page)
        self.assertNotIn("--moo-select", page)

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

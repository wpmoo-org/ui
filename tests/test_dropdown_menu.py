from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/dropdown_menu.html.jinja"
PAGE = ROOT / "src/pages/components/dropdown-menu.html.jinja"


class DropdownMenuTests(CatalogTestCase):
    def render_template(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Dropdown Menu macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def test_dropdown_wraps_bootstrap_trigger_and_menu(self) -> None:
        output = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
            '{% call dropdown("Actions", align="end") %}'
            '{{ dropdown_item("Open", icon="folder-open") }}'
            '{{ dropdown_item("Delete", destructive=true) }}'
            "{% endcall %}"
        )

        self.assertIn('<div class="dropdown">', output)
        self.assertIn(
            '<button class="btn btn-outline-secondary dropdown-toggle" '
            'type="button" data-bs-toggle="dropdown" aria-expanded="false">',
            output,
        )
        self.assertIn('<ul class="dropdown-menu dropdown-menu-end">', output)
        self.assertIn('class="dropdown-item"', output)
        self.assertIn('class="dropdown-item text-danger"', output)
        self.assertIn('data-icon="inline-start"', output)

    def test_dropdown_fails_fast_for_unknown_contracts(self) -> None:
        invalid_templates = (
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown %}'
                '{% call dropdown("Actions", align="middle") %}x{% endcall %}',
                "Unknown dropdown alignment: middle",
            ),
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
                '{{ dropdown_item("   ") }}',
                "Dropdown item label is required",
            ),
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown_header %}'
                '{{ dropdown_header("") }}',
                "Dropdown header label is required",
            ),
        )

        for source, message in invalid_templates:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_template(source)

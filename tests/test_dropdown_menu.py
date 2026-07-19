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
            '{{ dropdown_item("Open", icon="folder-open", shortcut="⌘O") }}'
            '{{ dropdown_item("Delete", destructive=true) }}'
            "{% endcall %}"
        )

        self.assertIn('<div class="dropdown">', output)
        self.assertIn(
            '<button class="btn btn-outline-secondary" '
            'type="button" data-bs-toggle="dropdown" aria-expanded="false">',
            output,
        )
        self.assertIn('<ul class="dropdown-menu dropdown-menu-end">', output)
        self.assertIn('class="dropdown-item"', output)
        self.assertIn('class="dropdown-item text-danger"', output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn('<span class="ms-auto small text-body-secondary">⌘O</span>', output)

    def test_dropdown_caret_is_explicit(self) -> None:
        output = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
            '{% call dropdown("Actions", caret=true) %}'
            '{{ dropdown_item("Open") }}'
            "{% endcall %}"
        )

        self.assertIn("dropdown-toggle", output)

    def test_dropdown_keeps_positional_extra_class_compatibility(self) -> None:
        output = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
            '{% call dropdown("Actions", "outline", "end", "my-menu") %}'
            '{{ dropdown_item("Open") }}'
            "{% endcall %}"
        )

        self.assertIn('<div class="dropdown my-menu">', output)
        self.assertIn('<ul class="dropdown-menu dropdown-menu-end">', output)
        self.assertNotIn("dropdown-toggle", output)

    def test_dropdown_menu_and_items_support_owned_extra_classes(self) -> None:
        output = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown_menu, dropdown_item, dropdown_divider %}'
            '{% call dropdown_menu(extra_class="sidebar-account-menu") %}'
            '{{ dropdown_item("Account", icon="badge-check", extra_class="sidebar-account-menu__item") }}'
            '{{ dropdown_divider(extra_class="sidebar-account-menu__divider") }}'
            "{% endcall %}"
        )

        self.assertIn('<ul class="dropdown-menu sidebar-account-menu">', output)
        self.assertIn(
            'class="dropdown-item sidebar-account-menu__item"',
            output,
        )
        self.assertIn(
            'class="dropdown-divider sidebar-account-menu__divider"',
            output,
        )

    def test_dropdown_item_keeps_positional_state_compatibility(self) -> None:
        output = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
            '{{ dropdown_item("Delete", "", "", false, false, true) }}'
        )

        self.assertIn('class="dropdown-item text-danger"', output)
        self.assertNotIn("ms-auto small", output)

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
            (
                '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
                '{{ dropdown_item("Acme Inc", icon_box=true) }}',
                "Dropdown item icon_box requires an icon",
            ),
        )

        for source, message in invalid_templates:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_template(source)

    def test_dropdown_item_icon_box_wraps_the_icon_only(self) -> None:
        boxed = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
            '{{ dropdown_item("Acme Inc", icon="gallery-vertical-end", icon_box=true, shortcut="⌘1") }}'
        )

        self.assertIn(
            '<span class="dropdown-item__icon-box">', boxed
        )
        self.assertIn('data-icon="inline-start"', boxed)
        self.assertIn('<span class="ms-auto small text-body-secondary">⌘1</span>', boxed)

        plain = self.render_template(
            '{% from "components/dropdown_menu.html.jinja" import dropdown_item %}'
            '{{ dropdown_item("Rename", icon="pencil") }}'
        )

        self.assertNotIn("dropdown-item__icon-box", plain)
        self.assertIn('data-icon="inline-start"', plain)

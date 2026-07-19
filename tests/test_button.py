from __future__ import annotations

import inspect
import re

from markupsafe import Markup, escape

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase, lucide_body


class ButtonTests(CatalogTestCase):
    def render_button(self, call: str) -> str:
        template = create_environment().from_string(
            '{% from "components/button.html.jinja" import button %}'
            f"{{{{ {call} }}}}"
        )
        return template.render()

    def test_button_rejects_unknown_variants(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown button variant: typo"):
            self.render_button('button("Save", variant="typo")')

    def test_button_rejects_unknown_sizes(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown button size: huge"):
            self.render_button('button("Save", size="huge")')

    def test_button_rejects_unknown_elements(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown button element: typo"):
            self.render_button('button("Save", element="typo")')

    def test_button_rejects_unknown_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown button type: typo"):
            self.render_button('button("Save", type="typo")')

    def test_button_dropdown_trigger_uses_bootstrap_plugin_contract(self) -> None:
        output = self.render_button('button("Actions", variant="outline", dropdown=true)')

        self.assertNotIn("dropdown-toggle", output)
        self.assertIn('data-bs-toggle="dropdown"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertNotIn('aria-pressed="false"', output)

        caret_output = self.render_button(
            'button("Actions", variant="outline", dropdown=true, dropdown_caret=true)'
        )
        self.assertIn("dropdown-toggle", caret_output)

        with self.assertRaisesRegex(
            ValueError,
            "Button cannot be both toggle and dropdown",
        ):
            self.render_button('button("Actions", toggle=true, dropdown=true)')

        with self.assertRaisesRegex(
            ValueError,
            "Button dropdown_caret requires dropdown=true",
        ):
            self.render_button('button("Actions", dropdown_caret=true)')

    def test_button_dropdown_offset_keeps_positional_compatibility(self) -> None:
        output = self.render_button(
            'button("Actions", "outline", "default", "button", "button", "", '
            'false, "", "", "", "", false, true, "0,8")'
        )

        self.assertIn('data-bs-offset="0,8"', output)
        self.assertNotIn("dropdown-toggle", output)

    def test_button_plugin_options_require_button_element(self) -> None:
        for call in (
            'button("Actions", element="a", toggle=true)',
            'button("Actions", element="a", dropdown=true)',
            'button("Actions", element="a", dropdown_offset="0,8")',
            'button("Actions", element="a", dropdown_caret=true)',
            'button("Actions", element="a", dropdown=true, dropdown_offset="0,8")',
            'button("Actions", element="a", dropdown=true, dropdown_caret=true)',
        ):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    ValueError,
                    "Button dropdown, toggle, and loading options require element=button",
                ):
                    self.render_button(call)

    def test_button_loading_requires_button_element(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Button dropdown, toggle, and loading options require element=button",
        ):
            self.render_button('button("Save", element="a", loading=true)')

    def test_button_loading_renders_decorative_spinner(self) -> None:
        output = self.render_button('button("Saving...", loading=true, disabled=true)')

        self.assertIn(
            '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>',
            output,
        )
        self.assertNotIn('role="status"', output)

    def test_button_loading_and_icon_start_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Button loading replaces icon_start; do not set both"
        ):
            self.render_button('button("Save", loading=true, icon_start="plus")')

    def test_buttons_without_visible_labels_require_an_accessible_name(self) -> None:
        for call in (
            'button("")',
            'button("", icon_start="plus")',
            'button("", size="icon", icon_start="plus")',
        ):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    ValueError,
                    r"require(?:s)? aria_label",
                ):
                    self.render_button(call)

    def test_button_uses_bundled_lucide_renderer_by_default(self) -> None:
        output = self.render_button(
            'button("Continue", icon_start="plus", icon_end="arrow-right")'
        )

        self.assertIn(lucide_body("plus"), output)
        self.assertIn(lucide_body("arrow-right"), output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn('data-icon="inline-end"', output)

    def test_button_accepts_a_custom_icon_renderer(self) -> None:
        calls: list[tuple[str, str]] = []

        def custom_renderer(name: str, position: str) -> Markup:
            calls.append((name, position))
            return Markup(
                '<i data-name="{}" data-icon="{}"></i>'
            ).format(
                escape(name),
                escape(position),
            )

        custom_name = 'custom"><script>alert(1)</script>'
        self.assertIn(
            "icon_renderer",
            inspect.signature(create_environment).parameters,
        )
        environment = create_environment(icon_renderer=custom_renderer)
        template = environment.from_string(
            '{% from "components/button.html.jinja" import button %}'
            '{{ button("Continue", icon_start=custom_name, '
            'icon_end="custom-end") }}'
        )
        output = template.render(custom_name=custom_name)

        self.assertEqual(
            calls,
            [
                (custom_name, "inline-start"),
                ("custom-end", "inline-end"),
            ],
        )
        self.assertIn(f'data-name="{escape(custom_name)}"', output)
        self.assertIn('data-name="custom-end" data-icon="inline-end"', output)
        self.assertNotIn("<script>", output)
        self.assertNotIn("<svg", output)

    def test_button_examples_do_not_emit_fake_external_links(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/button.html")
        self.assertNotIn("example.com", page)

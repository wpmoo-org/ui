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
                    "Button dropdown, toggle, loading, and collapse_target options require element=button",
                ):
                    self.render_button(call)

    def test_button_loading_requires_button_element(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Button dropdown, toggle, loading, and collapse_target options require element=button",
        ):
            self.render_button('button("Save", element="a", loading=true)')

    def test_button_loading_renders_decorative_spinner(self) -> None:
        output = self.render_button('button("Saving...", loading=true, disabled=true)')

        self.assertIn(lucide_body("loader-circle"), output)
        self.assertIn('data-icon="inline-start"', output)
        self.assertIn('aria-hidden="true"', output)
        self.assertIn('aria-busy="true"', output)
        self.assertNotIn('role="status"', output)

    def test_button_loading_and_icon_start_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Button loading replaces icon_start; do not set both"
        ):
            self.render_button('button("Save", loading=true, icon_start="plus")')

    def test_button_collapse_target_uses_bootstrap_collapse_contract(self) -> None:
        output = self.render_button(
            'button("Toggle", collapse_target="panel-one")'
        )

        self.assertIn('data-bs-toggle="collapse"', output)
        self.assertIn('data-bs-target="#panel-one"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertIn('aria-controls="panel-one"', output)

    def test_button_collapse_open_sets_aria_expanded_true(self) -> None:
        output = self.render_button(
            'button("Toggle", collapse_target="panel-one", collapse_open=true)'
        )

        self.assertIn('aria-expanded="true"', output)

    def test_button_collapse_target_cannot_combine_with_toggle_or_dropdown(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Button collapse_target cannot combine with toggle or dropdown",
        ):
            self.render_button(
                'button("Toggle", collapse_target="panel-one", toggle=true)'
            )
        with self.assertRaisesRegex(
            ValueError,
            "Button collapse_target cannot combine with toggle or dropdown",
        ):
            self.render_button(
                'button("Toggle", collapse_target="panel-one", dropdown=true)'
            )

    def test_button_collapse_open_requires_collapse_target(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Button collapse_open requires collapse_target"
        ):
            self.render_button('button("Toggle", collapse_open=true)')

    def test_button_tooltip_uses_bootstrap_plugin_contract(self) -> None:
        output = self.render_button(
            'button("Save", tooltip="Saves the current draft")'
        )

        self.assertIn('data-bs-toggle="tooltip"', output)
        self.assertIn('data-bs-title="Saves the current draft"', output)
        self.assertIn('data-bs-placement="top"', output)

    def test_button_tooltip_placement_is_configurable(self) -> None:
        output = self.render_button(
            'button("Save", tooltip="Saves the draft", tooltip_placement="bottom")'
        )

        self.assertIn('data-bs-placement="bottom"', output)

    def test_button_tooltip_works_on_anchor_element(self) -> None:
        output = self.render_button(
            'button("Docs", element="a", href="#", tooltip="Open documentation")'
        )

        self.assertIn('data-bs-toggle="tooltip"', output)
        self.assertIn('data-bs-title="Open documentation"', output)

    def test_button_rejects_unknown_tooltip_placement(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Unknown button tooltip placement: huge"
        ):
            self.render_button(
                'button("Save", tooltip="Saves the draft", tooltip_placement="huge")'
            )

    def test_button_tooltip_requires_button_or_anchor_element(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Button tooltip requires element=button or element=a",
        ):
            self.render_button(
                'button("Save", element="input", tooltip="Saves the draft")'
            )

    def test_button_tooltip_html_renders_composed_markup(self) -> None:
        output = self.render_button(
            'button("", variant="outline", size="icon-sm", icon_start="save", '
            'aria_label="Save draft", tooltip="Save draft <kbd>⌘S</kbd>", '
            'tooltip_html=true)'
        )

        self.assertIn('data-bs-html="true"', output)
        # The attribute value is HTML-escaped (Jinja's normal attribute
        # escaping), not injected raw. Browsers decode entities back to the
        # literal markup when JS reads the attribute via getAttribute(), so
        # Bootstrap's own tooltip sanitizer still receives the real <kbd>
        # tag; only the outer HTML attribute stays well-formed no matter
        # what the content contains. See
        # test_button_tooltip_html_content_cannot_break_out_of_the_attribute
        # for the regression this protects against.
        self.assertIn(
            'data-bs-title="Save draft &lt;kbd&gt;⌘S&lt;/kbd&gt;"', output
        )
        self.assertNotIn('data-bs-title="Save draft <kbd>', output)

    def test_button_tooltip_html_content_cannot_break_out_of_the_attribute(
        self,
    ) -> None:
        # Regression test for a real attribute-injection bug: tooltip_html
        # content used to be piped through |safe directly into
        # data-bs-title="...", which only suppresses Jinja's tag escaping,
        # not its quote escaping. A literal " in html=true content used to
        # close the attribute early and let anything after it become a new,
        # live HTML attribute (e.g. onclick="..."), completely bypassing
        # Bootstrap's own content sanitizer, which never even runs.
        output = self.render_button(
            "button(\"X\", tooltip='safe <code>x</code> quote \" onclick=\"bad', "
            "tooltip_html=true)"
        )

        self.assertEqual(output.count("data-bs-title="), 1)
        self.assertNotIn('onclick="bad"', output)
        self.assertIn("&#34;", output)

    def test_button_tooltip_html_requires_tooltip(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Button tooltip_html requires tooltip"
        ):
            self.render_button('button("Save", tooltip_html=true)')

    def test_button_tooltip_cannot_combine_with_dropdown_or_collapse(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Button tooltip cannot combine with toggle, dropdown, or collapse_target",
        ):
            self.render_button(
                'button("Actions", dropdown=true, tooltip="More actions")'
            )

        with self.assertRaisesRegex(
            ValueError,
            "Button tooltip cannot combine with toggle, dropdown, or collapse_target",
        ):
            self.render_button(
                'button("Toggle", collapse_target="panel-one", tooltip="Toggle panel")'
            )

    def test_anchor_button_carries_role_button(self) -> None:
        output = self.render_button('button("Link", element="a", href="#")')
        self.assertIn('role="button"', output)

    def test_disabled_anchor_button_gets_bootstrap_disabled_class(self) -> None:
        output = self.render_button('button("Link", element="a", disabled=true)')
        self.assertIn('class="btn btn-primary disabled"', output)
        self.assertIn('aria-disabled="true"', output)
        self.assertIn('tabindex="-1"', output)
        self.assertNotIn("href=", output)

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

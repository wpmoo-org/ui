from __future__ import annotations

import json
import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase, read_settings


COMPONENT = ROOT / "src/components/input.html.jinja"
PAGE = ROOT / "site/src/pages/components/input.html.jinja"


class InputTests(CatalogTestCase):
    def render_input(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Input macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/input.html.jinja" import input %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def read_input_output(self) -> str:
        output = DIST / "components/input/index.html"
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
        for input_type in ("text", "search", "file", "email", "password"):
            with self.subTest(input_type=input_type):
                output = self.render_input(
                    f'input(aria_label="Query", type="{input_type}")'
                )
                self.assertIn(f'type="{input_type}"', output)

        with self.assertRaisesRegex(
            ValueError,
            "Unknown input type: tel",
        ):
            self.render_input('input(aria_label="Phone", type="tel")')

    def test_password_input_rejects_a_rendered_value(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            'Input does not render a value for type="password"',
        ):
            self.render_input(
                'input(aria_label="Password", type="password", value="hunter2")'
            )

        output = self.render_input(
            'input(aria_label="Password", type="password")'
        )
        self.assertIn('type="password"', output)
        self.assertNotIn(" value=", output)

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

    def test_disabled_form_controls_share_disabled_text_token(self) -> None:
        variables = read_settings()
        tokens_root = (ROOT / "scss/themes/_standalone_root.scss").read_text(
            encoding="utf-8"
        )
        core_theme = (ROOT / "scss/themes/_scoped_core.scss").read_text(
            encoding="utf-8"
        )
        input_scss = (ROOT / "scss/components/_input.scss").read_text(encoding="utf-8")

        self.assertIn("$moo-disabled-foreground: $body-tertiary-color !default;", variables)
        self.assertIn(
            "$moo-disabled-foreground-dark: $body-tertiary-color-dark !default;",
            variables,
        )
        self.assertIn("$input-disabled-color: var(--moo-disabled-foreground) !default;", variables)
        self.assertIn("$form-select-disabled-color: $input-disabled-color !default;", variables)
        self.assertIn("$moo-disabled-control-opacity: 0.5 !default;", variables)
        self.assertIn("--moo-disabled-foreground: #{$moo-disabled-foreground};", tokens_root)
        self.assertIn("--moo-disabled-foreground: #{$moo-disabled-foreground};", core_theme)
        self.assertIn("--moo-disabled-control-opacity: #{$moo-disabled-control-opacity};", tokens_root)
        self.assertIn("--moo-disabled-control-opacity: #{$moo-disabled-control-opacity};", core_theme)
        self.assertIn(".form-control:disabled,", input_scss)
        self.assertIn(".form-select:disabled", input_scss)
        self.assertIn("opacity: var(--moo-disabled-control-opacity);", input_scss)

    def test_text_controls_use_compact_reference_line_height(self) -> None:
        variables = read_settings()

        self.assertIn("$font-size-base: 0.875rem !default;", variables)
        self.assertIn("$input-line-height: 1.4285714286 !default;", variables)

    def test_plain_text_inputs_match_input_group_outer_height(self) -> None:
        input_scss = (ROOT / "scss/components/_input.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            ".form-control:not(textarea):not([type=\"file\"]):not(.form-control-sm, .form-control-lg) {",
            input_scss,
        )
        self.assertIn(
            "min-height: calc(#{$input-height} + #{$input-border-width} * 2);",
            input_scss,
        )

    def test_file_selector_button_fills_file_input_inner_height(self) -> None:
        input_scss = (ROOT / "scss/components/_input.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            '.form-control[type="file"]:not(.form-control-sm, .form-control-lg)::file-selector-button {',
            input_scss,
        )
        self.assertIn(
            "min-height: calc(#{$input-height} - #{$input-border-width} * 2);",
            input_scss,
        )

    def test_invalid_form_controls_share_destructive_ring(self) -> None:
        variables = read_settings()
        focus = (ROOT / "scss/foundations/_focus.scss").read_text(
            encoding="utf-8"
        )
        bootstrap_overrides = (
            ROOT / "scss/settings/_bootstrap_overrides.scss"
        ).read_text(encoding="utf-8")
        tokens_root = (ROOT / "scss/themes/_standalone_root.scss").read_text(
            encoding="utf-8"
        )
        core_theme = (ROOT / "scss/themes/_scoped_core.scss").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "$moo-form-invalid-border-color: $moo-destructive !default;",
            variables,
        )
        self.assertIn(
            "$moo-form-invalid-ring-color: color-mix(in srgb, $moo-destructive 20%, transparent) !default;",
            variables,
        )
        self.assertIn(
            "$moo-form-invalid-border-color-dark: color-mix(in srgb, $moo-destructive-dark 50%, transparent) !default;",
            variables,
        )
        self.assertIn(
            "$moo-form-invalid-ring-color-dark: color-mix(in srgb, $moo-destructive-dark 40%, transparent) !default;",
            variables,
        )
        self.assertIn(
            "--moo-form-invalid-ring-color: #{$moo-form-invalid-ring-color};",
            tokens_root,
        )
        self.assertIn(
            "--moo-form-invalid-ring-color: #{$moo-form-invalid-ring-color-dark};",
            tokens_root,
        )
        self.assertIn(
            "--moo-form-invalid-ring-color: #{$moo-form-invalid-ring-color};",
            core_theme,
        )
        self.assertIn(
            "--moo-form-invalid-ring-color: #{$moo-form-invalid-ring-color-dark};",
            core_theme,
        )
        self.assertIn("--bs-form-invalid-color: var(--moo-destructive);", tokens_root)
        self.assertIn(
            "--#{$prefix}form-invalid-color: var(--moo-destructive);",
            core_theme,
        )
        self.assertIn(
            "--bs-form-invalid-border-color: #{$moo-form-invalid-border-color};",
            tokens_root,
        )
        self.assertIn(
            "--bs-form-invalid-border-color: #{$moo-form-invalid-border-color-dark};",
            tokens_root,
        )
        self.assertIn(
            "--#{$prefix}form-invalid-border-color: #{$moo-form-invalid-border-color};",
            core_theme,
        )
        self.assertIn(
            "--#{$prefix}form-invalid-border-color: #{$moo-form-invalid-border-color-dark};",
            core_theme,
        )
        self.assertIn("$enable-validation-icons: false !default;", bootstrap_overrides)
        self.assertIn(".form-control.is-invalid,", focus)
        self.assertIn(".form-control.is-invalid:focus,", focus)
        self.assertIn(".was-validated .form-control:invalid,", focus)
        self.assertIn(".was-validated .form-control:invalid:focus,", focus)
        self.assertIn(".form-select.is-invalid,", focus)
        self.assertIn(".form-select.is-invalid:focus,", focus)
        self.assertIn(".was-validated .form-select:invalid,", focus)
        self.assertIn(".was-validated .form-select:invalid:focus", focus)
        self.assertIn(
            "box-shadow: 0 0 0 #{$moo-form-focus-ring-width} var(--moo-form-invalid-ring-color);",
            focus,
        )

    def test_invalid_input_example_uses_field_invalid_contract(self) -> None:
        page_source = PAGE.read_text(encoding="utf-8")
        invalid_block = page_source[
            page_source.index("{% set invalid %}"):
            page_source.index("{% set file_input %}")
        ]

        self.assertIn("{% call field(invalid=true) %}", invalid_block)
        self.assertIn('label="Invalid Input"', invalid_block)
        self.assertIn('placeholder="Error"', invalid_block)
        self.assertIn("This field contains validation errors.", invalid_block)
        self.assertIn(
            'describedby="input-invalid-help"',
            invalid_block,
        )

    def test_input_emits_validation_and_required_states(self) -> None:
        output = self.render_input(
            'input(label="Key", id="key", aria_invalid=true, required=true)'
        )

        self.assertIn(" is-invalid", output)
        self.assertIn(' aria-invalid="true"', output)
        self.assertIn(" required", output)

    def test_full_form_example_uses_preview_validation_handler(self) -> None:
        page_source = PAGE.read_text(encoding="utf-8")
        form_block = page_source[
            page_source.index("{% set full_form %}"):
            page_source.index("{% set rtl_arabic %}")
        ]

        self.assertIn('form(extra_class="needs-validation mx-auto", novalidate=true)', form_block)

    def test_input_rtl_examples_keep_direction_wrapper_full_width(self) -> None:
        page_source = PAGE.read_text(encoding="utf-8")

        for block_name, direction in (
            ("rtl_arabic", "rtl"),
            ("rtl_hebrew", "rtl"),
            ("rtl_english", "ltr"),
        ):
            block_start = "{% set " + block_name + " %}"
            block = page_source[
                page_source.index(block_start):
                page_source.index("{% endset %}", page_source.index(block_start))
            ]

            with self.subTest(block=block_name):
                self.assertIn(f'<div dir="{direction}" class="w-100">', block)

    def test_input_describedby_links_helper_text(self) -> None:
        output = self.render_input(
            'input(label="Key", id="key", describedby="key-help")'
        )

        self.assertIn('aria-describedby="key-help"', output)

    def test_file_example_uses_bare_bootstrap_file_input_group(self) -> None:
        page_source = PAGE.read_text(encoding="utf-8")
        file_block = page_source[
            page_source.index("{% set file_input %}"):
            page_source.index('{% set inline %}')
        ]

        self.assertIn("{% call input_group() %}", file_block)
        self.assertIn('aria_label="Upload"', file_block)
        self.assertIn('id="input-picture"', file_block)
        self.assertIn('type="file"', file_block)
        self.assertNotIn("input_group_text", file_block)
        self.assertNotIn("field_description", file_block)
        self.assertNotIn('label="Picture"', file_block)

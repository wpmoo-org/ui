from __future__ import annotations

import re

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/switch.html.jinja"
PAGE = ROOT / "site/src/pages/components/switch.html.jinja"
CHECKBOX_SCSS = ROOT / "scss/components/_checkbox.scss"
FIELD_SCSS = ROOT / "scss/components/_field.scss"
COMPONENT_SETTINGS_SCSS = ROOT / "scss/settings/_components.scss"


class SwitchTests(CatalogTestCase):
    def render_switch(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Switch macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/switch.html.jinja" import switch %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_switch_renders_sibling_input_and_label(self) -> None:
        self.assertEqual(
            self.render_switch('switch("s1", label="Airplane mode")'),
            '<div class="form-check form-switch"> <input class="form-check-input"'
            ' type="checkbox" role="switch" id="s1"> <label class="form-check-label"'
            ' for="s1">Airplane mode</label> </div>',
        )

    def test_switch_checked_and_disabled_are_space_separated(self) -> None:
        output = self.render_switch(
            'switch("s2", label="Airplane mode", checked=true, disabled=true)'
        )
        self.assertIn('id="s2" checked disabled>', output)

    def test_switch_supports_aria_label_without_visible_label(self) -> None:
        output = self.render_switch('switch("s3", aria_label="Airplane mode")')
        self.assertIn('aria-label="Airplane mode"', output)
        self.assertNotIn("form-check-label", output)

    def test_switch_requires_exactly_one_of_label_or_aria_label(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Switch requires exactly one of label, aria_label, or labelledby"
        ):
            self.render_switch('switch("s")')
        with self.assertRaisesRegex(
            ValueError, "Switch requires exactly one of label, aria_label, or labelledby"
        ):
            self.render_switch('switch("s", label="A", aria_label="B")')
        with self.assertRaisesRegex(
            ValueError, "Switch requires exactly one of label, aria_label, or labelledby"
        ):
            self.render_switch('switch("s", aria_label="A", labelledby="s-label")')

    def test_switch_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Switch id is required"):
            self.render_switch('switch("   ", label="Airplane mode")')

    def test_switch_label_wrapper_rejects_visible_label(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Switch label_wrapper requires aria_label or labelledby"
        ):
            self.render_switch(
                'switch("s9", label="Airplane mode", label_wrapper=true)'
            )

    def test_switch_invalid_adds_is_invalid_class(self) -> None:
        output = self.render_switch('switch("s4", label="Airplane mode", invalid=true)')

        self.assertIn('class="form-check-input is-invalid"', output)
        self.assertIn('aria-invalid="true"', output)

    def test_switch_description_renders_form_text(self) -> None:
        output = self.render_switch(
            'switch("s5", label="Airplane mode", description="Details here.")'
        )
        self.assertIn(
            '<div class="form-text" id="s5-description">Details here.</div>',
            output,
        )
        self.assertIn('aria-describedby="s5-description"', output)

    def test_switch_supports_external_description_reference(self) -> None:
        output = self.render_switch(
            'switch("s7", aria_label="Airplane mode", describedby="s7-help")'
        )

        self.assertIn('aria-describedby="s7-help"', output)
        self.assertNotIn('id="s7-description"', output)

    def test_switch_supports_external_label_reference(self) -> None:
        output = self.render_switch(
            'switch("s8", labelledby="s8-label", label_wrapper=true)'
        )

        self.assertIn('aria-labelledby="s8-label"', output)
        self.assertNotIn('aria-label=', output)
        self.assertNotIn("form-check-label", output)

    def test_switch_label_wrapper_keeps_description_outside_label(self) -> None:
        output = self.render_switch(
            'switch("s6", aria_label="Airplane mode", label_wrapper=true, '
            'description="Details here.")'
        )

        self.assertIn(
            '<label class="form-check form-switch"> <input class="form-check-input"'
            ' type="checkbox" role="switch" id="s6" aria-label="Airplane mode"'
            ' aria-describedby="s6-description"> </label>',
            output,
        )
        self.assertIn(
            '<div class="form-text" id="s6-description">Details here.</div>',
            output,
        )
        self.assertLess(output.index("</label>"), output.index('id="s6-description"'))

    def test_description_example_uses_fieldset_group_and_field_contract(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        description_block = source[
            source.index("{% set description %}"):
            source.index("{% endset %}", source.index("{% set description %}"))
        ]

        self.assertIn(
            "{% from \"components/field.html.jinja\" import field, "
            "field_description, field_group, fieldset %}",
            source,
        )
        self.assertIn('{% call fieldset("Focus sharing"', description_block)
        self.assertIn("Configure how focus mode follows you across devices.", description_block)
        self.assertIn("{% call field_group()", description_block)
        self.assertIn("switch_field(", description_block)
        self.assertIn('"switch-description"', description_block)
        self.assertNotIn("visually-hidden", description_block)
        self.assertIn('label class="form-label"', source)
        self.assertIn("field_description(", source)

    def test_hero_preview_uses_single_enable_notifications_field(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        hero_block = source[
            source.index("<div class=\"moo-example__surface mb-5\">"):
            source.index('<section class="moo-example" aria-labelledby="usage">')
        ]

        self.assertIn('switch("switch-hero-notifications"', hero_block)
        self.assertIn('label="Enable notifications"', hero_block)
        self.assertNotIn("switch-hero-sync", hero_block)
        self.assertNotIn("switch-hero-disabled", hero_block)
        self.assertNotIn("switch_field(", hero_block)

    def test_usage_section_is_guidance_text_not_a_live_example(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        usage_block = source[
            source.index('<section class="moo-example" aria-labelledby="usage">'):
            source.index("{% set description %}")
        ]

        self.assertIn('<section class="moo-example" aria-labelledby="usage">', usage_block)
        self.assertIn('<h2 class="h4" id="usage">Usage</h2>', usage_block)
        self.assertIn("Use a switch for one boolean setting.", usage_block)
        self.assertNotIn("render_example(", usage_block)
        self.assertNotIn("moo-example__surface", usage_block)
        self.assertNotIn("switch_field(", usage_block)

    def test_switch_examples_use_field_contract_without_utility_layout(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        utility_layout_classes = (
            "d-grid",
            "d-flex",
            "align-items-start",
            "justify-content-between",
            "gap-2",
            "gap-3",
            "gap-5",
            "fw-medium",
            "mb-1",
            "m-0",
            "form-check-reverse",
        )

        for block_name in ("description", "disabled", "invalid"):
            block = source[
                source.index(f"{{% set {block_name} %}}"):
                source.index("{% endset %}", source.index(f"{{% set {block_name} %}}"))
            ]
            self.assertIn("{% call fieldset(", block, block_name)
            self.assertIn("{% call field_group()", block, block_name)
            self.assertIn("switch_field(", block, block_name)
            for utility_class in utility_layout_classes:
                self.assertNotIn(utility_class, block, block_name)

        self.assertGreaterEqual(source.count("switch_field("), 10)
        self.assertIn("field--disabled", source)
        self.assertIn("invalid=invalid", source)

    def test_invalid_example_is_description_model_with_invalid_state(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        invalid_block = source[
            source.index("{% set invalid %}"):
            source.index("{% endset %}", source.index("{% set invalid %}"))
        ]

        self.assertIn("Accept terms and conditions", invalid_block)
        self.assertIn(
            "You must accept the terms and conditions to continue.",
            invalid_block,
        )
        self.assertIn("invalid=true", invalid_block)
        self.assertIn("switch_field(", invalid_block)

    def test_switch_field_layout_is_owned_by_field_css(self) -> None:
        field_source = FIELD_SCSS.read_text(encoding="utf-8")
        settings_source = COMPONENT_SETTINGS_SCSS.read_text(encoding="utf-8")

        self.assertIn("$moo-field-switch-gap: $moo-field-group-gap !default;", settings_source)
        self.assertIn(".field--switch {", field_source)
        self.assertIn("align-items: flex-start;", field_source)
        self.assertIn("justify-content: space-between;", field_source)
        self.assertIn("gap: $moo-field-switch-gap;", field_source)
        self.assertIn("> label {", field_source)
        self.assertIn("margin: 0;", field_source)
        self.assertIn(".field--disabled {", field_source)
        self.assertIn("opacity: $moo-disabled-control-opacity;", field_source)

    def test_dark_unchecked_mouse_focus_keeps_thumb_visible(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        selector = (
            r":where\(\[data-bs-theme=\"dark\"\]\) "
            r"\.form-switch \.form-check-input:focus:not"
            r"\(:focus-visible\):not\(:checked\)"
        )
        rule = re.search(rf"{selector}[^{{]*\{{(?P<body>[^}}]*)\}}", css)

        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertIn(
            "fill='rgba%28255, 255, 255, 0.25%29'",
            rule.group("body"),
        )

    def test_invalid_checked_checkbox_override_does_not_target_switch(self) -> None:
        source = CHECKBOX_SCSS.read_text(encoding="utf-8")
        rule = re.search(
            r"(?P<selectors>\.form-check-input:is\(\[type=\"checkbox\"\], "
            r"\[type=\"radio\"\]\)[^{]+)\{\n"
            r"\s+border-color: var\(--bs-primary\);\n"
            r"\s+background-color: var\(--bs-primary\);",
            source,
        )

        self.assertIsNotNone(rule)
        assert rule is not None
        selectors = [
            selector.strip().removesuffix(",")
            for selector in rule.group("selectors").splitlines()
            if selector.strip()
        ]
        self.assertGreaterEqual(len(selectors), 1)
        for selector in selectors:
            self.assertIn(':not([role="switch"])', selector)

from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/switch.html.jinja"
PAGE = ROOT / "src/pages/components/switch.html.jinja"


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
            ValueError, "Switch requires exactly one of label or aria_label"
        ):
            self.render_switch('switch("s")')
        with self.assertRaisesRegex(
            ValueError, "Switch requires exactly one of label or aria_label"
        ):
            self.render_switch('switch("s", label="A", aria_label="B")')

    def test_switch_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Switch id is required"):
            self.render_switch('switch("   ", label="Airplane mode")')

    def test_switch_invalid_adds_is_invalid_class(self) -> None:
        self.assertIn(
            'class="form-check-input is-invalid"',
            self.render_switch('switch("s4", label="Airplane mode", invalid=true)'),
        )

    def test_switch_description_renders_form_text(self) -> None:
        self.assertIn(
            '<div class="form-text">Details here.</div>',
            self.render_switch(
                'switch("s5", label="Airplane mode", description="Details here.")'
            ),
        )

from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/radio_group.html.jinja"
PAGE = ROOT / "src/pages/components/radio-group.html.jinja"


class RadioGroupTests(CatalogTestCase):
    def render_radio_group(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Radio Group macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/radio_group.html.jinja" import radio_group %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_radio_group_renders_fieldset_legend_and_items(self) -> None:
        self.assertEqual(
            self.render_radio_group(
                'radio_group("plan", "Plan", [{"id": "plan-a", "label": "A"}])'
            ),
            '<fieldset class="radio-group"> <legend class="form-label">Plan</legend>'
            ' <div class="form-check">'
            ' <input class="form-check-input" type="radio" name="plan" id="plan-a">'
            ' <label class="form-check-label" for="plan-a">A</label>'
            " </div> </fieldset>",
        )

    def test_radio_group_checked_and_disabled_are_space_separated(self) -> None:
        output = self.render_radio_group(
            'radio_group("plan", "Plan", '
            '[{"id": "plan-a", "label": "A", "checked": true, "disabled": true}])'
        )
        self.assertIn('id="plan-a" checked disabled>', output)

    def test_radio_group_item_value_renders_when_provided(self) -> None:
        output = self.render_radio_group(
            'radio_group("plan", "Plan", '
            '[{"id": "plan-a", "label": "A", "value": "option-a"}])'
        )
        self.assertIn('value="option-a"', output)

    def test_radio_group_item_description_renders_form_text(self) -> None:
        output = self.render_radio_group(
            'radio_group("plan", "Plan", '
            '[{"id": "plan-a", "label": "A", "description": "Details here."}])'
        )
        self.assertIn(
            '<div class="form-text" id="plan-a-description">Details here.</div>',
            output,
        )
        self.assertIn('aria-describedby="plan-a-description"', output)

    def test_radio_group_supports_extra_class(self) -> None:
        output = self.render_radio_group(
            'radio_group("plan", "Plan", [{"id": "plan-a", "label": "A"}], extra_class="mb-3")'
        )
        self.assertIn('class="radio-group mb-3"', output)

    def test_radio_group_requires_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Radio Group name is required"):
            self.render_radio_group(
                'radio_group("   ", "Plan", [{"id": "plan-a", "label": "A"}])'
            )

    def test_radio_group_requires_legend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Radio Group legend is required"):
            self.render_radio_group(
                'radio_group("plan", "   ", [{"id": "plan-a", "label": "A"}])'
            )

    def test_radio_group_requires_items(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Radio Group requires at least one item"
        ):
            self.render_radio_group('radio_group("plan", "Plan", [])')

    def test_radio_group_requires_item_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Radio Group item id is required"):
            self.render_radio_group(
                'radio_group("plan", "Plan", [{"id": "   ", "label": "A"}])'
            )

    def test_radio_group_requires_item_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Radio Group item label is required"):
            self.render_radio_group(
                'radio_group("plan", "Plan", [{"id": "plan-a", "label": "   "}])'
            )

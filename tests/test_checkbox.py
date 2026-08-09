from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/checkbox.html.jinja"
PAGE = ROOT / "site/src/pages/components/checkbox.html.jinja"


class CheckboxTests(CatalogTestCase):
    def render_checkbox(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Checkbox macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/checkbox.html.jinja" import checkbox %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_checkbox_renders_sibling_input_and_label(self) -> None:
        self.assertEqual(
            self.render_checkbox('checkbox("c1", label="Accept")'),
            '<div class="form-check"> <input class="form-check-input"'
            ' type="checkbox" id="c1"> <label class="form-check-label"'
            ' for="c1">Accept</label> </div>',
        )

    def test_checkbox_checked_and_disabled_are_space_separated(self) -> None:
        output = self.render_checkbox(
            'checkbox("c2", label="Accept", checked=true, disabled=true)'
        )
        self.assertIn('id="c2" checked disabled>', output)

    def test_checkbox_supports_aria_label_without_visible_label(self) -> None:
        output = self.render_checkbox('checkbox("c3", aria_label="Accept")')
        self.assertIn('aria-label="Accept"', output)
        self.assertNotIn("form-check-label", output)

    def test_checkbox_supports_input_attrs_and_label_wrapper(self) -> None:
        output = self.render_checkbox(
            'checkbox("c6", aria_label="Select row", '
            'input_attrs="data-select-row", label_wrapper=true)'
        )

        self.assertTrue(output.startswith('<label class="form-check">'))
        self.assertIn('data-select-row', output)
        self.assertIn('aria-label="Select row"', output)

    def test_checkbox_requires_exactly_one_of_label_or_aria_label(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Checkbox requires exactly one of label or aria_label"
        ):
            self.render_checkbox('checkbox("c")')
        with self.assertRaisesRegex(
            ValueError, "Checkbox requires exactly one of label or aria_label"
        ):
            self.render_checkbox('checkbox("c", label="A", aria_label="B")')

    def test_checkbox_requires_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Checkbox id is required"):
            self.render_checkbox('checkbox("   ", label="Accept")')

    def test_checkbox_label_wrapper_rejects_visible_label(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Checkbox label_wrapper requires aria_label"
        ):
            self.render_checkbox('checkbox("c7", label="Accept", label_wrapper=true)')

    def test_checkbox_invalid_adds_is_invalid_class(self) -> None:
        output = self.render_checkbox('checkbox("c4", label="Accept", invalid=true)')

        self.assertIn('class="form-check-input is-invalid"', output)
        self.assertIn('aria-invalid="true"', output)

    def test_checkbox_description_renders_form_text(self) -> None:
        output = self.render_checkbox(
            'checkbox("c5", label="Accept", description="Details here.")'
        )
        self.assertIn(
            '<div class="form-text" id="c5-description">Details here.</div>',
            output,
        )
        self.assertIn('aria-describedby="c5-description"', output)

    def test_page_uses_render_rtl_example(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "includes/example.html.jinja" import render_example, render_rtl_example %}',
            source,
        )
        self.assertIn('render_rtl_example(', source)
        self.assertIn('"checkbox"', source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertIn("dir=\"rtl\"", source)
        self.assertNotIn('{% from "components/tabs.html.jinja" import tabs %}', source)

        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/checkbox.html")
        self.assertIn("checkbox-direction-tabs", output)
        self.assertIn("rtl-arabic-code", output)
        self.assertIn("rtl-hebrew-code", output)
        self.assertIn("rtl-english-code", output)
        self.assertIn('id="rtl">RTL</h2>', output)

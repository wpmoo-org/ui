from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/field.html.jinja"
PAGE = ROOT / "src/pages/components/field.html.jinja"
PREVIEW_JS = ROOT / "static/js/preview.js"


class FieldTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Field macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/field.html.jinja" import form, field, '
            "field_description, field_error, field_group, "
            'fieldset %}' + source
        )
        return " ".join(template.render().split())

    def test_form_renders_form_tag_with_novalidate_and_class(self) -> None:
        output = self.render(
            '{% call form(extra_class="needs-validation", novalidate=true) %}<p>Content</p>{% endcall %}'
        )

        self.assertIn('<form class="needs-validation" novalidate>', output)
        self.assertIn("<p>Content</p>", output)
        self.assertIn("</form>", output)

    def test_form_omits_class_and_novalidate_by_default(self) -> None:
        output = self.render('{% call form() %}x{% endcall %}')

        self.assertIn("<form>", output)
        self.assertNotIn("novalidate", output)

    def test_field_wraps_caller_content(self) -> None:
        output = self.render(
            '{% call field() %}<p>Content</p>{% endcall %}'
        )

        self.assertIn('class="field"', output)
        self.assertIn("<p>Content</p>", output)

    def test_field_accepts_extra_class(self) -> None:
        output = self.render(
            '{% call field(extra_class="mb-3") %}x{% endcall %}'
        )

        self.assertIn('class="field mb-3"', output)

    def test_field_description_renders_form_text(self) -> None:
        output = self.render(
            '{{ field_description("field-1-description", "Helper text.") }}'
        )

        self.assertIn('class="form-text"', output)
        self.assertIn('id="field-1-description"', output)
        self.assertIn("Helper text.", output)

    def test_field_description_requires_id_and_text(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Field description id is required"
        ):
            self.render('{{ field_description("   ", "Helper text.") }}')
        with self.assertRaisesRegex(
            ValueError, "Field description text is required"
        ):
            self.render(
                '{{ field_description("field-1-description", "   ") }}'
            )

    def test_field_error_renders_invalid_feedback(self) -> None:
        output = self.render(
            '{{ field_error("field-1-error", "This field is required.") }}'
        )

        self.assertIn('class="invalid-feedback"', output)
        self.assertIn('id="field-1-error"', output)
        self.assertIn("This field is required.", output)

    def test_field_error_requires_id_and_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "Field error id is required"):
            self.render('{{ field_error("   ", "This field is required.") }}')
        with self.assertRaisesRegex(
            ValueError, "Field error text is required"
        ):
            self.render(
                '{{ field_error("field-1-error", "   ") }}'
            )

    def test_field_group_wraps_caller_content(self) -> None:
        output = self.render(
            '{% call field_group() %}<p>Content</p>{% endcall %}'
        )

        self.assertIn('class="field-group"', output)
        self.assertIn("<p>Content</p>", output)

    def test_fieldset_renders_legend_and_content(self) -> None:
        output = self.render(
            '{% call fieldset("Notifications") %}<p>Content</p>{% endcall %}'
        )

        self.assertIn('<fieldset class="field-fieldset">', output)
        self.assertIn('<legend class="form-label">Notifications</legend>', output)
        self.assertIn("<p>Content</p>", output)
        self.assertNotIn('class="form-text mb-2"', output)

    def test_fieldset_accepts_extra_class(self) -> None:
        output = self.render(
            '{% call fieldset("Notifications", extra_class="mb-3") %}x{% endcall %}'
        )

        self.assertIn('<fieldset class="field-fieldset mb-3">', output)

    def test_fieldset_description_is_optional(self) -> None:
        output = self.render(
            '{% call fieldset("Notifications", description="Choose what to hear about.") %}x{% endcall %}'
        )

        self.assertIn('class="form-text mb-2"', output)
        self.assertIn("Choose what to hear about.", output)

    def test_fieldset_requires_legend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Fieldset legend is required"):
            self.render('{% call fieldset("   ") %}x{% endcall %}')

    def test_page_composes_field_with_ready_form_controls(self) -> None:
        self.assertTrue(PAGE.is_file(), "Field page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "components/field.html.jinja" import form, field, '
            "field_description, field_error, field_group, "
            'fieldset %}',
            source,
        )
        self.assertIn(
            '{% from "components/input.html.jinja" import input %}', source
        )
        self.assertIn(
            '{% from "components/textarea.html.jinja" import textarea %}', source
        )
        self.assertIn(
            '{% from "components/select.html.jinja" import select %}', source
        )
        self.assertIn(
            '{% from "components/switch.html.jinja" import switch %}', source
        )
        self.assertIn(
            'form(extra_class="needs-validation", novalidate=true)', source
        )
        self.assertIn("field_error(", source)
        self.assertIn("field_description(", source)
        self.assertIn("fieldset(", source)
        self.assertIn('type="submit"', source)

    def test_preview_js_wires_needs_validation_forms(self) -> None:
        self.assertTrue(PREVIEW_JS.is_file())
        source = PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn('form.needs-validation', source)
        self.assertIn("checkValidity", source)
        self.assertIn("was-validated", source)

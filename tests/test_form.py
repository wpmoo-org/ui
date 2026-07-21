from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/form.html.jinja"
PAGE = ROOT / "src/pages/components/form.html.jinja"
PREVIEW_JS = ROOT / "static/js/preview.js"


class FormTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Form macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/form.html.jinja" import form, form_field, '
            "form_field_description, form_field_error, form_field_group, "
            'form_fieldset %}' + source
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

    def test_form_field_wraps_caller_content(self) -> None:
        output = self.render(
            '{% call form_field() %}<p>Content</p>{% endcall %}'
        )

        self.assertIn('class="form-field"', output)
        self.assertIn("<p>Content</p>", output)

    def test_form_field_accepts_extra_class(self) -> None:
        output = self.render(
            '{% call form_field(extra_class="mb-3") %}x{% endcall %}'
        )

        self.assertIn('class="form-field mb-3"', output)

    def test_form_field_description_renders_form_text(self) -> None:
        output = self.render(
            '{{ form_field_description("field-1-description", "Helper text.") }}'
        )

        self.assertIn('class="form-text"', output)
        self.assertIn('id="field-1-description"', output)
        self.assertIn("Helper text.", output)

    def test_form_field_description_requires_id_and_text(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Form field description id is required"
        ):
            self.render('{{ form_field_description("   ", "Helper text.") }}')
        with self.assertRaisesRegex(
            ValueError, "Form field description text is required"
        ):
            self.render(
                '{{ form_field_description("field-1-description", "   ") }}'
            )

    def test_form_field_error_renders_invalid_feedback(self) -> None:
        output = self.render(
            '{{ form_field_error("field-1-error", "This field is required.") }}'
        )

        self.assertIn('class="invalid-feedback"', output)
        self.assertIn('id="field-1-error"', output)
        self.assertIn("This field is required.", output)

    def test_form_field_error_requires_id_and_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "Form field error id is required"):
            self.render('{{ form_field_error("   ", "This field is required.") }}')
        with self.assertRaisesRegex(
            ValueError, "Form field error text is required"
        ):
            self.render(
                '{{ form_field_error("field-1-error", "   ") }}'
            )

    def test_form_field_group_wraps_caller_content(self) -> None:
        output = self.render(
            '{% call form_field_group() %}<p>Content</p>{% endcall %}'
        )

        self.assertIn('class="form-field-group"', output)
        self.assertIn("<p>Content</p>", output)

    def test_form_fieldset_renders_legend_and_content(self) -> None:
        output = self.render(
            '{% call form_fieldset("Notifications") %}<p>Content</p>{% endcall %}'
        )

        self.assertIn("<fieldset>", output)
        self.assertIn('<legend class="form-label">Notifications</legend>', output)
        self.assertIn("<p>Content</p>", output)
        self.assertNotIn('class="form-text mb-2"', output)

    def test_form_fieldset_description_is_optional(self) -> None:
        output = self.render(
            '{% call form_fieldset("Notifications", description="Choose what to hear about.") %}x{% endcall %}'
        )

        self.assertIn('class="form-text mb-2"', output)
        self.assertIn("Choose what to hear about.", output)

    def test_form_fieldset_requires_legend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Form fieldset legend is required"):
            self.render('{% call form_fieldset("   ") %}x{% endcall %}')

    def test_page_composes_form_with_ready_field_controls(self) -> None:
        self.assertTrue(PAGE.is_file(), "Form page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "components/form.html.jinja" import form, form_field, '
            "form_field_description, form_field_error, form_field_group, "
            'form_fieldset %}',
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
        self.assertIn("form_field_error(", source)
        self.assertIn("form_field_description(", source)
        self.assertIn("form_fieldset(", source)
        self.assertIn('type="submit"', source)

    def test_preview_js_wires_needs_validation_forms(self) -> None:
        self.assertTrue(PREVIEW_JS.is_file())
        source = PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn('form.needs-validation', source)
        self.assertIn("checkValidity", source)
        self.assertIn("was-validated", source)

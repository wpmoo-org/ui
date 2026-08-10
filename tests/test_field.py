from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/field.html.jinja"
PAGE = ROOT / "site/src/pages/components/field.html.jinja"
FIELD_SCSS = ROOT / "scss/components/_field.scss"
COMPONENT_SETTINGS_SCSS = ROOT / "scss/settings/_components.scss"
BOOTSTRAP_PREVIEW_JS = ROOT / "site/src/js/catalog/bootstrap-preview.js"


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

        self.assertIn('<form class="field-form needs-validation" novalidate>', output)
        self.assertIn("<p>Content</p>", output)
        self.assertIn("</form>", output)

    def test_form_renders_field_form_class_by_default(self) -> None:
        output = self.render('{% call form() %}x{% endcall %}')

        self.assertIn('<form class="field-form">', output)
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

    def test_field_accepts_invalid_state(self) -> None:
        output = self.render(
            '{% call field(invalid=true) %}x{% endcall %}'
        )

        self.assertIn('<div class="field" data-invalid="true">', output)

    def test_field_styles_invalid_state_from_wrapper(self) -> None:
        source = FIELD_SCSS.read_text(encoding="utf-8")

        self.assertIn('&[data-invalid="true"] {', source)
        self.assertIn("color: var(--bs-form-invalid-color);", source)
        self.assertNotIn(":has(> .is-invalid) > .form-label", source)

    def test_field_description_renders_form_text(self) -> None:
        output = self.render(
            '{{ field_description("field-1-description", "Helper text.") }}'
        )

        self.assertIn('class="field-description form-text"', output)
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

        self.assertIn('class="field-error invalid-feedback"', output)
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
        self.assertIn('<legend class="field-legend">Notifications</legend>', output)
        self.assertIn("<p>Content</p>", output)
        self.assertNotIn('field-description', output)

    def test_fieldset_accepts_extra_class(self) -> None:
        output = self.render(
            '{% call fieldset("Notifications", extra_class="mb-3") %}x{% endcall %}'
        )

        self.assertIn('<fieldset class="field-fieldset mb-3">', output)

    def test_fieldset_description_is_optional(self) -> None:
        output = self.render(
            '{% call fieldset("Notifications", description="Choose what to hear about.") %}x{% endcall %}'
        )

        self.assertIn('class="field-description form-text"', output)
        self.assertIn("Choose what to hear about.", output)

    def test_fieldset_sibling_spacing_uses_dedicated_token(self) -> None:
        field_source = FIELD_SCSS.read_text(encoding="utf-8")
        settings_source = COMPONENT_SETTINGS_SCSS.read_text(encoding="utf-8")

        self.assertIn(
            "$moo-field-form-gap: $moo-field-group-gap !default;",
            settings_source,
        )
        self.assertIn(
            "$moo-field-fieldset-sibling-gap: "
            "$moo-field-group-gap !default;",
            settings_source,
        )
        self.assertIn(".field-form {", field_source)
        self.assertIn("gap: $moo-field-form-gap;", field_source)
        self.assertIn(".field-fieldset + .field-fieldset", field_source)
        self.assertIn(
            "margin-top: $moo-field-fieldset-sibling-gap;",
            field_source,
        )
        self.assertIn(".field-form > .field-fieldset + .field-fieldset", field_source)

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

    def test_page_form_like_examples_use_standard_preview_measure(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/field.html")

        for example in (
            "basic",
            "invalid",
            "disabled",
            "group",
            "textarea",
            "select",
            "fieldset",
            "fieldset-group",
            "checkbox",
            "separator",
        ):
            with self.subTest(example=example):
                section = page.split(f'data-example="{example}"', 1)[1].split(
                    '<div class="moo-example__source"',
                    1,
                )[0]
                self.assertIn(
                    'class="moo-example__preview moo-example__preview--narrow"',
                    section,
                )

        self.assertGreaterEqual(
            page.count('<div class="w-100" dir="rtl">'),
            2,
        )
        self.assertIn('<div class="w-100" dir="ltr">', page)

    def test_catalog_bootstrap_module_wires_needs_validation_forms(self) -> None:
        self.assertTrue(BOOTSTRAP_PREVIEW_JS.is_file())
        source = BOOTSTRAP_PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn('form.needs-validation', source)
        self.assertIn("checkValidity", source)
        self.assertIn("was-validated", source)

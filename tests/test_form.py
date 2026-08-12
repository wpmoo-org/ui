from __future__ import annotations

import json

from tests.helpers import ROOT, CatalogTestCase


PAGE = ROOT / "site/src/pages/components/form.html.jinja"
REGISTRY = ROOT / "src/registry/components.json"


class FormPageTests(CatalogTestCase):
    def test_form_is_a_catalog_page_backed_by_field_primitives(self) -> None:
        self.assertTrue(PAGE.is_file(), "Form page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn(
            '{% from "components/field.html.jinja" import form, field, '
            "field_description, field_error, field_group, fieldset %}",
            source,
        )
        self.assertIn("{% call form(", source)
        self.assertIn("{% call fieldset(", source)
        self.assertIn("{% call field_group()", source)
        self.assertIn("{% call field()", source)
        self.assertNotIn('{% from "components/form.html.jinja"', source)

    def test_form_is_listed_as_ready_without_a_new_component_macro(self) -> None:
        catalog = json.loads(REGISTRY.read_text(encoding="utf-8"))
        form = next((item for item in catalog if item["slug"] == "form"), None)

        self.assertIsNotNone(form)
        self.assertEqual(form["label"], "Form")
        self.assertEqual(form["status"], "ready")
        self.assertFalse((ROOT / "src/components/form.html.jinja").exists())

    def test_usage_links_to_related_field_and_control_pages(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/form.html")

        usage = page.split('id="usage">Usage</h2>', 1)[1].split(
            'data-example="account-settings"',
            1,
        )[0]

        for href in (
            "/components/field/",
            "/components/input/",
            "/components/select/",
            "/components/checkbox/",
        ):
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"', usage)

    def test_form_page_includes_shared_rtl_example_for_intro_pattern(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('render_rtl_example(', source)
        self.assertIn('"form-profile"', source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertIn('dir="rtl"', source)
        self.assertIn('dir="ltr"', source)

    def test_form_examples_use_pattern_headings_instead_of_scenario_titles(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/form.html")

        for heading in (
            'id="field-composition">Field composition</h2>',
            'id="validation-feedback">Validation feedback</h2>',
            'id="grouped-controls">Grouped controls</h2>',
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, page)

        for heading in (
            'id="account-settings">Account settings</h2>',
            'id="deploy-request">Deploy request</h2>',
            'id="access-policy">Access policy</h2>',
        ):
            with self.subTest(heading=heading):
                self.assertNotIn(heading, page)

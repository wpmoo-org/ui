from __future__ import annotations

import json

from tests.helpers import ROOT, CatalogTestCase


PAGE = ROOT / "src/pages/components/form.html.jinja"
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
        self.assertIn("Bootstrap Forms", source)
        self.assertIn("Field", source)
        self.assertNotIn('{% from "components/form.html.jinja"', source)

    def test_form_is_listed_as_ready_without_a_new_component_macro(self) -> None:
        catalog = json.loads(REGISTRY.read_text(encoding="utf-8"))
        form = next((item for item in catalog if item["slug"] == "form"), None)

        self.assertIsNotNone(form)
        self.assertEqual(form["label"], "Form")
        self.assertEqual(form["status"], "ready")
        self.assertFalse((ROOT / "src/components/form.html.jinja").exists())


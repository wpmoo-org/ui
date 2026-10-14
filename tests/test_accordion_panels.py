from __future__ import annotations

from build import create_environment
from tests.helpers import CatalogTestCase


class AccordionPanelsTests(CatalogTestCase):
    def render_panels(self, options: str = "") -> str:
        template = create_environment().from_string(
            '{% from "blocks/accordion_panels.html.jinja" import accordion_panels %}'
            '{{ accordion_panels("panels", [{"id": "a", "heading_id": "authored:a", '
            '"title": "<Question>", "content": "<p>Original <strong>guidance</strong></p>", '
            '"disabled": true, "open": true}]' + options + ') }}'
        )
        return " ".join(template.render().split())

    def test_recipe_preserves_content_and_multiple_open_contract(self) -> None:
        output = self.render_panels()
        self.assertIn('id="authored:a"', output)
        self.assertIn('&lt;Question&gt;', output)
        self.assertIn('<p>Original <strong>guidance</strong></p>', output)
        self.assertIn('data-accordion-indicator="plus-minus"', output)
        self.assertIn('role="region"', output)
        self.assertIn('d-grid gap-2', output)
        self.assertIn('border rounded overflow-hidden', output)
        self.assertIn('bg-body-secondary fw-semibold text-start pe-5 text-decoration-none', output)
        self.assertIn('aria-expanded="true"', output)
        self.assertIn('disabled', output)
        self.assertNotIn('data-bs-parent', output)

    def test_recipe_single_open_and_caller_classes(self) -> None:
        output = self.render_panels(', always_open=false, extra_class="mb-4"')
        self.assertIn('data-bs-parent="#panels"', output)
        self.assertIn('d-grid gap-2 mb-4', output)

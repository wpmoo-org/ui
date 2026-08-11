from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/button_group.html.jinja"
PAGE = ROOT / "site/src/pages/components/button-group.html.jinja"


class ButtonGroupTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Button Group macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def test_renders_bootstrap_group_with_accessible_label(self) -> None:
        output = self.render(
            '{% from "components/button_group.html.jinja" import button_group %}'
            '{% call button_group("Ticket actions") %}Actions{% endcall %}'
        )

        self.assertIn('class="btn-group"', output)
        self.assertIn('role="group"', output)
        self.assertIn('aria-label="Ticket actions"', output)

    def test_toolbar_and_vertical_modes_use_bootstrap_classes(self) -> None:
        toolbar = self.render(
            '{% from "components/button_group.html.jinja" import button_group %}'
            '{% call button_group("Editor toolbar", toolbar=true, extra_class="gap-2") %}x{% endcall %}'
        )
        vertical = self.render(
            '{% from "components/button_group.html.jinja" import button_group %}'
            '{% call button_group("Quantity", vertical=true) %}x{% endcall %}'
        )

        self.assertIn('class="btn-toolbar gap-2"', toolbar)
        self.assertIn('role="toolbar"', toolbar)
        self.assertIn('class="btn-group-vertical"', vertical)

    def test_page_uses_render_rtl_example_for_direction(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('render_rtl_example(', source)
        self.assertIn('"button-group-ribbon"', source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertIn('dir="rtl"', source)
        self.assertNotIn('{% from "components/tabs.html.jinja" import tabs %}', source)

    def test_page_omits_redundant_split_example_and_keeps_dropdown_menu(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/button-group.html")
        self.assertNotIn('data-example="split-button"', output)
        self.assertNotIn('aria-label="Follow options"', output)

        section = output.split('data-example="dropdown-button"', 1)[1].split(
            '<div class="moo-example__source"',
            1,
        )[0]

        self.assertIn('aria-label="Deploy options"', section)
        self.assertIn('data-bs-toggle="dropdown"', section)
        self.assertIn('class="dropdown-menu dropdown-menu-end"', section)

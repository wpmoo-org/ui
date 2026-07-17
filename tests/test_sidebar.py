from __future__ import annotations

from build import create_environment
from tests.helpers import CatalogTestCase


class SidebarTests(CatalogTestCase):
    def render_sidebar(self, source: str) -> str:
        template = create_environment().from_string(
            '{% from "components/sidebar.html.jinja" import '
            'sidebar, sidebar_content, sidebar_group_label, sidebar_menu_button, '
            'sidebar_menu_action, sidebar_menu_sub, sidebar_menu_sub_button, '
            'sidebar_provider, sidebar_trigger %}'
            + source
        )
        return " ".join(template.render().split())

    def test_sidebar_provider_and_trigger_emit_accessible_shell_contract(self) -> None:
        output = self.render_sidebar(
            """
            {% call sidebar_provider(key="catalog-shell") %}
              {{ sidebar_trigger(sidebar_id="catalog-sidebar") }}
              {% call sidebar(aria_label="Catalog navigation") %}
                {% call sidebar_content() %}
                  {{ sidebar_group_label("Components") }}
                {% endcall %}
              {% endcall %}
            {% endcall %}
            """
        )

        self.assertIn('class="sidebar-wrapper"', output)
        self.assertIn('data-moo-sidebar-key="catalog-shell"', output)
        self.assertIn('id="catalog-sidebar"', output)
        self.assertIn('aria-label="Catalog navigation"', output)
        self.assertIn('data-moo-sidebar-trigger', output)
        self.assertIn('data-bs-target="#catalog-sidebar"', output)
        self.assertIn('aria-controls="catalog-sidebar"', output)
        self.assertIn('aria-expanded="true"', output)
        self.assertIn('class="sidebar-content scroll-fade-y no-scrollbar"', output)

    def test_sidebar_menu_contracts_emit_active_and_disclosure_state(self) -> None:
        output = self.render_sidebar(
            """
            {{ sidebar_menu_button(
              "Button", href="components/button.html", active=true, icon="component"
            ) }}
            {% call sidebar_menu_sub(id="projects-sub", open=true) %}
              {{ sidebar_menu_sub_button("Projects", "projects-sub", open=true) }}
            {% endcall %}
            """
        )

        self.assertIn('aria-current="page"', output)
        self.assertIn('data-moo-sidebar-tooltip="Button"', output)
        self.assertIn('id="projects-sub"', output)
        self.assertIn('class="sidebar-menu-sub collapse show"', output)
        self.assertIn('data-bs-toggle="collapse"', output)
        self.assertIn('data-bs-target="#projects-sub"', output)
        self.assertIn('aria-controls="projects-sub"', output)
        self.assertIn('aria-expanded="true"', output)

    def test_sidebar_menu_action_uses_bootstrap_dropdown_and_aria_contract(self) -> None:
        output = self.render_sidebar(
            """
            {% call sidebar_menu_action(aria_label="Project actions") %}
              <span>Rename</span>
            {% endcall %}
            """
        )

        self.assertIn('data-slot="sidebar-menu-action"', output)
        self.assertIn('data-bs-toggle="dropdown"', output)
        self.assertIn('aria-label="Project actions"', output)
        self.assertIn('class="dropdown-menu', output)

    def test_sidebar_macros_fail_fast_on_invalid_contracts(self) -> None:
        invalid_calls = (
            ('sidebar(side="top")', "Unknown sidebar side: top"),
            ('sidebar(variant="card")', "Unknown sidebar variant: card"),
            ('sidebar(collapsible="rail")', "Unknown sidebar collapsible mode: rail"),
            ('sidebar(id="")', "Sidebar id is required"),
            ('sidebar_trigger(sidebar_id="")', "Sidebar trigger target id is required"),
            ('sidebar_group_label("")', "Sidebar group label is required"),
            ('sidebar_menu_button("")', "Sidebar menu button title is required"),
            (
                'sidebar_menu_button("Button", size="compact")',
                "Unknown sidebar menu button size: compact",
            ),
            ('sidebar_menu_sub(id="")', "Sidebar submenu id is required"),
            (
                'sidebar_menu_sub_button("Projects", "")',
                "Sidebar submenu target id is required",
            ),
        )

        for call, message in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_sidebar("{{ " + call + " }}")

    def test_sidebar_catalog_page_uses_distinct_demo_target(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/sidebar.html")
        self.assertEqual(page.count('id="catalog-sidebar"'), 1)
        self.assertEqual(page.count('id="components-sidebar-demo"'), 1)
        self.assertIn('aria-controls="components-sidebar-demo"', page)

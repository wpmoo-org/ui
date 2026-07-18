from __future__ import annotations

import re

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


def _css_block(styles: str, selector: str) -> str:
    pattern = re.compile(rf"(?s){re.escape(selector)}\s*\{{([^}}]+)\}}")
    match = pattern.search(styles)
    if not match:
        raise AssertionError(f"Missing CSS rule for selector: {selector}")
    return match.group(1)


class SidebarTests(CatalogTestCase):
    def render_sidebar(self, source: str) -> str:
        template = create_environment().from_string(
            '{% from "components/sidebar.html.jinja" import '
            'sidebar, sidebar_content, sidebar_group_label, sidebar_input, '
            'sidebar_menu_button, '
            'sidebar_group_action, sidebar_group_content, sidebar_menu_action, '
            'sidebar_menu_badge, sidebar_menu_skeleton, sidebar_menu_sub, '
            'sidebar_menu_sub_button, sidebar_separator, sidebar_provider, '
            'sidebar_trigger %}'
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

    def test_sidebar_group_and_badge_macros_emit_expected_slots_and_classes(self) -> None:
        output = self.render_sidebar(
            """
            {% call sidebar_group_content(extra_class="group-content") %}
              {{ sidebar_group_action(icon="plus", aria_label="Add project", extra_class="group-action") }}
              {{ sidebar_menu_badge("8", variant="outline", extra_class="menu-badge") }}
            {% endcall %}
            """
        )

        self.assertIn('class="sidebar-group-content group-content"', output)
        self.assertIn('data-slot="sidebar-group-content"', output)
        self.assertIn('class="btn btn-ghost btn-icon-xs', output)
        self.assertIn('class="sidebar-group-action group-action"', output)
        self.assertIn('data-slot="sidebar-group-action"', output)
        self.assertIn('aria-label="Add project"', output)
        self.assertIn('class="sidebar-menu-badge menu-badge"', output)
        self.assertIn('class="badge border text-body-secondary"', output)
        self.assertIn('data-slot="sidebar-menu-badge"', output)

    def test_sidebar_group_action_uses_button_composition_and_icon_only_a11y_contract(self) -> None:
        output = self.render_sidebar(
            """
            {{ sidebar_group_action(aria_label="Add project") }}
            """
        )

        self.assertIn('class="sidebar-group-action"', output)
        self.assertIn('class="btn btn-ghost btn-icon-xs', output)
        self.assertIn("btn-icon-xs", output)
        self.assertIn("data-slot=\"sidebar-group-action\"", output)
        self.assertIn("aria-label=\"Add project\"", output)
        self.assertIn("data-icon", output)

    def test_sidebar_menu_badge_uses_badge_composition(self) -> None:
        output = self.render_sidebar(
            """
            {{ sidebar_menu_badge("8", variant="secondary") }}
            """
        )

        self.assertIn('class="sidebar-menu-badge" data-slot="sidebar-menu-badge"', output)
        self.assertIn('class="badge text-bg-secondary"', output)
        self.assertIn('data-slot="sidebar-menu-badge"', output)

    def test_sidebar_input_separator_and_menu_skeleton_composition_and_slots(self) -> None:
        output = self.render_sidebar(
            """
            {{ sidebar_input(id="sidebar-search", placeholder="Search", aria_label="Search docs") }}
            {{ sidebar_separator(extra_class="sidebar-sep") }}
            {{ sidebar_menu_skeleton(show_icon=true, extra_class="menu-skeleton") }}
            """
        )

        self.assertIn('class="sidebar-input"', output)
        self.assertIn('data-slot="sidebar-input"', output)
        self.assertIn('class="form-control"', output)
        self.assertIn('id="sidebar-search"', output)
        self.assertIn('placeholder="Search"', output)
        self.assertIn('aria-label="Search docs"', output)

        self.assertIn('class="sidebar-separator sidebar-sep"', output)
        self.assertIn('data-slot="sidebar-separator"', output)
        self.assertIn('<hr aria-hidden="true">', output)

        self.assertIn('class="sidebar-menu-skeleton menu-skeleton"', output)
        self.assertIn('data-slot="sidebar-menu-skeleton"', output)
        self.assertIn('class="skeleton placeholder-glow', output)
        self.assertIn('aria-hidden="true"', output)

    def test_sidebar_menu_skeleton_icon_option_is_deterministic(self) -> None:
        with_icon = self.render_sidebar("{{ sidebar_menu_skeleton(show_icon=true) }}")
        without_icon = self.render_sidebar("{{ sidebar_menu_skeleton() }}")

        self.assertEqual(
            with_icon.count('class="skeleton placeholder-glow'),
            without_icon.count('class="skeleton placeholder-glow') + 1,
        )

    def test_sidebar_input_fails_fast_for_missing_accessible_name(self) -> None:
        for call in ('sidebar_input(aria_label="")', 'sidebar_input(aria_label="   ")'):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                    ValueError, "Input requires exactly one of label or aria_label"
                ):
                    self.render_sidebar("{{ " + call + " }}")

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
            ('sidebar_group_action(aria_label="")', "Sidebar group action aria-label is required"),
            (
                'sidebar_menu_badge("8", variant="bad")',
                "Unknown badge variant: bad",
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

    def test_sidebar_collapsed_state_scoped_classes_are_present_in_css(self) -> None:
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()
        self.assertIn(".sidebar-group-content", styles)
        self.assertIn(".sidebar-group-action", styles)
        self.assertIn(".sidebar-menu-badge", styles)
        self.assertIn(".sidebar-input", styles)
        self.assertIn(".sidebar-separator", styles)
        self.assertIn(".sidebar-menu-skeleton", styles)
        self.assertIn(".sidebar-group-content--inline", styles)
        self.assertIn(".sidebar-menu-item--has-action > .sidebar-menu-badge", styles)
        self.assertIn(
            "[data-moo-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-group-action",
            styles,
        )
        self.assertIn(
            "[data-moo-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-menu-badge",
            styles,
        )
        self.assertIn(
            "[data-moo-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-menu-skeleton",
            styles,
        )
        self.assertIn(
            "[data-moo-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-menu-skeleton__line",
            styles,
        )

    def test_sidebar_group_content_is_neutral_and_inline_modifier_is_scoped(self) -> None:
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()
        self.assertIn("display: block", _css_block(styles, ".sidebar-group-content"))
        self.assertIn("width: 100%", _css_block(styles, ".sidebar-input"))
        self.assertIn("padding: $spacer * 0.25", _css_block(styles, ".sidebar-input"))
        self.assertIn("display: flex", _css_block(styles, ".sidebar-separator"))
        self.assertIn("display: flex", _css_block(styles, ".sidebar-menu-skeleton"))
        self.assertIn("display: flex", _css_block(styles, ".sidebar-group-content--inline"))
        self.assertIn(
            "justify-content: center",
            _css_block(
                styles,
                '[data-moo-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-skeleton',
            ),
        )
        self.assertIn(
            "display: none",
            _css_block(
                styles,
                '[data-moo-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-skeleton__line',
            ),
        )
        self.assertIn("position: absolute", _css_block(styles, ".sidebar-menu-item--has-action > .sidebar-menu-badge"))

    def test_sidebar_catalog_page_uses_distinct_demo_target(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/sidebar.html")
        self.assertEqual(page.count('id="catalog-sidebar"'), 1)
        self.assertEqual(page.count('id="components-sidebar-demo"'), 1)
        self.assertIn('aria-controls="components-sidebar-demo"', page)
        self.assertEqual(page.count('class="moo-example"'), 1)

    def test_sidebar_catalog_page_keeps_shell_example_before_reference_sections(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/sidebar.html")

        positions = [
            page.index('id="usage"'),
            page.index('id="app-shell-title"'),
            page.index('id="composition"'),
            page.index('id="sidebar-api-reference"'),
            page.index('id="usesidebar"'),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("SidebarProvider", page)
        self.assertIn("<table", page)
        self.assertIn("<th scope=\"col\">Macro</th>", page)
        self.assertIn("<th scope=\"col\">Purpose</th>", page)

    def test_sidebar_catalog_page_documents_public_macro_reference(self) -> None:
        source = (ROOT / "src/pages/components/sidebar.html.jinja").read_text(
            encoding="utf-8"
        )
        public_macros = (
            "sidebar_provider()",
            "sidebar()",
            "sidebar_input()",
            "sidebar_header()",
            "sidebar_footer()",
            "sidebar_separator()",
            "sidebar_content()",
            "sidebar_group()",
            "sidebar_group_label()",
            "sidebar_group_action()",
            "sidebar_group_content()",
            "sidebar_menu()",
            "sidebar_menu_item()",
            "sidebar_menu_button()",
            "sidebar_menu_action()",
            "sidebar_menu_badge()",
            "sidebar_menu_skeleton()",
            "sidebar_menu_sub()",
            "sidebar_menu_sub_item()",
            "sidebar_menu_sub_button()",
            "sidebar_trigger()",
            "sidebar_rail()",
            "sidebar_inset()",
        )

        for macro in public_macros:
            with self.subTest(macro=macro):
                self.assertIn(f'"name": "{macro}"', source)

        self.assertNotIn("SidebarBrandMark", source)
        self.assertIn("sidebar_brand_mark", source)
        self.assertIn(
            'sidebar_menu_item(extra_class="sidebar-menu-item--has-action")',
            source,
        )
        self.assertIn(
            "sidebar_group_content()",
            source,
        )
        self.assertEqual(source.count("render_example("), 1)

    def test_sidebar_catalog_page_documents_sidebar_state_mapping_without_fake_hook(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        page = self.read_output("components/sidebar.html")
        self.assertIn("useSidebar", page)
        self.assertIn("data-moo-sidebar-state", page)
        self.assertIn("static/js/preview.js", page)
        self.assertIn("runtime mapping", page)
        self.assertNotIn("useSidebar()", page)

        preview_js = self.read_output("assets/js/preview.js")
        self.assertTrue(
            "dataset.mooSidebarState" in preview_js
            or "data-moo-sidebar-state" in preview_js,
            "Sidebar runtime state should be controlled in static/js/preview.js",
        )

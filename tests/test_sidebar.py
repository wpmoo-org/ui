from __future__ import annotations

import re

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase


def _css_block(styles: str, selector: str) -> str:
    # Brace-depth aware so a rule containing Sass interpolation (`#{...}`) or
    # any other nested `{}` pair doesn't truncate the match at the wrong `}`.
    match = re.search(rf"{re.escape(selector)}\s*\{{", styles)
    if not match:
        raise AssertionError(f"Missing CSS rule for selector: {selector}")
    start = match.end()
    depth = 1
    for index in range(start, len(styles)):
        if styles[index] == "{":
            depth += 1
        elif styles[index] == "}":
            depth -= 1
            if depth == 0:
                return styles[start:index]
    raise AssertionError(f"Unbalanced braces for selector: {selector}")


class SidebarTests(CatalogTestCase):
    def render_sidebar(self, source: str) -> str:
        template = create_environment().from_string(
            '{% from "components/sidebar.html.jinja" import '
            'sidebar, sidebar_content, sidebar_group_label, sidebar_input, '
            'sidebar_menu_button, sidebar_menu_item, '
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
            (
                'sidebar_menu_button("Button", dropdown_offset="0,10")',
                "Sidebar menu button dropdown_offset requires dropdown=true",
            ),
            ('sidebar_group_action(aria_label="")', "Sidebar group action aria-label is required"),
            (
                'sidebar_menu_item(dropdown=true, dropdown_direction="sideways")',
                "Unknown sidebar dropdown direction: sideways",
            ),
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
        self.assertIn(".sidebar-menu-item:has(> .sidebar-menu-badge) > .sidebar-menu-button", styles)
        self.assertIn(".sidebar-group:has(.sidebar-group-action) .sidebar-group-label", styles)
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
        self.assertIn("position: absolute", _css_block(styles, ".sidebar-menu-badge"))

    def test_sidebar_group_action_and_menu_badge_position_without_extra_classes(self) -> None:
        # Regression coverage: sidebar_group_action and sidebar_menu_badge must
        # overlay their trailing slot in their own documented default usage,
        # as a sibling of sidebar_group_label / sidebar_menu_button, not only
        # when an extra `--has-action` class is added by the consumer.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()

        self.assertIn("position: relative", _css_block(styles, ".sidebar-group"))
        self.assertIn("position: absolute", _css_block(styles, ".sidebar-group-action"))
        self.assertIn("position: absolute", _css_block(styles, ".sidebar-menu-badge"))
        self.assertNotIn("margin-inline-start: auto", _css_block(styles, ".sidebar-group-action"))
        self.assertNotIn("margin-inline-start: auto", _css_block(styles, ".sidebar-menu-badge"))

    def test_sidebar_group_action_renders_beside_group_label(self) -> None:
        output = self.render_sidebar(
            """
            {% call sidebar_group_content() %}
              {{ sidebar_group_label("Application") }}
              {{ sidebar_group_action(icon="plus", aria_label="Add project") }}
            {% endcall %}
            """
        )

        label_index = output.index('data-slot="sidebar-group-label"')
        action_index = output.index('data-slot="sidebar-group-action"')
        self.assertLess(label_index, action_index)

    def test_sidebar_menu_badge_renders_beside_menu_button_without_has_action(self) -> None:
        output = self.render_sidebar(
            """
            {% call sidebar_menu_item() %}
              {{ sidebar_menu_button("Inbox", href="#") }}
              {{ sidebar_menu_badge("24") }}
            {% endcall %}
            """
        )

        self.assertIn('data-slot="sidebar-menu-badge"', output)
        self.assertNotIn("sidebar-menu-item--has-action", output)

    def test_sidebar_menu_action_and_badge_do_not_share_the_same_trailing_slot(self) -> None:
        # Regression coverage: a menu item can combine a trailing action with
        # a badge (e.g. an unread count beside a "..." overflow menu). Both
        # default to the same inset-inline-end slot, so the combined case
        # must shift the badge inward instead of overlapping the action. The
        # combination is auto-detected via :has() — no extra class required.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()

        base_badge_end = _css_block(styles, ".sidebar-menu-badge")
        action_end = _css_block(styles, ".sidebar-menu-action")
        combined_badge_end = _css_block(
            styles, ".sidebar-menu-item:has(> .sidebar-menu-action) > .sidebar-menu-badge"
        )

        self.assertIn("inset-inline-end: $spacer * 0.25", base_badge_end)
        self.assertIn("inset-inline-end: $spacer * 0.25", action_end)
        self.assertIn("inset-inline-end: $spacer * 2", combined_badge_end)
        self.assertIn(
            "z-index: 2",
            _css_block(styles, ".sidebar-menu-action:has(> [data-popper-placement])"),
        )
        self.assertIn(
            "padding-inline-end: $spacer * 4.5",
            _css_block(
                styles,
                ".sidebar-menu-item:has(> .sidebar-menu-action):has(> .sidebar-menu-badge) > .sidebar-menu-button",
            ),
        )
        self.assertNotIn("sidebar-menu-item--has-action", styles)

    def test_sidebar_menu_action_and_badge_compose_without_overlap(self) -> None:
        # No extra_class needed: the action's own presence is what the CSS
        # detects, so a public consumer combining these two macros gets
        # correct positioning without having to know about any styling hook.
        output = self.render_sidebar(
            """
            {% call sidebar_menu_item() %}
              {{ sidebar_menu_button("Inbox", href="#") }}
              {{ sidebar_menu_badge("24") }}
              {% call sidebar_menu_action(aria_label="Inbox actions") %}
                <span>Archive</span>
              {% endcall %}
            {% endcall %}
            """
        )

        self.assertIn('data-slot="sidebar-menu-badge"', output)
        self.assertIn('data-slot="sidebar-menu-action"', output)
        self.assertNotIn("sidebar-menu-item--has-action", output)

    def test_sidebar_menu_item_supports_dropend_profile_menus(self) -> None:
        output = self.render_sidebar(
            """
            {% call sidebar_menu_item(dropdown=true, dropdown_direction="dropend", extra_class="sidebar-menu-item--account") %}
              {{ sidebar_menu_button("Moo Admin", dropdown=true, dropdown_offset="0,4", extra_class="sidebar-menu-button--account") }}
            {% endcall %}
            """
        )

        self.assertIn('class="sidebar-menu-item dropend sidebar-menu-item--account"', output)
        self.assertIn("sidebar-menu-button--account", output)
        self.assertIn('data-bs-offset="0,4"', output)
        self.assertNotIn('class="sidebar-menu-item dropdown dropend"', output)

    def test_sidebar_account_dropdown_open_state_is_visible(self) -> None:
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()

        open_account = _css_block(
            styles, '.sidebar-menu-button--account[aria-expanded="true"]'
        )

        self.assertIn("background: var(--moo-sidebar-accent)", open_account)
        self.assertIn("color: var(--moo-sidebar-foreground)", open_account)
        account_item = _css_block(styles, ".sidebar-menu-item--account")
        account_button = _css_block(styles, ".sidebar-menu-item--account > .sidebar-menu-button--account")
        self.assertIn("padding-inline: 0", account_item)
        self.assertIn("height: $spacer * 3", account_button)
        self.assertIn("min-height: $spacer * 3", account_button)
        self.assertIn("padding: $spacer * 0.5", account_button)
        account_menu = _css_block(styles, ".sidebar-footer .sidebar-account-menu")
        self.assertIn("width: 100%", account_menu)
        self.assertIn("min-width: 100%", account_menu)
        self.assertIn("padding: $spacer * 0.25", account_menu)
        self.assertIn("border-radius: var(--bs-border-radius-lg)", account_menu)
        self.assertIn("box-shadow: var(--bs-box-shadow)", account_menu)
        self.assertIn("min-width: 0", _css_block(styles, ".sidebar-account-menu__header"))
        account_menu_item = _css_block(styles, ".sidebar-account-menu__item")
        self.assertIn("min-height: $spacer * 2", account_menu_item)
        self.assertIn("padding: $spacer * 0.375 $spacer * 0.5", account_menu_item)
        self.assertIn("line-height: $line-height-sm", account_menu_item)
        self.assertIn(
            "margin: $spacer * 0.25 0",
            _css_block(styles, ".sidebar-account-menu__divider"),
        )

    def test_sidebar_floating_variant_detaches_the_surface_with_a_bordered_card(self) -> None:
        # Regression coverage: sidebar(variant="floating") accepted the enum
        # value but produced no visual difference from the default variant.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()

        floating = _css_block(styles, '.sidebar[data-variant="floating"] .sidebar-inner')
        self.assertIn("margin: $spacer * 0.5", floating)
        self.assertIn("border:", floating)
        self.assertIn("border-radius:", floating)
        self.assertIn("box-shadow:", floating)
        self.assertIn(
            "height: calc(100%",
            _css_block(
                styles,
                '.sidebar-wrapper--contained .sidebar[data-variant="floating"] .sidebar-inner',
            ),
        )

    def test_sidebar_floating_variant_inner_width_does_not_overflow_the_column(self) -> None:
        # Regression coverage: the base .sidebar-inner rule sets width: 100%;
        # adding a margin on top of that (without resetting width) makes the
        # card's border box extend past the fixed-width .sidebar column by
        # the margin amount on each side.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()
        floating = _css_block(styles, '.sidebar[data-variant="floating"] .sidebar-inner')
        self.assertIn("width: auto", floating)

    def test_sidebar_inset_variant_turns_main_content_into_a_floating_card(self) -> None:
        # Regression coverage: sidebar(variant="inset") accepted the enum
        # value but produced no visual difference from the default variant.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()

        self.assertIn(
            "background: var(--moo-sidebar)",
            _css_block(styles, '.sidebar-wrapper:has(.sidebar[data-variant="inset"])'),
        )
        inset_content = _css_block(
            styles, '.sidebar-wrapper:has(.sidebar[data-variant="inset"]) .sidebar-inset'
        )
        self.assertIn("margin: $spacer * 0.5", inset_content)
        self.assertIn("margin-inline-start: 0", inset_content)
        self.assertIn("border-radius:", inset_content)
        self.assertIn("box-shadow:", inset_content)
        self.assertIn(
            "margin-inline-start: $spacer * 0.5",
            _css_block(
                styles,
                '.sidebar-wrapper[data-moo-sidebar-state="collapsed"]:has(.sidebar[data-variant="inset"]) .sidebar-inset',
            ),
        )

    def test_sidebar_inset_variant_is_side_aware_for_a_right_sidebar(self) -> None:
        # Regression coverage: side="right" is an accepted, styled sidebar
        # position, so combining it with variant="inset" must flush the
        # content card against the end side, not the start side the
        # left-sidebar default assumes.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()

        right_inset = _css_block(
            styles,
            '.sidebar-wrapper:has(.sidebar[data-variant="inset"][data-side="right"]) .sidebar-inset',
        )
        self.assertIn("margin-inline-end: 0", right_inset)
        self.assertIn("margin-inline-start: $spacer * 0.5", right_inset)
        self.assertIn(
            "margin-inline-end: $spacer * 0.5",
            _css_block(
                styles,
                '.sidebar-wrapper[data-moo-sidebar-state="collapsed"]:has(.sidebar[data-variant="inset"][data-side="right"]) .sidebar-inset',
            ),
        )

    def test_sidebar_variant_decoration_is_scoped_to_desktop(self) -> None:
        # The mobile offcanvas drawer ignores variant styling, matching
        # shadcn's own md:-prefixed scoping, so both new blocks must live
        # inside the same desktop-only breakpoint as the icon-collapse rules.
        styles = ROOT.joinpath("scss/components/_sidebar.scss").read_text()
        up_lg_blocks = re.findall(
            r"@include media-breakpoint-up\(lg\)\s*\{(.*?)\n\}", styles, re.DOTALL
        )
        combined = "\n".join(up_lg_blocks)
        self.assertIn('.sidebar[data-variant="floating"] .sidebar-inner', combined)
        self.assertIn('.sidebar-wrapper:has(.sidebar[data-variant="inset"])', combined)

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
            page.index('assets/images/sidebar-structure.webp'),
            page.index('id="sidebar-api-reference"'),
            page.index('id="usesidebar"'),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("SidebarProvider", page)
        self.assertIn("<table", page)
        self.assertIn("<th scope=\"col\">Macro</th>", page)
        self.assertIn("<th scope=\"col\">Purpose</th>", page)
        self.assertIn("Diagram showing sidebar_provider", page)
        self.assertTrue((DIST / "assets/images/sidebar-structure.webp").is_file())

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
        # The action-bearing Projects rows document the composable pattern
        # with no styling hook required (positioning is auto-detected).
        self.assertIn("sidebar_menu_action(aria_label=", source)
        self.assertNotIn("sidebar-menu-item--has-action", source)
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

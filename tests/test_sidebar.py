from __future__ import annotations

import re
from html import unescape

from build import create_environment
from tests.helpers import DIST, ROOT, CatalogTestCase, read_scss_aggregate


SIDEBAR_JS = ROOT / "src/js/components/sidebar.js"
CATALOG_JS = ROOT / "site/src/js/catalog/index.js"
SIDEBAR_SCSS = ROOT / "scss/components/_sidebar.scss"


def read_sidebar_styles() -> str:
    return read_scss_aggregate(SIDEBAR_SCSS, "components/sidebar")


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
            'sidebar_menu_sub_button, sidebar_menu_sub_item, sidebar_separator, sidebar_provider, '
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
        self.assertIn('data-sidebar-key="catalog-shell"', output)
        self.assertIn('id="catalog-sidebar"', output)
        self.assertIn('aria-label="Catalog navigation"', output)
        self.assertIn('data-sidebar-trigger', output)
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
        self.assertIn('data-sidebar-tooltip="Button"', output)
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
        styles = read_sidebar_styles()
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
            "[data-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-group-action",
            styles,
        )
        self.assertIn(
            "[data-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-menu-badge",
            styles,
        )
        self.assertIn(
            "[data-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-menu-skeleton",
            styles,
        )
        self.assertIn(
            "[data-sidebar-state=\"collapsed\"] .sidebar[data-collapsible=\"icon\"] .sidebar-menu-skeleton__line",
            styles,
        )

    def test_sidebar_group_content_is_neutral_and_inline_modifier_is_scoped(self) -> None:
        styles = read_sidebar_styles()
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
                '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-skeleton',
            ),
        )
        self.assertIn(
            "display: none",
            _css_block(
                styles,
                '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-skeleton__line',
            ),
        )
        self.assertIn("position: absolute", _css_block(styles, ".sidebar-menu-badge"))

    def test_sidebar_menu_sub_item_badge_reserves_trailing_space(self) -> None:
        styles = read_sidebar_styles()

        output = self.render_sidebar(
            """
            {% call sidebar_menu_sub_item() %}
              {{ sidebar_menu_button("Pending review", href="#") }}
              {{ sidebar_menu_badge("3", variant="secondary") }}
            {% endcall %}
            """
        )

        self.assertIn('class="sidebar-menu-sub-item"', output)
        self.assertIn('data-slot="sidebar-menu-badge"', output)
        self.assertIn("position: relative", _css_block(styles, ".sidebar-menu-sub-item"))
        self.assertIn(
            "padding-inline-end: $spacer * 2.5",
            _css_block(
                styles,
                ".sidebar-menu-sub-item:has(> .sidebar-menu-badge) > .sidebar-menu-button",
            ),
        )

    def test_collapsed_sidebar_submenus_render_as_side_flyouts(self) -> None:
        styles = read_sidebar_styles()

        flyout = _css_block(
            styles,
            ".sidebar-menu-flyout",
        )
        collapsed_inset = _css_block(
            styles,
            '.sidebar-wrapper[data-sidebar-state="collapsed"] .sidebar-inset',
        )
        flyout_layer = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"]:has(.sidebar-menu-button[data-bs-toggle="dropdown"][aria-expanded="true"])',
        )
        flyout_text = _css_block(
            styles,
            ".sidebar-menu-flyout .sidebar-menu-button__text",
        )
        flyout_badge = _css_block(
            styles,
            ".sidebar-menu-flyout .sidebar-menu-badge",
        )

        self.assertIn("position: fixed", flyout)
        self.assertIn("z-index: $zindex-dropdown", flyout)
        self.assertIn("position: relative", collapsed_inset)
        self.assertIn("z-index: 0", collapsed_inset)
        self.assertIn("z-index: $zindex-dropdown", flyout_layer)
        self.assertIn("inset-inline-start: var(--moo-sidebar-flyout-inline-start)", flyout)
        self.assertIn("inset-block-start: var(--moo-sidebar-flyout-block-start)", flyout)
        self.assertIn("min-width: $spacer * 10", flyout)
        self.assertIn("list-style: none", flyout)
        self.assertIn("background: var(--moo-surface)", flyout)
        self.assertIn("box-shadow: var(--bs-box-shadow)", flyout)
        self.assertIn("display: flex", flyout)
        self.assertIn("display: grid", flyout_text)
        self.assertIn("display: flex !important", flyout_badge)

    def test_sidebar_group_action_and_menu_badge_position_without_extra_classes(self) -> None:
        # Regression coverage: sidebar_group_action and sidebar_menu_badge must
        # overlay their trailing slot in their own documented default usage,
        # as a sibling of sidebar_group_label / sidebar_menu_button, not only
        # when an extra `--has-action` class is added by the consumer.
        styles = read_sidebar_styles()

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
        styles = read_sidebar_styles()

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
        styles = read_sidebar_styles()

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
        self.assertIn("width: auto", account_menu)
        self.assertIn("min-width: var(--moo-dropdown-sidebar-min-width)", account_menu)
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
        collapsed_account_hover = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-item--account > .sidebar-menu-button--account:hover',
        )
        collapsed_account_open = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-item--account > .sidebar-menu-button--account[aria-expanded="true"]',
        )
        collapsed_account_button = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-item--account > .sidebar-menu-button--account',
        )
        collapsed_account_focus = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-item--account > .sidebar-menu-button--account:focus-visible',
        )
        self.assertIn("background: transparent", collapsed_account_hover)
        self.assertIn("background: transparent", collapsed_account_open)
        self.assertIn("outline: 0", collapsed_account_open)
        self.assertIn("box-shadow: none", collapsed_account_open)
        self.assertIn("padding: 0", collapsed_account_button)
        self.assertIn("overflow: visible", collapsed_account_button)
        self.assertIn("background: transparent", collapsed_account_focus)
        self.assertIn("outline: 0", collapsed_account_focus)
        self.assertIn("box-shadow: none", collapsed_account_focus)

    def test_sidebar_avatar_uses_default_avatar_shape(self) -> None:
        styles = read_sidebar_styles()

        self.assertNotIn(".sidebar-avatar {", styles)
        self.assertNotIn(".sidebar-avatar > img", styles)
        self.assertNotIn(".sidebar-avatar > .avatar-fallback", styles)

    def test_sidebar_workspace_dropdown_uses_identity_trigger_contract(self) -> None:
        styles = read_sidebar_styles()
        dropdown_styles = ROOT.joinpath("scss/components/_dropdown.scss").read_text()

        identity_cursors = _css_block(
            styles,
            ".sidebar-menu-button.sidebar-menu-button--account,\n.sidebar-menu-button.sidebar-menu-button--workspace",
        )
        collapsed_workspace_hover = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-button--workspace:hover',
        )
        collapsed_workspace_open = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-button--workspace[aria-expanded="true"]',
        )
        collapsed_workspace_focus = _css_block(
            styles,
            '[data-sidebar-state="collapsed"] .sidebar[data-collapsible="icon"] .sidebar-menu-button--workspace:focus-visible',
        )
        collapsed_header_dropdown = _css_block(
            dropdown_styles,
            '[data-slot="sidebar-header"] [data-sidebar-dropdown-positioned] > .dropdown-menu',
        )

        self.assertIn("cursor: default", identity_cursors)
        self.assertIn("background: transparent", collapsed_workspace_hover)
        self.assertIn("background: transparent", collapsed_workspace_open)
        self.assertIn("outline: 0", collapsed_workspace_open)
        self.assertIn("box-shadow: none", collapsed_workspace_open)
        self.assertIn("background: transparent", collapsed_workspace_focus)
        self.assertIn("outline: 0", collapsed_workspace_focus)
        self.assertIn("box-shadow: none", collapsed_workspace_focus)
        self.assertIn("position: fixed !important", collapsed_header_dropdown)
        self.assertIn("z-index: $zindex-dropdown", collapsed_header_dropdown)
        self.assertIn("width: var(--moo-dropdown-sidebar-min-width)", collapsed_header_dropdown)
        self.assertIn("min-width: var(--moo-dropdown-sidebar-min-width)", collapsed_header_dropdown)
        self.assertIn(
            "inset-inline-start: var(--moo-sidebar-dropdown-inline-start) !important",
            collapsed_header_dropdown,
        )
        self.assertIn(
            "inset-block-start: var(--moo-sidebar-dropdown-block-start) !important",
            collapsed_header_dropdown,
        )
        self.assertIn("transform: none !important", collapsed_header_dropdown)

    def test_sidebar_identity_dropdowns_stack_inside_small_mobile_drawer(self) -> None:
        dropdown_styles = ROOT.joinpath("scss/components/_dropdown.scss").read_text()

        self.assertIn("@include media-breakpoint-down(sm)", dropdown_styles)
        shared_dropdown = _css_block(
            dropdown_styles,
            '[data-slot="sidebar-header"] .dropend > .dropdown-menu,\n  [data-slot="sidebar-footer"] .dropend > .dropdown-menu',
        )

        self.assertIn("left: 0 !important", shared_dropdown)
        self.assertIn("right: 0 !important", shared_dropdown)
        self.assertIn("min-width: 100%", shared_dropdown)
        self.assertIn("transform: none !important", shared_dropdown)

        self.assertIn(
            '[data-slot="sidebar-header"] .dropend > .dropdown-menu {\n'
            "    top: calc(100% + #{$spacer * 0.25}) !important;\n"
            "    bottom: auto !important;",
            dropdown_styles,
        )
        self.assertIn(
            '[data-slot="sidebar-footer"] .dropend > .dropdown-menu {\n'
            "    top: auto !important;\n"
            "    bottom: calc(100% + #{$spacer * 0.25}) !important;",
            dropdown_styles,
        )

    def test_sidebar_floating_variant_detaches_the_surface_with_a_bordered_card(self) -> None:
        # Regression coverage: sidebar(variant="floating") accepted the enum
        # value but produced no visual difference from the default variant.
        styles = read_sidebar_styles()

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
        styles = read_sidebar_styles()
        floating = _css_block(styles, '.sidebar[data-variant="floating"] .sidebar-inner')
        self.assertIn("width: auto", floating)

    def test_sidebar_inset_variant_turns_main_content_into_a_floating_card(self) -> None:
        # Regression coverage: sidebar(variant="inset") accepted the enum
        # value but produced no visual difference from the default variant.
        styles = read_sidebar_styles()

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
                '.sidebar-wrapper[data-sidebar-state="collapsed"]:has(.sidebar[data-variant="inset"]) .sidebar-inset',
            ),
        )

    def test_sidebar_inset_variant_is_side_aware_for_a_right_sidebar(self) -> None:
        # Regression coverage: side="right" is an accepted, styled sidebar
        # position, so combining it with variant="inset" must flush the
        # content card against the end side, not the start side the
        # left-sidebar default assumes.
        styles = read_sidebar_styles()

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
                '.sidebar-wrapper[data-sidebar-state="collapsed"]:has(.sidebar[data-variant="inset"][data-side="right"]) .sidebar-inset',
            ),
        )

    def test_sidebar_variant_decoration_is_scoped_to_desktop(self) -> None:
        # The mobile offcanvas drawer ignores variant styling, matching
        # the design reference's own md:-prefixed scoping, so both new
        # blocks must live inside the same desktop-only breakpoint as the
        # icon-collapse rules.
        styles = read_sidebar_styles()
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
        self.assertIn('data-moo-block-frame-shell', page)
        self.assertIn('src="../../blocks/previews/sidebar-floating/"', page)
        self.assertIn('title="Application shell preview"', page)
        self.assertIn("components-sidebar-floating-demo", page)
        # Sidebar documents one full application-shell example; RTL is not part of this component contract.
        self.assertEqual(page.count('class="moo-example"'), 1)

    def test_sidebar_catalog_page_keeps_shell_example_before_reference_sections(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        page = self.read_output("components/sidebar.html")

        positions = [
            page.index('id="usage"'),
            page.index('id="application-shell"'),
            page.index('id="composition"'),
            page.index('assets/images/sidebar-structure.webp'),
            page.index('id="sidebar-html-anatomy"'),
            page.index('id="sidebar-javascript"'),
            page.index('id="sidebar-state"'),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("SidebarProvider", page)
        self.assertIn("<table", page)
        self.assertIn("<th scope=\"col\">Selector</th>", page)
        self.assertIn("<th scope=\"col\">Purpose</th>", page)
        self.assertTrue((DIST / "assets/images/sidebar-structure.webp").is_file())

    def test_sidebar_catalog_page_documents_public_html_anatomy(self) -> None:
        source = (ROOT / "site/src/pages/components/sidebar.html.jinja").read_text(
            encoding="utf-8"
        )
        shell_source = (ROOT / "site/src/blocks/sidebar_shell.html.jinja").read_text(
            encoding="utf-8"
        )
        example_source = source + shell_source
        public_hooks = (
            ".sidebar-wrapper",
            ".sidebar",
            "[data-sidebar-trigger]",
            "[data-sidebar-rail]",
            "[data-slot=\"sidebar-content\"]",
            "[data-slot=\"sidebar-menu-button\"]",
            ".sidebar-menu-sub.collapse",
            ".sidebar-inset",
        )

        for hook in public_hooks:
            with self.subTest(hook=hook):
                self.assertIn(hook, source)

        self.assertNotIn("SidebarBrandMark", source)
        self.assertNotIn("sidebar_provider()", source)
        self.assertNotIn("sidebar_header()", source)
        self.assertNotIn("sidebar_menu_button()", source)
        self.assertIn("sidebar_brand_mark", example_source)
        # The action-bearing Projects rows document the composable pattern
        # with no styling hook required (positioning is auto-detected).
        self.assertIn("sidebar_menu_action(aria_label=", example_source)
        self.assertNotIn("sidebar-menu-item--has-action", example_source)
        self.assertEqual(source.count("render_block_example("), 1)

    def test_sidebar_catalog_page_documents_sidebar_state_mapping_without_fake_hook(self) -> None:
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)

        page = self.read_output("components/sidebar.html")
        page_text = unescape(re.sub(r"<[^>]+>", "", page))
        self.assertIn("useSidebar", page)
        self.assertIn("data-sidebar-state", page)
        self.assertIn("@wpmoo/ui/sidebar.js", page)
        self.assertIn("Sidebar.getOrCreateInstance(element)", page_text)
        self.assertIn("sidebar.dispose()", page_text)
        self.assertNotIn("static/js/preview.js", page)
        self.assertNotIn("useSidebar()", page)

        sidebar_js = self.read_output("assets/js/components/sidebar.js")
        self.assertIn("dataset.sidebarState", sidebar_js)
        catalog_js = self.read_output("assets/js/catalog/index.js")
        self.assertRegex(
            catalog_js,
            r'import Sidebar from "\.\./components/sidebar\.js(?:\?v=[0-9a-f]+)?";',
        )
        self.assertIn("Sidebar.getOrCreateInstance(element);", catalog_js)
        self.assertNotIn("dataset.sidebarState", catalog_js)

    def test_public_sidebar_module_owns_instance_lifecycle(self) -> None:
        source = SIDEBAR_JS.read_text(encoding="utf-8")
        catalog = CATALOG_JS.read_text(encoding="utf-8")

        self.assertIn("export default class Sidebar", source)
        self.assertIn("static getInstance(element)", source)
        self.assertIn("static getOrCreateInstance(element, config = {})", source)
        self.assertIn("instances.set(element, this);", source)
        self.assertIn("instances.delete(this._element);", source)
        self.assertIn("removeEventListener(type, handler, options)", source)
        self.assertIn("this._directionObserver?.disconnect();", source)
        self.assertIn("this._offcanvas?.dispose();", source)
        self.assertIn(
            'import Sidebar from "../../../../src/js/components/sidebar.js";',
            catalog,
        )
        self.assertIn("Sidebar.getOrCreateInstance(element);", catalog)
        self.assertNotIn("SIDEBAR_STORAGE_PREFIX", catalog)
        self.assertNotIn("openSidebarFlyout", catalog)

    def test_catalog_hands_off_persisted_state_before_sidebar_content(self) -> None:
        source = SIDEBAR_JS.read_text(encoding="utf-8")
        styles = read_sidebar_styles()
        catalog_styles = (ROOT / "site/scss/catalog/_shell.scss").read_text(
            encoding="utf-8"
        )
        base = (ROOT / "site/src/layouts/base.html.jinja").read_text(encoding="utf-8")
        layout = (ROOT / "site/src/layouts/catalog.html.jinja").read_text(encoding="utf-8")

        restore_index = source.index("this._restoreState();")
        ready_index = source.index('setAttribute("data-sidebar-ready", "")')
        self.assertLess(restore_index, ready_index)
        self.assertNotIn("requestAnimationFrame", source[restore_index:ready_index])
        self.assertIn('window.localStorage.getItem("moo-sidebar:catalog-shell")', base)
        self.assertLess(
            layout.index('{% call sidebar_provider(key="catalog-shell") %}'),
            layout.index("shell.dataset.sidebarState = state"),
        )
        self.assertLess(
            layout.index("shell.dataset.sidebarState = state"),
            layout.index('{% include "shell/sidebar.html.jinja" %}'),
        )
        self.assertIn('removeAttribute("data-sidebar-ready")', source)
        self.assertNotIn("transition:", _css_block(styles, ".sidebar"))
        self.assertRegex(
            styles,
            r"@include media-breakpoint-up\(lg\)\s*\{\s*"
            r"\.sidebar\s*\{[^}]*transition:\s*flex-basis",
        )
        self.assertNotIn("moo-sidebar-catalog-state", styles)
        self.assertRegex(
            catalog_styles,
            r"@media \(prefers-reduced-motion: reduce\)\s*\{\s*"
            r"\.moo-catalog \.sidebar\s*\{\s*transition:\s*none;",
        )

    def test_sidebar_shortcut_ignores_editable_targets(self) -> None:
        source = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn('target.matches("input, textarea, select")', source)
        self.assertIn("target.isContentEditable", source)
        self.assertIn("event.defaultPrevented", source)
        self.assertIn("event.isComposing", source)
        self.assertIn("isEditable ||", source)

    def test_mobile_offcanvas_restores_focus_to_its_trigger(self) -> None:
        source = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn("this._offcanvasTrigger = control;", source)
        self.assertIn('this._sidebar, "hidden.bs.offcanvas"', source)
        self.assertIn("const trigger = this._offcanvasTrigger;", source)
        self.assertIn("this._offcanvasTrigger = null;", source)
        self.assertIn("trigger?.isConnected", source)
        self.assertIn("trigger.focus();", source)

    def test_sidebar_dropdown_trigger_disables_collapsed_tooltip_while_open(self) -> None:
        script = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn("_disposeTooltip", script)
        self.assertIn('show.bs.dropdown', script)
        self.assertIn('hidden.bs.dropdown', script)
        self.assertIn('[data-bs-toggle="dropdown"][data-sidebar-tooltip]', script)

    def test_sidebar_identity_triggers_skip_collapsed_tooltips(self) -> None:
        script = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn('closest(".sidebar-menu-item--account")', script)
        self.assertIn('classList.contains("sidebar-menu-button--workspace")', script)
        self.assertIn("return;", script)

    def test_sidebar_disclosure_triggers_use_collapsed_flyout_instead_of_tooltip(self) -> None:
        script = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn("_openFlyout", script)
        self.assertIn("_closeFlyouts", script)
        self.assertIn('this._listen(this._window, "click"', script)
        self.assertIn("cloneNode(true)", script)
        self.assertIn("sidebar-menu-flyout", script)
        self.assertIn('flyout.removeAttribute("style")', script)
        self.assertIn("this._flyoutOwner === item", script)
        self.assertIn("sidebarFlyout", script)
        self.assertIn("sidebar-menu-item--flyout-open", script)
        self.assertIn('querySelector(":scope > .sidebar-menu-sub")', script)
        self.assertIn("stopImmediatePropagation", script)
        self.assertIn("this._flyout.contains(event.target)", script)
        self.assertIn("this._resetFlyoutTrigger(this._flyoutOwner, false)", script)
        self.assertIn("this._closeDropdowns()", script)
        self.assertNotIn('document.addEventListener("pointerover"', script)
        self.assertNotIn('document.addEventListener("focusin"', script)

    def test_sidebar_overlays_close_siblings_before_opening(self) -> None:
        script = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn("_closeDropdowns(exceptControl = null)", script)
        self.assertIn("control === exceptControl", script)
        self.assertIn("Dropdown.getOrCreateInstance(control).hide()", script)
        self.assertIn("this._closeDropdowns(", script)
        self.assertIn("this._positionDropdown(control)", script)

    def test_sidebar_workspace_dropdown_is_positioned_from_collapsed_icon_rail(self) -> None:
        script = SIDEBAR_JS.read_text(encoding="utf-8")

        self.assertIn("_positionDropdown", script)
        self.assertIn("_clearDropdownPosition", script)
        self.assertIn("sidebarDropdownPositioned", script)
        self.assertIn("[data-sidebar-dropdown-positioned]", script)
        self.assertIn("--moo-sidebar-dropdown-inline-start", script)
        self.assertIn("--moo-sidebar-dropdown-block-start", script)
        self.assertIn("rect.bottom + gap", script)

from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/menubar.html.jinja"
PAGE = ROOT / "src/pages/components/menubar.html.jinja"


class MenubarTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Menubar macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def test_menubar_wraps_dropdowns_in_a_bordered_group(self) -> None:
        output = self.render(
            '{% from "components/menubar.html.jinja" import menubar %}'
            '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
            '{% call menubar("Document actions") %}'
            '{% call dropdown("File", variant="ghost") %}'
            '{{ dropdown_item("New document") }}'
            "{% endcall %}"
            "{% endcall %}"
        )
        self.assertIn('role="group"', output)
        self.assertIn('aria-label="Document actions"', output)
        self.assertIn("border", output)
        self.assertIn('class="dropdown">', output)
        self.assertIn("New document", output)

    def test_menubar_does_not_spoof_menubar_or_menuitem_roles(self) -> None:
        output = self.render(
            '{% from "components/menubar.html.jinja" import menubar %}'
            '{% from "components/dropdown_menu.html.jinja" import dropdown, dropdown_item %}'
            '{% call menubar("Document actions") %}'
            '{% call dropdown("File", variant="ghost") %}'
            '{{ dropdown_item("New document") }}'
            "{% endcall %}"
            "{% endcall %}"
        )
        self.assertNotIn('role="menubar"', output)
        self.assertNotIn('role="menuitem"', output)

    def test_requires_aria_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "Menubar aria_label is required"):
            self.render(
                '{% from "components/menubar.html.jinja" import menubar %}'
                '{% call menubar("   ") %}x{% endcall %}'
            )

    def test_supports_extra_class(self) -> None:
        output = self.render(
            '{% from "components/menubar.html.jinja" import menubar %}'
            '{% call menubar("Document actions", extra_class="mb-3") %}x{% endcall %}'
        )
        self.assertIn("mb-3", output)

    def test_page_uses_bootstrap_offset_for_menu_gap(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn('{% set menubar_dropdown_offset = "0,8" %}', source)
        self.assertIn("offset=menubar_dropdown_offset", source)

    def test_open_trigger_state_is_scoped_to_menubar(self) -> None:
        styles = (ROOT / "scss/components/_menubar.scss").read_text(encoding="utf-8")

        self.assertIn(".menubar .dropdown-toggle.show", styles)
        self.assertIn("--bs-btn-color: var(--moo-foreground)", styles)
        self.assertIn("font-weight: $font-weight-medium", styles)

    def test_page_uses_realistic_original_scenarios(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        for distinctive_reference_scenario in (
            "New Tab",
            "New Window",
            "⌘T",
            "Bookmarks Bar",
            "Full URLs",
            "Reload",
            "Force Reload",
            "Andy",
            "Benoit",
            "Luis",
        ):
            self.assertNotIn(
                distinctive_reference_scenario,
                source,
                f"Page reuses the reference's own scenario shape: {distinctive_reference_scenario}",
            )
        for original_scenario in (
            "New document",
            "Export as PDF",
            "Invite teammate",
            "Sidebar",
            "Profile",
        ):
            self.assertIn(original_scenario, source)

    def test_checkbox_and_radio_menus_opt_into_outside_auto_close(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        checkbox_block = source.split('{% set checkbox_example %}')[1].split(
            "{% endset %}"
        )[0]
        radio_block = source.split('{% set radio_example %}')[1].split(
            "{% endset %}"
        )[0]

        self.assertIn('auto_close="outside"', checkbox_block)
        self.assertIn('auto_close="outside"', radio_block)

    def test_page_reuses_ready_checkbox_and_radio_group_macros(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn(
            '{% from "components/checkbox.html.jinja" import checkbox %}', source
        )
        self.assertIn(
            '{% from "components/radio_group.html.jinja" import radio_group %}',
            source,
        )
        self.assertNotIn("menuitemcheckbox", source)
        self.assertNotIn("menuitemradio", source)

    def test_page_documents_the_submenu_gap_without_faking_it(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn("Submenu is not yet supported", source)
        self.assertNotIn("MenubarSub", source)

    def test_page_uses_tabbed_rtl_locales_like_accordion(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertIn('{% from "components/tabs.html.jinja" import tabs %}', source)
        for locale_tab in ("Arabic", "Hebrew", "English"):
            self.assertIn(locale_tab, source)

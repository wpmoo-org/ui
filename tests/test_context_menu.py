from __future__ import annotations

import json
import subprocess

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/context_menu.html.jinja"
PAGE = ROOT / "site/src/pages/components/context-menu.html.jinja"
REGISTRY = ROOT / "src/registry/components.json"
EVIDENCE_INVENTORY = ROOT / "src/certification/evidence-inventory.json"
CONTEXT_MENU_JS = ROOT / "src/js/components/context-menu.js"
CATALOG_JS = ROOT / "site/src/js/catalog/index.js"
CONTEXT_MENU_SCSS = ROOT / "scss/components/_context-menu.scss"
FIXTURE = ROOT / "tests/fixtures/certification/context-menu.html"


class ContextMenuTests(CatalogTestCase):
    def render_context_menu(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Context Menu macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/context_menu.html.jinja" import context_menu %}'
            '{% from "components/dropdown_menu.html.jinja" import dropdown_item, dropdown_divider %}'
            + source
        )
        return " ".join(template.render().split())

    def test_context_menu_renders_bootstrap_native_anatomy(self) -> None:
        output = self.render_context_menu(
            '{% set items %}{{ dropdown_item("Rename") }}{{ dropdown_divider() }}'
            '{{ dropdown_item("Delete", destructive=true) }}{% endset %}'
            '{% call context_menu("ctx-1", "File actions", items) %}'
            "<p>Surface content</p>"
            "{% endcall %}"
        )

        self.assertIn('<div class="context-menu" id="ctx-1">', output)
        self.assertIn(
            '<div class="context-menu-trigger" id="ctx-1-surface" role="button" tabindex="0" '
            'aria-haspopup="menu" aria-expanded="false" aria-controls="ctx-1-menu">',
            output,
        )
        self.assertIn("<p>Surface content</p>", output)
        self.assertIn('data-bs-toggle="dropdown"', output)
        self.assertIn("data-context-menu-fallback", output)
        self.assertIn('aria-label="Open File actions menu"', output)
        self.assertIn(
            '<ul class="dropdown-menu context-menu-menu" id="ctx-1-menu" tabindex="-1" aria-label="File actions">',
            output,
        )
        self.assertIn('class="dropdown-item"', output)
        self.assertRegex(
            output,
            r'<button(?=[^>]*\sclass="dropdown-item"(?:\s|>))'
            r'(?=[^>]*\stype="button"(?:\s|>))'
            r'(?=[^>]*\sdata-variant="destructive"(?:\s|>))[^>]*>',
        )

    def test_context_menu_fallback_uses_ghost_icon_button(self) -> None:
        output = self.render_context_menu(
            '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
            '{% call context_menu("ctx-1", "File actions", items) %}'
            "<p>Surface</p>"
            "{% endcall %}"
        )

        self.assertIn("btn btn-ghost btn-icon-sm", output)
        self.assertNotIn("btn-outline-secondary", output)

    def test_context_menu_two_triggers_share_the_public_trigger_class(self) -> None:
        output = self.render_context_menu(
            '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
            '{% call context_menu("ctx-1", "File actions", items) %}'
            "<p>Surface</p>"
            "{% endcall %}"
        )

        self.assertEqual(output.count("context-menu-trigger"), 2)

    def test_context_menu_surface_does_not_advertise_primary_click(self) -> None:
        source = CONTEXT_MENU_SCSS.read_text(encoding="utf-8")

        self.assertIn(".context-menu-trigger:not([data-context-menu-fallback])", source)
        self.assertIn("cursor: default;", source)

    def test_context_menu_custom_fallback_label(self) -> None:
        output = self.render_context_menu(
            '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
            '{% call context_menu("ctx-1", "File actions", items, fallback_label="More actions") %}'
            "<p>Surface</p>"
            "{% endcall %}"
        )

        self.assertIn('aria-label="More actions"', output)
        self.assertNotIn('aria-label="Open File actions menu"', output)

    def test_context_menu_align_passes_through_to_menu(self) -> None:
        output = self.render_context_menu(
            '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
            '{% call context_menu("ctx-1", "File actions", items, align="end") %}'
            "<p>Surface</p>"
            "{% endcall %}"
        )

        self.assertIn('class="dropdown-menu context-menu-menu dropdown-menu-end"', output)

    def test_context_menu_extra_classes_pass_through(self) -> None:
        output = self.render_context_menu(
            '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
            '{% call context_menu('
            '"ctx-1", "File actions", items, '
            'extra_class="ctx-extra", trigger_class="trigger-extra", menu_class="menu-extra"'
            ") %}"
            "<p>Surface</p>"
            "{% endcall %}"
        )

        self.assertIn('class="context-menu ctx-extra"', output)
        self.assertIn('context-menu-trigger trigger-extra"', output)
        self.assertIn("dropdown-menu context-menu-menu menu-extra", output)

    def test_context_menu_fails_fast_without_id(self) -> None:
        with self.assertRaises(Exception):
            self.render_context_menu(
                '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
                '{% call context_menu("", "File actions", items) %}'
                "<p>Surface</p>"
                "{% endcall %}"
            )

    def test_context_menu_fails_fast_without_label(self) -> None:
        with self.assertRaises(Exception):
            self.render_context_menu(
                '{% set items %}{{ dropdown_item("Rename") }}{% endset %}'
                '{% call context_menu("ctx-1", "", items) %}'
                "<p>Surface</p>"
                "{% endcall %}"
            )

    def test_context_menu_fails_fast_without_items(self) -> None:
        with self.assertRaises(Exception):
            self.render_context_menu(
                '{% call context_menu("ctx-1", "File actions", "") %}'
                "<p>Surface</p>"
                "{% endcall %}"
            )

    def test_context_menu_is_ready_in_catalog_registry(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = next((item for item in registry if item["slug"] == "context-menu"), None)

        self.assertIsNotNone(entry)
        self.assertEqual(entry["label"], "Context Menu")
        self.assertEqual(entry["status"], "ready")

    def test_context_menu_is_no_longer_a_planned_component(self) -> None:
        inventory = json.loads(EVIDENCE_INVENTORY.read_text(encoding="utf-8"))
        planned_slugs = {component["slug"] for component in inventory["plannedComponents"]}
        component_slugs = {component["slug"] for component in inventory["components"]}

        self.assertNotIn("context-menu", planned_slugs)
        self.assertIn("context-menu", component_slugs)
        entry = next(
            component for component in inventory["components"] if component["slug"] == "context-menu"
        )
        self.assertEqual(inventory["profiles"][entry["profile"]]["tier"], 3)

    def test_context_menu_has_t3_evidence(self) -> None:
        phase_three = json.loads(
            (ROOT / "src/certification/phase-3-evidence.json").read_text(encoding="utf-8")
        )
        components = {c["slug"]: c for c in phase_three["components"]}

        self.assertIn("context-menu", components)
        self.assertEqual(components["context-menu"]["tier"], 3)
        self.assertEqual(components["context-menu"]["status"], "backfill-passed")

    def test_public_module_owns_context_menu_behavior_and_lifecycle(self) -> None:
        source = CONTEXT_MENU_JS.read_text(encoding="utf-8")
        catalog = CATALOG_JS.read_text(encoding="utf-8")

        self.assertIn("export default class ContextMenu", source)
        self.assertIn("static getInstance(element)", source)
        self.assertIn("static getOrCreateInstance(element, config = {})", source)
        self.assertIn("dispose()", source)
        self.assertIn("instances.set(element, this);", source)
        self.assertIn("instances.delete(this._element);", source)
        self.assertIn("removeEventListener(type, handler, options)", source)
        self.assertIn('"contextmenu"', source)
        self.assertIn('event.shiftKey && event.key === "F10"', source)
        self.assertIn('event.key === "ContextMenu"', source)
        self.assertIn("_handleFallbackKeydown(event)", source)
        self.assertIn('event.key !== " " && event.key !== "Spacebar"', source)
        self.assertIn('this._open(this._fallback, null, "fallback-keyboard")', source)
        self.assertIn('this._fallback.focus()', source)
        self.assertIn("`${name}.moo.context-menu`", source)
        self.assertIn('this._trigger("show", true)', source)
        self.assertIn('this._trigger("shown")', source)
        self.assertIn('this._trigger("hide", true)', source)
        self.assertIn('this._trigger("hidden")', source)
        self.assertIn('contextMenu: ".context-menu"', catalog)
        self.assertIn(
            'import("../../../../src/js/components/context-menu.js")',
            catalog,
        )
        self.assertIn("({ default: ContextMenu })", catalog)
        self.assertIn("ContextMenu.getOrCreateInstance(element)", catalog)
        self.assertIn("instances.forEach((instance) => instance.dispose())", catalog)

    def test_public_module_import_has_no_document_side_effects(self) -> None:
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "--eval",
                'import("./src/js/components/context-menu.js")',
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_context_menu_page_uses_reference_without_nested_submenu_markup(self) -> None:
        self.assertTrue(PAGE.is_file(), "Context Menu page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertNotIn('"submenu",', source)
        self.assertNotIn('"Submenu",', source)
        self.assertNotIn("context-menu-submenu-trigger", source)
        self.assertNotIn('class="dropend"', source)
        self.assertIn("render_reference(", source)

    def test_context_menu_page_covers_shadcn_flat_example_sections(self) -> None:
        self.assertTrue(PAGE.is_file(), "Context Menu page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        for example_id in (
            "basic",
            "shortcuts",
            "groups",
            "icons",
            "checkboxes",
            "radio",
            "destructive",
            "sides",
        ):
            self.assertIn(f'"{example_id}",', source)

        self.assertIn('align="end"', source)

    def test_fixture_toggle_item_renders_a_real_check_indicator(self) -> None:
        # dropdown_toggle_item() always renders an icon inside
        # .dropdown-item-check__indicator (the CSS only toggles that span's
        # opacity; it never supplies the checkmark itself), so a hand-authored
        # fixture that leaves the indicator empty toggles aria-pressed/.active
        # correctly but never shows anything -- a static parse catches that
        # without needing a full browser run.
        self.assertTrue(FIXTURE.is_file(), "Context Menu certification fixture is missing")
        source = FIXTURE.read_text(encoding="utf-8")
        indicator = source.split('class="dropdown-item-check__indicator"', 1)[1]
        indicator_body = indicator.split(">", 1)[1].split("</span>", 1)[0]

        self.assertIn("<svg", indicator_body)

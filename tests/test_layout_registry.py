from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "src/registry/layouts.json"
COMPONENT_REGISTRY = ROOT / "src/registry/components.json"
SIDEBAR_SOURCE = ROOT / "src/components/sidebar.html.jinja"
LAYOUT_SOURCE_ROOT = ROOT / "src/layouts"
PUBLIC_LAYOUT_SLUGS = {"page", "app"}
REQUIRED_FIELDS = {
    "slug",
    "label",
    "status",
    "description",
    "source",
    "parts",
    "layoutParts",
}
MACRO_PATTERN = re.compile(r"{%[-+]?\s*macro\s+(?P<name>[A-Za-z_]\w*)\s*\(")

# The component registry records component identities, but it does not record
# which helper/anatomy macros are owned by each source file. Freeze that
# recognition rule here so an unregistered layout macro cannot hide in a
# component or include template. A new component-owned macro must therefore be
# reviewed together with this finite allowlist; layout macros must remain in
# the dedicated layout source directory.
COMPONENT_MACROS_BY_FILE = {
    "accordion.html.jinja": {"accordion"},
    "alert.html.jinja": {"alert"},
    "alert_dialog.html.jinja": {"alert_dialog", "alert_dialog_header"},
    "avatar.html.jinja": {"avatar"},
    "badge.html.jinja": {"badge"},
    "breadcrumb.html.jinja": {"breadcrumb"},
    "button.html.jinja": {"icon", "button"},
    "button_group.html.jinja": {"button_group"},
    "card.html.jinja": {"card"},
    "chart.html.jinja": {"chart"},
    "checkbox.html.jinja": {"checkbox"},
    "close_button.html.jinja": {"close_button"},
    "collapsible.html.jinja": {"collapsible"},
    "combobox.html.jinja": {
        "combobox_option_content",
        "combobox_chip",
        "combobox_options",
        "combobox",
    },
    "context_menu.html.jinja": {"context_menu"},
    "datatable.html.jinja": {
        "datatable_bulk_actions",
        "datatable_facet_item",
        "datatable_facet",
        "datatable_search_filter",
        "datatable_column_header",
        "datatable_view_toggle",
        "datatable_column_visibility_menu",
        "datatable_frame_header",
        "datatable",
    },
    "datepicker.html.jinja": {
        "datepicker_label",
        "datepicker_range_label",
        "calendar",
        "datepicker",
        "date_range_picker",
    },
    "dialog.html.jinja": {"dialog", "dialog_header", "dialog_body", "dialog_footer"},
    "dropdown_menu.html.jinja": {
        "dropdown",
        "dropdown_menu",
        "dropdown_item",
        "dropdown_toggle_item",
        "dropdown_header",
        "dropdown_identity",
        "dropdown_divider",
    },
    "field.html.jinja": {
        "form",
        "field",
        "field_description",
        "field_error",
        "field_group",
        "fieldset",
    },
    "input.html.jinja": {"input"},
    "input_group.html.jinja": {
        "input_group",
        "input_group_text",
        "input_group_block_addon",
    },
    "kbd.html.jinja": {"kbd"},
    "menubar.html.jinja": {"menubar"},
    "navigation.html.jinja": {"nav_menu", "nav_item"},
    "pagination.html.jinja": {
        "pagination",
        "pagination_item",
        "_pagination_nav_item",
        "pagination_prev",
        "pagination_next",
        "pagination_ellipsis",
    },
    "popover.html.jinja": {"popover_dismiss_trigger"},
    "progress.html.jinja": {"progress"},
    "radio_group.html.jinja": {"radio_group"},
    "select.html.jinja": {"select"},
    "separator.html.jinja": {"separator"},
    "sheet.html.jinja": {"sheet", "sheet_header", "sheet_body"},
    "sidebar.html.jinja": {
        "sidebar",
        "sidebar_trigger",
        "sidebar_header",
        "sidebar_content",
        "sidebar_input",
        "sidebar_separator",
        "sidebar_footer",
        "sidebar_group",
        "sidebar_group_label",
        "sidebar_group_content",
        "sidebar_menu",
        "sidebar_group_action",
        "sidebar_menu_item",
        "_sidebar_button_body",
        "sidebar_menu_button",
        "sidebar_menu_sub",
        "sidebar_menu_sub_item",
        "sidebar_menu_sub_button",
        "sidebar_menu_action",
        "sidebar_menu_badge",
        "sidebar_menu_skeleton",
        "sidebar_brand_mark",
    },
    "skeleton.html.jinja": {"skeleton"},
    "slider.html.jinja": {"slider", "slider_range"},
    "spinner.html.jinja": {"spinner"},
    "switch.html.jinja": {"switch"},
    "table.html.jinja": {"table", "table_row_actions"},
    "tabs.html.jinja": {"tabs"},
    "textarea.html.jinja": {"textarea"},
    "toast.html.jinja": {"toast_container", "toast", "toast_template"},
    "toggle_group.html.jinja": {"toggle_group"},
    "tooltip.html.jinja": {"tooltip_trigger"},
    "typography.html.jinja": {"typography"},
    "src/includes/field.html.jinja": {"render_field"},
}
COMPONENT_SOURCE_FILES = {
    path for path in COMPONENT_MACROS_BY_FILE if not path.startswith("src/")
}


def _macro_names(path: Path) -> set[str]:
    return {
        match.group("name")
        for match in MACRO_PATTERN.finditer(path.read_text(encoding="utf-8"))
    }


def _unregistered_layout_macro_offenders(root: Path) -> list[str]:
    layout_root = root / "src/layouts"
    component_root = root / "src/components"
    offenders: list[str] = []

    for path in sorted((root / "src").rglob("*.html.jinja")):
        relative = path.relative_to(root).as_posix()
        names = _macro_names(path)
        if path.parent == layout_root:
            allowed = PUBLIC_LAYOUT_SLUGS
        elif path.parent == component_root:
            allowed = set(COMPONENT_MACROS_BY_FILE.get(path.name, ()))
        elif relative == "src/includes/field.html.jinja":
            allowed = COMPONENT_MACROS_BY_FILE[relative]
        else:
            allowed = set()

        offenders.extend(
            f"{relative}:{name}"
            for name in sorted(names - allowed)
        )

    return offenders


class LayoutRegistryTests(unittest.TestCase):
    def _read_json(self, path: Path) -> object:
        self.assertTrue(path.is_file(), f"Missing required contract file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_registry_has_exactly_the_two_public_layouts(self) -> None:
        payload = self._read_json(REGISTRY)

        self.assertIsInstance(payload, list)
        entries = payload
        self.assertEqual([entry["slug"] for entry in entries], ["app", "page"])
        self.assertEqual({entry["slug"] for entry in entries}, PUBLIC_LAYOUT_SLUGS)

        for entry in entries:
            with self.subTest(slug=entry["slug"]):
                self.assertEqual(set(entry), REQUIRED_FIELDS)
                self.assertTrue(entry["label"])
                self.assertTrue(entry["description"])
                self.assertEqual(entry["status"], "preview")
                self.assertEqual(
                    entry["source"],
                    f"src/layouts/{entry['slug']}.html.jinja",
                )
                self.assertIsInstance(entry["parts"], list)
                self.assertIsInstance(entry["layoutParts"], list)

    def test_layout_dependencies_resolve_without_changing_component_identity(self) -> None:
        layouts = self._read_json(REGISTRY)
        components = self._read_json(COMPONENT_REGISTRY)
        layout_by_slug = {entry["slug"]: entry for entry in layouts}
        component_by_slug = {entry["slug"]: entry for entry in components}

        self.assertTrue(PUBLIC_LAYOUT_SLUGS.isdisjoint(component_by_slug))
        self.assertEqual(layout_by_slug["page"]["parts"], [])
        self.assertEqual(layout_by_slug["page"]["layoutParts"], [])
        self.assertEqual(layout_by_slug["app"]["parts"], ["sidebar"])
        self.assertEqual(layout_by_slug["app"]["layoutParts"], ["page"])

        for entry in layout_by_slug.values():
            for component_slug in entry["parts"]:
                with self.subTest(layout=entry["slug"], dependency=component_slug):
                    self.assertIn(component_slug, component_by_slug)
                    self.assertEqual(component_by_slug[component_slug]["status"], "ready")
            for layout_slug in entry["layoutParts"]:
                with self.subTest(layout=entry["slug"], dependency=layout_slug):
                    self.assertIn(layout_slug, layout_by_slug)

    def test_component_inventory_remains_the_exact_45_entry_baseline(self) -> None:
        components = self._read_json(COMPONENT_REGISTRY)
        evidence_inventory = self._read_json(
            ROOT / "src/certification/evidence-inventory.json"
        )

        self.assertEqual(len(components), 45)
        self.assertEqual(len({entry["slug"] for entry in components}), 45)
        self.assertEqual(len(evidence_inventory["components"]), 45)
        self.assertEqual(evidence_inventory["plannedComponents"], [])
        self.assertEqual(
            [entry["slug"] for entry in components],
            [entry["slug"] for entry in evidence_inventory["components"]],
        )
        self.assertEqual(len(COMPONENT_SOURCE_FILES), 44)
        self.assertIn("field.html.jinja", COMPONENT_SOURCE_FILES)
        self.assertIn("src/includes/field.html.jinja", COMPONENT_MACROS_BY_FILE)
        self.assertIn("form", COMPONENT_MACROS_BY_FILE["field.html.jinja"])

    def test_registered_layout_macros_have_one_dedicated_source_directory(self) -> None:
        registered = PUBLIC_LAYOUT_SLUGS
        definitions: dict[str, list[Path]] = {slug: [] for slug in registered}

        for path in (ROOT / "src").rglob("*.html.jinja"):
            source = path.read_text(encoding="utf-8")
            for match in MACRO_PATTERN.finditer(source):
                name = match.group("name")
                if name in registered:
                    definitions[name].append(path)

        for slug, paths in definitions.items():
            with self.subTest(slug=slug):
                self.assertTrue(
                    all(path.parent == LAYOUT_SOURCE_ROOT for path in paths),
                    f"Registered layout {slug} must be sourced from src/layouts",
                )

        self.assertTrue(SIDEBAR_SOURCE.is_file())
        for path in (ROOT / "src").rglob("*.html.jinja"):
            transition_definitions = {
                match.group("name")
                for match in MACRO_PATTERN.finditer(path.read_text(encoding="utf-8"))
            } & {"sidebar_provider", "sidebar_inset"}
            self.assertFalse(transition_definitions)

        self.assertEqual(_unregistered_layout_macro_offenders(ROOT), [])

    def test_an_extra_unregistered_layout_macro_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "src/components/account_layout.html.jinja"
            source.parent.mkdir(parents=True)
            source.write_text(
                "{% macro account_layout() %}{% endmacro %}\n",
                encoding="utf-8",
            )

            self.assertEqual(
                _unregistered_layout_macro_offenders(root),
                ["src/components/account_layout.html.jinja:account_layout"],
            )

    def test_settings_layout_is_not_a_public_layout(self) -> None:
        payload = self._read_json(REGISTRY)
        self.assertNotIn("settings-layout", {entry["slug"] for entry in payload})


if __name__ == "__main__":
    unittest.main()

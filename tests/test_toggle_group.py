from __future__ import annotations

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/toggle_group.html.jinja"
PAGE = ROOT / "src/pages/components/toggle-group.html.jinja"


class ToggleGroupTests(CatalogTestCase):
    def render_toggle_group(self, call: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Toggle Group macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/toggle_group.html.jinja" import toggle_group %}'
            f"{{{{ {call} }}}}"
        )
        return " ".join(template.render().split())

    def test_single_type_renders_radio_inputs_sharing_name(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", ['
            '{"id": "view-list", "label": "List"}, '
            '{"id": "view-grid", "label": "Grid"}'
            '], legend="View")'
        )
        self.assertIn('type="radio" class="btn-check" name="view" id="view-list"', output)
        self.assertIn('type="radio" class="btn-check" name="view" id="view-grid"', output)

    def test_multiple_type_shares_name_across_checkboxes(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("channels", ['
            '{"id": "channel-email", "label": "Email"}, '
            '{"id": "channel-sms", "label": "SMS"}'
            '], legend="Channels", type="multiple")'
        )
        self.assertIn(
            'type="checkbox" class="btn-check" name="channels" id="channel-email"',
            output,
        )
        self.assertIn(
            'type="checkbox" class="btn-check" name="channels" id="channel-sms"',
            output,
        )

    def test_item_value_defaults_to_item_id(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], legend="View")'
        )
        self.assertIn('id="view-list" value="view-list"', output)

    def test_item_falsey_value_is_preserved(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", '
            '[{"id": "view-list", "label": "List", "value": 0}], legend="View")'
        )
        self.assertIn('value="0"', output)

    def test_item_aria_label_renders_on_the_native_input(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", '
            '[{"id": "view-list", "icon": "list", "aria_label": "List"}], legend="View")'
        )
        self.assertIn('id="view-list" value="view-list" autocomplete="off" aria-label="List"', output)

    def test_duplicate_item_ids_fail(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Toggle Group item ids must be unique"
        ):
            self.render_toggle_group(
                'toggle_group("view", ['
                '{"id": "view-list", "label": "A"}, '
                '{"id": "view-list", "label": "B"}'
                '], legend="View")'
            )

    def test_pressed_and_disabled_render_as_boolean_attributes(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", ['
            '{"id": "view-list", "label": "List", "pressed": true, "disabled": true}'
            '], legend="View")'
        )
        self.assertIn("checked disabled>", output)

    def test_group_level_disabled_applies_to_every_item(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", ['
            '{"id": "view-list", "label": "List"}, '
            '{"id": "view-grid", "label": "Grid"}'
            '], legend="View", disabled=true)'
        )
        self.assertEqual(output.count("disabled>"), 2)

    def test_spacing_defaults_to_gap_2_horizontal_and_gap_1_vertical(self) -> None:
        horizontal = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], legend="View")'
        )
        vertical = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], '
            "legend=\"View\", vertical=true)"
        )
        self.assertIn("gap-2", horizontal)
        self.assertIn("gap-1", vertical)
        self.assertIn("flex-column", vertical)

    def test_spacing_can_be_overridden_explicitly(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], '
            'legend="View", spacing="3")'
        )
        self.assertIn("gap-3", output)

    def test_unknown_spacing_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown toggle group spacing: 4"):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "view-list", "label": "List"}], '
                'legend="View", spacing="4")'
            )

    def test_icon_only_item_gets_the_icon_button_size_class(self) -> None:
        default_size = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "icon": "list", "aria_label": "List"}], legend="View")'
        )
        small = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "icon": "list", "aria_label": "List"}], '
            'legend="View", size="sm")'
        )
        large = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "icon": "list", "aria_label": "List"}], '
            'legend="View", size="lg")'
        )
        self.assertIn("btn-icon\"", default_size)
        self.assertIn("btn-icon-sm", small)
        self.assertIn("btn-icon-lg", large)

    def test_labeled_item_uses_the_plain_button_size_class(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], '
            'legend="View", size="sm")'
        )
        self.assertNotIn("btn-icon", output)
        self.assertIn("btn-sm", output)

    def test_variant_maps_to_ghost_or_outline_secondary(self) -> None:
        default_variant = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], legend="View")'
        )
        outline_variant = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], '
            'legend="View", variant="outline")'
        )
        self.assertIn("btn-ghost", default_variant)
        self.assertIn("btn-outline-secondary", outline_variant)

    def test_requires_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Toggle Group name is required"):
            self.render_toggle_group(
                'toggle_group("   ", [{"id": "view-list", "label": "List"}], legend="View")'
            )

    def test_requires_legend(self) -> None:
        with self.assertRaisesRegex(ValueError, "Toggle Group legend is required"):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "view-list", "label": "List"}], legend="   ")'
            )

    def test_requires_items(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "Toggle Group requires at least one item"
        ):
            self.render_toggle_group('toggle_group("view", [], legend="View")')

    def test_requires_item_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "Toggle Group item id is required"):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "   ", "label": "List"}], legend="View")'
            )

    def test_requires_item_label_or_aria_label(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Toggle Group item without a visible label requires aria_label",
        ):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "view-list", "icon": "list"}], legend="View")'
            )

    def test_unknown_type_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown toggle group type: range"):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "view-list", "label": "List"}], '
                'legend="View", type="range")'
            )

    def test_unknown_variant_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown toggle group variant: solid"):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "view-list", "label": "List"}], '
                'legend="View", variant="solid")'
            )

    def test_unknown_size_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown toggle group size: xl"):
            self.render_toggle_group(
                'toggle_group("view", [{"id": "view-list", "label": "List"}], '
                'legend="View", size="xl")'
            )

    def test_supports_extra_class(self) -> None:
        output = self.render_toggle_group(
            'toggle_group("view", [{"id": "view-list", "label": "List"}], '
            'legend="View", extra_class="mb-3")'
        )
        self.assertIn("mb-3", output)

    def test_page_uses_realistic_original_scenarios(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        for distinctive_reference_scenario in (
            "Bold",
            "Italic",
            "Underline",
            "Top",
            "Bottom",
        ):
            self.assertNotIn(
                distinctive_reference_scenario,
                source,
                f"Page reuses the reference's own scenario shape: {distinctive_reference_scenario}",
            )
        for original_scenario in (
            "Notification channels",
            "Shipment method",
            "Task priority",
            "Approval stage",
        ):
            self.assertIn(original_scenario, source)

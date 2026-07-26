from __future__ import annotations

import json

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/combobox.html.jinja"
PAGE = ROOT / "src/pages/components/combobox.html.jinja"
REGISTRY = ROOT / "src/registry/components.json"
PREVIEW_JS = ROOT / "static/js/preview.js"


class ComboboxTests(CatalogTestCase):
    def render_combobox(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Combobox macro is not implemented")
        template = create_environment().from_string(
            '{% from "components/combobox.html.jinja" import combobox %}'
            + source
        )
        return " ".join(template.render().split())

    def test_combobox_renders_input_group_and_listbox_contract(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-owner", '
            'label="Owner", '
            'name="owner", '
            'placeholder="Select an owner", '
            'items=['
            '{"value": "ada", "label": "Ada Lovelace"}, '
            '{"value": "grace", "label": "Grace Hopper", "selected": true}'
            ']'
            ') }}'
        )

        self.assertIn('class="combobox"', output)
        self.assertIn('<label class="form-label" for="combo-owner-input">Owner</label>', output)
        self.assertIn('class="input-group combobox-control"', output)
        self.assertIn('id="combo-owner-input"', output)
        self.assertIn('class="form-control combobox-input"', output)
        self.assertIn('name="owner"', output)
        self.assertIn('role="combobox"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertIn('aria-controls="combo-owner-listbox"', output)
        self.assertIn('placeholder="Select an owner"', output)
        self.assertIn('value="Grace Hopper"', output)
        self.assertIn('type="hidden" name="owner-value" value="grace"', output)
        self.assertIn('class="input-group-text combobox-indicator"', output)
        self.assertNotIn("combobox-toggle", output)
        self.assertIn('role="listbox"', output)
        self.assertIn('id="combo-owner-listbox"', output)
        self.assertIn('role="option"', output)
        self.assertIn('data-value="grace"', output)
        self.assertIn('aria-selected="true"', output)

    def test_combobox_supports_grouped_and_custom_option_content(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-team", '
            'aria_label="Team", '
            'items=['
            '{"label": "Engineering", "options": ['
            '{"value": "portal", "label": "Portal Squad", "description": "Owns customer portal", "meta": "4 open", "icon": "layers", "selected": true}'
            ']}, '
            '{"label": "Operations", "options": ['
            '{"value": "support", "label": "Support Ops", "badge": "On call", "badge_variant": "warning"}'
            ']}'
            ']'
            ') }}'
        )

        self.assertIn('class="dropdown-header combobox-group-label">Engineering</h6>', output)
        self.assertIn('id="combo-team-option-1"', output)
        self.assertIn('class="combobox-option__description">Owns customer portal</span>', output)
        self.assertIn('class="combobox-option__meta">4 open</span>', output)
        self.assertIn('class="badge text-bg-warning combobox-option__badge">On call</span>', output)

    def test_combobox_can_render_open_popup_and_auto_highlight_state(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-status", '
            'aria_label="Status", '
            'placeholder="Search status", '
            'items=['
            '{"value": "draft", "label": "Draft"}, '
            '{"value": "approved", "label": "Approved"}'
            '], '
            'open=true, highlight_first=true'
            ') }}'
        )

        self.assertIn('aria-expanded="true"', output)
        self.assertIn('aria-activedescendant="combo-status-option-1"', output)
        self.assertIn('class="dropdown-menu combobox-menu show"', output)
        self.assertIn('data-bs-popper="static"', output)
        self.assertIn(
            'id="combo-status-option-1" type="button" role="option" '
            'data-value="draft" aria-selected="false"',
            output,
        )

    def test_combobox_supports_aria_label_mode_and_optional_states(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-region", '
            'aria_label="Region", '
            'placeholder="Search regions", '
            'items=[{"value": "eu", "label": "EU West"}], '
            'disabled=true, invalid=true, required=true, multiple=true'
            ') }}'
        )

        self.assertNotIn("<label", output)
        self.assertIn('aria-label="Region"', output)
        self.assertIn(" disabled", output)
        self.assertIn(" required", output)
        self.assertIn(" is-invalid", output)
        self.assertIn('aria-invalid="true"', output)
        self.assertIn('aria-multiselectable="true"', output)

    def test_combobox_fails_fast_for_invalid_contracts(self) -> None:
        invalid_calls = (
            (
                'combobox(id="combo", items=[{"value": "x", "label": "X"}])',
                "Combobox requires exactly one of label or aria_label",
            ),
            (
                'combobox(id="combo", label="Owner", aria_label="Owner", items=[{"value": "x", "label": "X"}])',
                "Combobox requires exactly one of label or aria_label",
            ),
            (
                'combobox(label="Owner", items=[{"value": "x", "label": "X"}])',
                "Combobox id is required",
            ),
            (
                'combobox(id="combo", aria_label="Owner")',
                "Combobox items are required",
            ),
            (
                'combobox(id="combo", aria_label="Owner", items=[{"value": "x"}, {"label": "Y"}])',
                "Combobox item value and label are required",
            ),
            (
                'combobox(id="combo", aria_label="Owner", items=[{"label": "Team", "options": [{"label": "Y"}]}])',
                "Combobox item value and label are required",
            ),
        )

        for call, message in invalid_calls:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_combobox(f"{{{{ {call} }}}}")

    def test_combobox_page_composes_original_moo_examples(self) -> None:
        self.assertTrue(PAGE.is_file(), "Combobox page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/combobox.html.jinja" import combobox %}', source)
        self.assertIn('{% from "components/field.html.jinja" import field, field_description, field_error %}', source)
        self.assertIn("Assign reviewer", source)
        self.assertIn("With chips", source)
        self.assertIn("Groups", source)
        self.assertIn("Custom Items", source)
        self.assertIn("Release window", source)
        self.assertIn("Workspace access", source)
        self.assertIn("Auto Highlight", source)
        self.assertIn("Popup", source)
        self.assertIn("Input Group", source)
        self.assertIn("render_rtl_example(", source)
        self.assertNotIn("Select a framework", source)
        self.assertNotIn("Svelte", source)

    def test_preview_js_wires_interactive_combobox_behavior(self) -> None:
        source = PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn(".combobox", source)
        self.assertIn(".combobox-input", source)
        self.assertIn(".combobox-option", source)
        self.assertIn("data-moo-combobox-empty", source)
        self.assertIn('menu.classList.add("show")', source)
        self.assertIn('input.addEventListener("focus"', source)
        self.assertIn('option.setAttribute("aria-selected",', source)
        self.assertIn('input.setAttribute("aria-activedescendant"', source)
        self.assertIn("hidden.value = option.dataset.value || \"\"", source)

    def test_combobox_is_ready_in_catalog_registry(self) -> None:
        catalog = json.loads(REGISTRY.read_text(encoding="utf-8"))
        combobox = next((item for item in catalog if item["slug"] == "combobox"), None)

        self.assertIsNotNone(combobox)
        self.assertEqual(combobox["label"], "Combobox")
        self.assertEqual(combobox["status"], "ready")

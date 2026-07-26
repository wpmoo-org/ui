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

    def test_combobox_renders_basic_shadcn_anatomy(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-reviewer", '
            'label="Reviewer", '
            'name="reviewer", '
            'placeholder="Select a reviewer", '
            'items=['
            '{"value": "ada", "label": "Ada Lovelace"}, '
            '{"value": "grace", "label": "Grace Hopper", "selected": true}'
            ']'
            ') }}'
        )

        self.assertIn('class="combobox"', output)
        self.assertIn('<label class="form-label" for="combo-reviewer-input">Reviewer</label>', output)
        self.assertIn('class="combobox-control"', output)
        self.assertNotIn("input-group", output)
        self.assertNotIn("combobox-addon", output)
        self.assertIn('class="form-control combobox-input"', output)
        self.assertIn('id="combo-reviewer-input"', output)
        self.assertIn('role="combobox"', output)
        self.assertIn('aria-expanded="false"', output)
        self.assertIn('aria-controls="combo-reviewer-listbox"', output)
        self.assertIn('aria-autocomplete="list"', output)
        self.assertIn('placeholder="Select a reviewer"', output)
        self.assertIn('value="Grace Hopper"', output)
        self.assertNotIn('name="reviewer" role="combobox"', output)
        self.assertIn('type="hidden" name="reviewer" value="grace"', output)
        self.assertIn('class="combobox-indicator"', output)
        self.assertIn('data-lucide="chevron-down"', output)
        self.assertNotIn('data-lucide="chevrons-up-down"', output)
        self.assertIn('class="dropdown-menu combobox-menu"', output)
        self.assertIn('id="combo-reviewer-listbox"', output)
        self.assertIn('role="listbox"', output)
        self.assertIn('role="option"', output)
        self.assertIn('data-value="grace"', output)
        self.assertIn('aria-selected="true"', output)
        self.assertEqual(output.count('class="combobox-option__check"'), 2)
        self.assertNotIn("aria-multiselectable", output)
        self.assertNotIn("combobox-popup", output)

    def test_combobox_check_icon_is_css_driven_for_runtime_selection(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-runtime", '
            'aria_label="Reviewer", '
            'items=['
            '{"value": "ada", "label": "Ada Lovelace"}, '
            '{"value": "grace", "label": "Grace Hopper"}'
            ']'
            ') }}'
        )
        scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")

        self.assertEqual(output.count('class="combobox-option__check"'), 2)
        self.assertIn(".combobox-option__check", scss)
        self.assertIn("visibility: hidden;", scss)
        self.assertIn('.combobox-option[aria-selected="true"] .combobox-option__check', scss)

    def test_combobox_can_render_open_basic_list(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-open", '
            'aria_label="Reviewer", '
            'placeholder="Select a reviewer", '
            'items=['
            '{"value": "ada", "label": "Ada Lovelace"}, '
            '{"value": "grace", "label": "Grace Hopper"}'
            '], '
            'open=true, highlight_first=true'
            ') }}'
        )

        self.assertIn('aria-expanded="true"', output)
        self.assertIn('aria-activedescendant="combo-open-option-1"', output)
        self.assertIn('class="dropdown-menu combobox-menu show"', output)
        self.assertNotIn('data-bs-popper="static"', output)

    def test_combobox_renders_multiple_chips_anatomy(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-areas", '
            'aria_label="Review areas", '
            'name="review_areas", '
            'placeholder="Add review area", '
            'multiple=true, '
            'selected=["security", "billing"], '
            'items=['
            '{"value": "security", "label": "Security"}, '
            '{"value": "billing", "label": "Billing"}, '
            '{"value": "ops", "label": "Operations"}'
            ']'
            ') }}'
        )

        self.assertIn('class="combobox combobox--multiple"', output)
        self.assertIn('data-moo-combobox-multiple="true"', output)
        self.assertIn('class="form-control combobox-chips"', output)
        self.assertIn('class="combobox-value"', output)
        self.assertEqual(output.count('class="badge text-bg-secondary combobox-chip"'), 2)
        self.assertIn('aria-label="Remove Security"', output)
        self.assertIn('aria-label="Remove Billing"', output)
        self.assertIn('data-moo-combobox-chip-remove="true"', output)
        self.assertIn("combobox-chips-input", output)
        self.assertIn('role="combobox"', output)
        self.assertIn('placeholder="Add review area"', output)
        self.assertIn('aria-controls="combo-areas-listbox"', output)
        self.assertIn('role="listbox" aria-multiselectable="true"', output)
        self.assertEqual(output.count('type="hidden" name="review_areas"'), 2)
        self.assertIn('type="hidden" name="review_areas" value="security"', output)
        self.assertIn('type="hidden" name="review_areas" value="billing"', output)
        self.assertNotIn('name="review_areas" role="combobox"', output)
        self.assertIn('data-value="security" aria-selected="true"', output)
        self.assertIn('data-value="billing" aria-selected="true"', output)
        self.assertIn('data-value="ops" aria-selected="false"', output)

    def test_combobox_fails_fast_for_invalid_basic_contracts(self) -> None:
        invalid_calls = (
            (
                'combobox(id="combo", items=[{"value": "x", "label": "X"}])',
                "Combobox requires exactly one of label or aria_label",
            ),
            (
                'combobox(id="combo", label="Reviewer", aria_label="Reviewer", items=[{"value": "x", "label": "X"}])',
                "Combobox requires exactly one of label or aria_label",
            ),
            (
                'combobox(label="Reviewer", items=[{"value": "x", "label": "X"}])',
                "Combobox id is required",
            ),
            (
                'combobox(id="combo", aria_label="Reviewer")',
                "Combobox items are required",
            ),
            (
                'combobox(id="combo", aria_label="Reviewer", items=[{"value": "x"}, {"label": "Y"}])',
                "Combobox item value and label are required",
            ),
            (
                'combobox(id="combo", aria_label="Reviewer", items=[{"label": "Team", "options": [{"value": "x", "label": "X"}]}])',
                "Combobox Basic supports flat items only",
            ),
        )

        for call, message in invalid_calls:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_combobox(f"{{{{ {call} }}}}")

    def test_combobox_multiple_requires_list_selection(self) -> None:
        invalid_calls = (
            (
                'combobox(id="combo", aria_label="Reviewer", multiple=true, selected="x", items=[{"value": "x", "label": "X"}])',
                "Combobox multiple selected values must be a list",
            ),
            (
                'combobox(id="combo", aria_label="Reviewer", multiple=false, selected=["x"], items=[{"value": "x", "label": "X"}])',
                "Combobox single selected value must be a string",
            ),
        )

        for call, message in invalid_calls:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_combobox(f"{{{{ {call} }}}}")

    def test_combobox_page_contains_basic_and_multiple_only_for_current_phase(self) -> None:
        self.assertTrue(PAGE.is_file(), "Combobox page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/combobox.html.jinja" import combobox %}', source)
        self.assertIn('"basic"', source)
        self.assertIn('"Basic"', source)
        self.assertIn("Select a reviewer", source)
        self.assertIn('"multiple"', source)
        self.assertIn('"Multiple"', source)
        self.assertIn("Add review area", source)
        self.assertNotIn('"Clear Button"', source)
        self.assertNotIn('"Groups"', source)
        self.assertNotIn('"Custom Items"', source)
        self.assertNotIn('"Popup"', source)
        self.assertNotIn('"Input Group"', source)
        self.assertNotIn("render_rtl_example(", source)
        self.assertNotIn("Select a framework", source)
        self.assertNotIn("Svelte", source)

    def test_preview_js_wires_basic_combobox_behavior(self) -> None:
        source = PREVIEW_JS.read_text(encoding="utf-8")

        self.assertIn(".combobox", source)
        self.assertIn(".combobox-input", source)
        self.assertIn(".combobox-option", source)
        self.assertIn("data-moo-combobox-empty", source)
        self.assertIn("mooComboboxMultiple", source)
        self.assertIn("data-moo-combobox-chip-remove", source)
        self.assertIn('menu.classList.add("show")', source)
        self.assertIn('input.addEventListener("focus"', source)
        self.assertIn('setAttribute("aria-selected",', source)
        self.assertIn("syncMultipleValue", source)
        self.assertIn("removeChip", source)
        self.assertIn('event.key === "Backspace"', source)
        self.assertIn('input.setAttribute("aria-activedescendant"', source)
        self.assertIn("hidden.value = option.dataset.value || \"\"", source)
        self.assertRegex(
            source,
            r"const closeMenu = \(\) => \{[^}]*input\.removeAttribute\(\"aria-activedescendant\"\);",
        )
        self.assertIn("const clearSelection = () => {", source)
        self.assertIn('hidden.value = "";', source)
        self.assertIn('input.addEventListener("blur", clearStaleSelection);', source)
        self.assertIn('event.key === "Tab"', source)
        self.assertNotIn("combobox-popup-trigger", source)

    def test_combobox_is_ready_in_catalog_registry(self) -> None:
        catalog = json.loads(REGISTRY.read_text(encoding="utf-8"))
        combobox = next((item for item in catalog if item["slug"] == "combobox"), None)

        self.assertIsNotNone(combobox)
        self.assertEqual(combobox["label"], "Combobox")
        self.assertEqual(combobox["status"], "ready")

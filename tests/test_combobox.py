from __future__ import annotations

import json

from build import create_environment
from tests.helpers import (
    ROOT,
    CatalogTestCase,
    read_catalog_styles,
    read_primary_variables,
)


COMPONENT = ROOT / "src/components/combobox.html.jinja"
PAGE = ROOT / "site/src/pages/components/combobox.html.jinja"
REGISTRY = ROOT / "src/registry/components.json"
COMBOBOX_JS = ROOT / "src/js/components/combobox.js"
CATALOG_JS = ROOT / "src/js/catalog/index.js"


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
        self.assertEqual(output.count('<li role="presentation">'), 2)
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

    def test_combobox_renders_clear_button_anatomy(self) -> None:
        selected_output = self.render_combobox(
            '{{ combobox('
            'id="combo-clear-selected", '
            'aria_label="Reviewer", '
            'name="reviewer", '
            'placeholder="Select a reviewer", '
            'show_clear=true, '
            'selected="grace", '
            'items=['
            '{"value": "ada", "label": "Ada Lovelace"}, '
            '{"value": "grace", "label": "Grace Hopper"}'
            ']'
            ') }}'
        )
        empty_output = self.render_combobox(
            '{{ combobox('
            'id="combo-clear-empty", '
            'aria_label="Reviewer", '
            'name="reviewer", '
            'placeholder="Select a reviewer", '
            'show_clear=true, '
            'items=['
            '{"value": "ada", "label": "Ada Lovelace"}, '
            '{"value": "grace", "label": "Grace Hopper"}'
            ']'
            ') }}'
        )

        self.assertIn('class="combobox combobox--clearable"', selected_output)
        self.assertIn('data-moo-combobox-selected="true"', selected_output)
        self.assertIn('class="form-control combobox-input"', selected_output)
        self.assertIn('value="Grace Hopper"', selected_output)
        self.assertIn('type="hidden" name="reviewer" value="grace"', selected_output)
        self.assertIn('class="combobox-clear"', selected_output)
        self.assertIn('aria-label="Clear selection"', selected_output)
        self.assertIn('data-moo-combobox-clear="true"', selected_output)
        self.assertIn('data-lucide="x"', selected_output)
        self.assertNotIn("btn-close", selected_output)
        self.assertNotIn('data-moo-combobox-clear="true" hidden', selected_output)
        self.assertIn('class="combobox-indicator" aria-hidden="true" hidden', selected_output)
        self.assertIn('data-lucide="chevron-down"', selected_output)
        self.assertIn('data-moo-combobox-selected="false"', empty_output)
        self.assertIn('data-moo-combobox-clear="true" hidden', empty_output)
        self.assertIn('class="combobox-indicator" aria-hidden="true">', empty_output)

    def test_combobox_renders_grouped_items_anatomy(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-timezone", '
            'aria_label="Timezone", '
            'name="timezone", '
            'placeholder="Select a timezone", '
            'items=['
            '{"label": "Americas", "options": ['
            '{"value": "new-york", "label": "(GMT-5) New York"}, '
            '{"value": "los-angeles", "label": "(GMT-8) Los Angeles"}'
            ']}, '
            '{"label": "Europe", "options": ['
            '{"value": "london", "label": "(GMT+0) London", "selected": true}, '
            '{"value": "paris", "label": "(GMT+1) Paris"}'
            ']}'
            ']'
            ') }}'
        )

        self.assertIn('class="combobox"', output)
        self.assertNotIn("combobox--grouped", output)
        self.assertIn('placeholder="Select a timezone"', output)
        self.assertIn('value="(GMT+0) London"', output)
        self.assertIn('type="hidden" name="timezone" value="london"', output)
        self.assertIn('role="group" aria-labelledby="combo-timezone-group-1"', output)
        self.assertIn('class="dropdown-header combobox-group-label" id="combo-timezone-group-1"', output)
        self.assertIn(">Americas<", output)
        self.assertIn('role="group" aria-labelledby="combo-timezone-group-2"', output)
        self.assertIn('class="dropdown-header combobox-group-label" id="combo-timezone-group-2"', output)
        self.assertIn(">Europe<", output)
        self.assertIn('class="list-unstyled mb-0" role="presentation"', output)
        self.assertIn(
            '<li role="presentation" aria-hidden="true" data-moo-combobox-separator>',
            output,
        )
        self.assertIn('class="dropdown-divider combobox-separator"', output)
        self.assertIn('data-value="london" aria-selected="true"', output)
        self.assertEqual(output.count('role="option"'), 4)

    def test_combobox_renders_custom_item_rows_anatomy(self) -> None:
        output = self.render_combobox(
            '{{ combobox('
            'id="combo-request-type", '
            'aria_label="Request type", '
            'name="request_type", '
            'placeholder="Search request types...", '
            'items=['
            '{"value": "sla-risk", "label": "SLA risk", "description": "Support queue"}, '
            '{"value": "plan-change", "label": "Plan change", "description": "Billing workflow"}, '
            '{"value": "portal-bug", "label": "Portal bug", "description": "Customer portal", "selected": true}'
            ']'
            ') }}'
        )

        self.assertIn('class="combobox combobox--custom-items"', output)
        self.assertIn('placeholder="Search request types..."', output)
        self.assertIn('value="Portal bug"', output)
        self.assertIn('type="hidden" name="request_type" value="portal-bug"', output)
        self.assertEqual(output.count('class="combobox-option__content"'), 3)
        self.assertIn('class="combobox-option__description">Support queue</span>', output)
        self.assertIn('class="combobox-option__description">Billing workflow</span>', output)
        self.assertIn('data-value="portal-bug" aria-selected="true"', output)

    def test_combobox_menus_scroll_with_hidden_scrollbar_when_long(self) -> None:
        scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")
        variables = read_primary_variables()

        self.assertIn(".combobox-menu {", scss)
        menu_source = scss.split(".combobox-menu {", 1)[1]
        menu_end = "\n}\n\n.combobox--custom-items" if ".combobox--custom-items .combobox-menu" in scss else "\n}\n\n.combobox-option"
        menu = menu_source.split(menu_end, 1)[0]
        self.assertIn("max-height: var(--moo-combobox-menu-max-height);", menu)
        self.assertIn("overflow-y: auto;", menu)
        self.assertIn("overscroll-behavior: contain;", menu)
        self.assertIn("scrollbar-width: none;", menu)
        self.assertIn(".combobox-menu::-webkit-scrollbar", scss)
        self.assertIn("--moo-combobox-menu-max-height", scss)
        self.assertIn("$moo-combobox-menu-max-height: $input-height * 8 !default;", variables)
        self.assertNotIn(".combobox--custom-items .combobox-menu", scss)

    def test_combobox_custom_item_typography_matches_reference_contract(self) -> None:
        scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")
        variables = read_primary_variables()

        self.assertIn("$moo-combobox-option-line-height: 1.25rem !default;", variables)
        self.assertIn("$moo-combobox-description-font-size: 0.75rem !default;", variables)
        self.assertIn("--moo-combobox-option-line-height", scss)
        self.assertIn("--moo-combobox-description-font-size", scss)

        option_block = scss.split(".combobox-option {", 1)[1].split("}", 1)[0]
        description_block = scss.split(".combobox-option__description {", 1)[1].split("}", 1)[0]
        group_label_block = scss.split(".combobox-group-label {", 1)[1].split("}", 1)[0]

        self.assertIn("line-height: var(--moo-combobox-option-line-height);", option_block)
        self.assertNotIn("min-height: $input-height;", option_block)
        self.assertIn("padding-inline-end: $input-height;", option_block)
        self.assertIn("font-size: var(--moo-combobox-description-font-size);", group_label_block)
        self.assertIn("font-weight: $font-weight-normal;", group_label_block)
        self.assertIn("line-height: $spacer;", group_label_block)
        self.assertIn("font-size: var(--moo-combobox-description-font-size);", description_block)
        self.assertIn("line-height: $line-height-base;", description_block)
        self.assertIn(".combobox--custom-items .combobox-option__label", scss)
        self.assertIn("font-weight: $font-weight-medium;", scss)

    def test_combobox_renders_invalid_and_disabled_states(self) -> None:
        invalid_output = self.render_combobox(
            '{{ combobox('
            'id="combo-invalid", '
            'aria_label="Reviewer", '
            'placeholder="Select a reviewer", '
            'invalid=true, '
            'items=[{"value": "ada", "label": "Ada Lovelace"}]'
            ') }}'
        )
        disabled_output = self.render_combobox(
            '{{ combobox('
            'id="combo-disabled", '
            'aria_label="Reviewer", '
            'placeholder="Select a reviewer", '
            'disabled=true, '
            'items=[{"value": "ada", "label": "Ada Lovelace"}]'
            ') }}'
        )

        self.assertIn('class="form-control combobox-input is-invalid"', invalid_output)
        self.assertIn('aria-invalid="true"', invalid_output)
        self.assertIn('class="form-control combobox-input"', disabled_output)
        self.assertIn('disabled', disabled_output)
        self.assertNotIn('aria-invalid="true"', disabled_output)

    def test_combobox_invalid_state_keeps_single_inline_affordance(self) -> None:
        scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")

        self.assertIn(".combobox-input.is-invalid {", scss)
        invalid_input = scss.split(".combobox-input.is-invalid {", 1)[1].split(
            "\n}\n\n.combobox-indicator",
            1,
        )[0]
        self.assertIn("background-image: none;", invalid_input)

    def test_combobox_disabled_state_fades_indicator_with_input(self) -> None:
        scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")

        self.assertIn(".combobox-control:has(.combobox-input:disabled)", scss)
        self.assertIn("opacity: var(--moo-disabled-control-opacity);", scss)
        self.assertIn(".combobox-control:has(.combobox-input:disabled) .combobox-input:disabled", scss)
        self.assertIn("opacity: 1;", scss)

    def test_combobox_option_content_keeps_minimal_item_api(self) -> None:
        source = COMPONENT.read_text(encoding="utf-8")

        self.assertIn("{% macro combobox_option_content(item) -%}", source)
        self.assertNotIn("combobox_option_content(item, selected", source)
        self.assertNotIn("combobox_option_content(item, is_selected)", source)

    def test_combobox_multiple_chips_surface_focuses_like_input(self) -> None:
        script = COMBOBOX_JS.read_text(encoding="utf-8")
        scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")
        chips_block = scss.split(".combobox-chips {", 1)[1].split("}", 1)[0]

        self.assertIn("cursor: text;", chips_block)
        self.assertIn('target.closest(".combobox-chips")', script)
        self.assertRegex(
            script,
            r"target\.closest\(\"\.combobox-chips\"\)[\s\S]*this\._input\.focus\(\);",
        )

    def test_combobox_preview_keeps_component_width_tokens(self) -> None:
        catalog_scss = read_catalog_styles()
        component_scss = (ROOT / "scss/components/_combobox.scss").read_text(encoding="utf-8")

        self.assertIn(".moo-example__preview--narrow > .combobox", catalog_scss)
        self.assertIn("max-width: var(--moo-combobox-width);", catalog_scss)
        self.assertIn(".moo-example__preview--narrow > .combobox--multiple", catalog_scss)
        self.assertIn("max-width: var(--moo-combobox-multiple-width);", catalog_scss)
        multiple_block = component_scss.split(".combobox--multiple {", 1)[1].split("}", 1)[0]
        catalog_multiple_block = catalog_scss.split(
            ".moo-example__preview--narrow > .combobox--multiple {",
            1,
        )[1].split("}", 1)[0]

        self.assertIn("max-width: var(--moo-combobox-multiple-width);", multiple_block)
        self.assertIn(
            "max-width: var(--moo-combobox-multiple-width);",
            catalog_multiple_block,
        )
        self.assertNotIn(".combobox--grouped", multiple_block)
        self.assertNotIn(".combobox--custom-items", multiple_block)
        self.assertNotIn(".moo-example__preview--narrow > .combobox--grouped", catalog_scss)
        self.assertNotIn(".moo-example__preview--narrow > .combobox--custom-items", catalog_scss)

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
                'combobox(id="combo", aria_label="Reviewer", items=[{"options": [{"value": "x", "label": "X"}]}])',
                "Combobox group label is required",
            ),
            (
                'combobox(id="combo", aria_label="Reviewer", items=[{"label": "Team", "options": []}])',
                "Combobox group options are required",
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
            (
                'combobox(id="combo", aria_label="Reviewer", multiple=true, show_clear=true, items=[{"value": "x", "label": "X"}])',
                "Combobox clear button supports single selection only",
            ),
        )

        for call, message in invalid_calls:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    self.render_combobox(f"{{{{ {call} }}}}")

    def test_combobox_page_contains_basic_multiple_and_clear_button_for_current_phase(self) -> None:
        self.assertTrue(PAGE.is_file(), "Combobox page is not implemented")
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('{% from "components/combobox.html.jinja" import combobox %}', source)
        self.assertIn('{% from "components/field.html.jinja" import field, field_description %}', source)
        self.assertIn('"basic"', source)
        self.assertIn('"Basic"', source)
        self.assertIn("Select a reviewer", source)
        self.assertIn('"multiple"', source)
        self.assertIn('"Multiple"', source)
        self.assertIn('label="Review areas"', source)
        self.assertIn('describedby="combobox-review-areas-help"', source)
        self.assertIn("Choose every area this review should cover.", source)
        self.assertNotIn("Add review area", source)
        self.assertIn('"clear-button"', source)
        self.assertIn('"Clear Button"', source)
        self.assertIn('selected="ada"', source)
        self.assertIn("show_clear=true", source)
        self.assertIn('"groups"', source)
        self.assertIn('"Groups"', source)
        self.assertIn("Select a timezone", source)
        self.assertIn("Bootstrap dropdown headers and dividers", source)
        self.assertIn('"Americas"', source)
        self.assertIn('"Europe"', source)
        self.assertIn('"Asia/Pacific"', source)
        self.assertIn("(GMT-5) New York", source)
        self.assertIn("(GMT-8) Los Angeles", source)
        self.assertIn("(GMT-5) Toronto", source)
        self.assertIn("(GMT-8) Vancouver", source)
        self.assertIn("(GMT-3) São Paulo", source)
        self.assertIn("(GMT+1) Amsterdam", source)
        self.assertIn("(GMT+11) Sydney", source)
        self.assertNotIn("ComboboxGroup", source)
        self.assertNotIn("ComboboxSeparator", source)
        self.assertIn('"custom-items"', source)
        self.assertIn('"Custom Items"', source)
        self.assertIn("Search request types...", source)
        self.assertIn("secondary text", source)
        self.assertNotIn("South America", source)
        self.assertNotIn("Argentina", source)
        self.assertNotIn("Brazil", source)
        self.assertNotIn("Search countries", source)
        self.assertIn('"invalid"', source)
        self.assertIn('"Invalid"', source)
        self.assertIn("invalid=true", source)
        self.assertIn('"disabled"', source)
        self.assertIn('"Disabled"', source)
        self.assertIn("disabled=true", source)
        self.assertNotIn('"Auto Highlight"', source)
        self.assertNotIn('"Popup"', source)
        self.assertNotIn('"Input Group"', source)
        self.assertNotIn("render_rtl_example(", source)
        self.assertNotIn("Select a framework", source)
        self.assertNotIn("Svelte", source)
        self.assertIn(
            'typography("JavaScript", variant="section-title", id="combobox-javascript")',
            source,
        )
        self.assertNotIn('<h2 id="combobox-javascript">', source)
        self.assertIn('import Combobox from "@wpmoo/ui/combobox.js";', source)
        self.assertIn("Combobox.getOrCreateInstance(element)", source)
        self.assertIn("combobox.dispose()", source)
        self.assertIn("Bootstrap 5.3 does not provide a Combobox plugin", source)

    def test_public_module_owns_combobox_behavior_and_lifecycle(self) -> None:
        source = COMBOBOX_JS.read_text(encoding="utf-8")
        catalog = CATALOG_JS.read_text(encoding="utf-8")

        self.assertIn("export default class Combobox", source)
        self.assertIn("static getInstance(element)", source)
        self.assertIn("static getOrCreateInstance(element, config = {})", source)
        self.assertIn("dispose()", source)
        self.assertIn("instances.set(element, this);", source)
        self.assertIn("instances.delete(this._element);", source)
        self.assertIn("removeEventListener(type, handler, options)", source)
        self.assertIn(".combobox-input", source)
        self.assertIn(".combobox-option", source)
        self.assertIn("mooComboboxMultiple", source)
        self.assertIn("data-moo-combobox-chip-remove", source)
        self.assertIn('event.key === "Backspace"', source)
        self.assertIn('event.key === "Tab"', source)
        self.assertIn('this._hidden.value = option.dataset.value || ""', source)
        self.assertIn("data-moo-combobox-group", source)
        self.assertNotIn("combobox-popup-trigger", source)
        self.assertIn('import Combobox from "../components/combobox.js";', catalog)
        self.assertIn("Combobox.getOrCreateInstance(element);", catalog)
        self.assertNotIn(".combobox-input", catalog)

    def test_public_module_does_not_scroll_closed_comboboxes_on_initialization(self) -> None:
        source = COMBOBOX_JS.read_text(encoding="utf-8")

        self.assertIn(
            "this._filterOptions({ open: this._startsOpen, activate: this._startsOpen });",
            source,
        )
        self.assertIn("this._menu.scrollTop", source)
        self.assertNotIn("scrollIntoView", source)
        self.assertNotIn("this._filterOptions();\n    if (!this._startsOpen)", source)

    def test_combobox_is_ready_in_catalog_registry(self) -> None:
        catalog = json.loads(REGISTRY.read_text(encoding="utf-8"))
        combobox = next((item for item in catalog if item["slug"] == "combobox"), None)

        self.assertIsNotNone(combobox)
        self.assertEqual(combobox["label"], "Combobox")
        self.assertEqual(combobox["status"], "ready")

from __future__ import annotations

from html.parser import HTMLParser
import re

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase


COMPONENT = ROOT / "src/components/button_group.html.jinja"
PAGE = ROOT / "site/src/pages/components/button-group.html.jinja"


class ButtonGroupSemanticParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.groups: list[dict[str, object]] = []
        self._current_group: dict[str, object] | None = None
        self._current_group_depth = 0
        self._current_button: dict[str, object] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()

        if self._current_group is not None:
            self._current_group_depth += 1

        if tag == "div" and "btn-group" in classes:
            self._current_group = {
                "role": attributes.get("role") or "",
                "aria_label": attributes.get("aria-label") or "",
                "buttons": [],
            }
            self.groups.append(self._current_group)
            self._current_group_depth = 1
            return

        if tag == "button" and self._current_group is not None:
            self._current_button = {"classes": classes, "text": ""}
            buttons = self._current_group["buttons"]
            assert isinstance(buttons, list)
            buttons.append(self._current_button)

    def handle_data(self, data: str) -> None:
        if self._current_button is not None:
            self._current_button["text"] = str(self._current_button["text"]) + data

    def handle_endtag(self, tag: str) -> None:
        if tag == "button":
            self._current_button = None

        if self._current_group is None:
            return

        self._current_group_depth -= 1
        if self._current_group_depth <= 0:
            self._current_group = None
            self._current_group_depth = 0


class ButtonGroupTests(CatalogTestCase):
    def render(self, source: str) -> str:
        self.assertTrue(COMPONENT.is_file(), "Button Group macro is not implemented")
        template = create_environment().from_string(source)
        return " ".join(template.render().split())

    def normalize_css_selector(self, selector: str) -> str:
        selector = re.sub(r"\s+", " ", selector.strip())
        selector = re.sub(r"\s*,\s*", ",", selector)
        selector = re.sub(r"\s*>\s*", ">", selector)
        selector = re.sub(r"\s*\+\s*", "+", selector)
        return selector

    def css_rule_body(self, css: str, selector: str) -> str:
        expected_selector = self.normalize_css_selector(selector)
        for rule in re.finditer(
            r"(?P<selector>[^{}]+)\{(?P<body>[^{}]*)\}",
            css,
            re.DOTALL,
        ):
            if self.normalize_css_selector(rule.group("selector")) == expected_selector:
                return rule.group("body")

        self.fail(f"Missing CSS rule for selector: {selector}")
        return ""

    def test_renders_bootstrap_group_with_accessible_label(self) -> None:
        output = self.render(
            '{% from "components/button_group.html.jinja" import button_group %}'
            '{% call button_group("Ticket actions") %}Actions{% endcall %}'
        )

        self.assertIn('class="btn-group"', output)
        self.assertIn('role="group"', output)
        self.assertIn('aria-label="Ticket actions"', output)

    def test_toolbar_and_vertical_modes_use_bootstrap_classes(self) -> None:
        toolbar = self.render(
            '{% from "components/button_group.html.jinja" import button_group %}'
            '{% call button_group("Editor toolbar", toolbar=true, extra_class="gap-2") %}x{% endcall %}'
        )
        vertical = self.render(
            '{% from "components/button_group.html.jinja" import button_group %}'
            '{% call button_group("Quantity", vertical=true) %}x{% endcall %}'
        )

        self.assertIn('class="btn-toolbar gap-2"', toolbar)
        self.assertIn('role="toolbar"', toolbar)
        self.assertIn('class="btn-group-vertical"', vertical)

    def test_page_uses_render_rtl_example_for_direction(self) -> None:
        source = PAGE.read_text(encoding="utf-8")

        self.assertIn('render_rtl_example(', source)
        self.assertIn('"button-group-ribbon"', source)
        self.assertIn("rtl_arabic", source)
        self.assertIn("rtl_hebrew", source)
        self.assertIn("rtl_english", source)
        self.assertIn('dir="rtl"', source)
        self.assertNotIn('{% from "components/tabs.html.jinja" import tabs %}', source)

    def test_page_omits_redundant_split_example_and_keeps_dropdown_menu(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/button-group.html")
        self.assertNotIn('data-example="split-button"', output)
        self.assertNotIn('aria-label="Follow options"', output)

        section = output.split('data-example="dropdown-button"', 1)[1].split(
            '<div class="moo-example__source"',
            1,
        )[0]

        self.assertIn('aria-label="Deploy options"', section)
        self.assertIn('data-bs-toggle="dropdown"', section)
        self.assertIn('class="dropdown-menu dropdown-menu-end"', section)

    def test_page_documents_mixed_emphasis_actions_as_a_joined_group(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.read_output("components/button-group.html")
        section = output.split('data-example="mixed-emphasis-group"', 1)[1].split(
            '<div class="moo-example__source"',
            1,
        )[0]
        parser = ButtonGroupSemanticParser()
        parser.feed(section)
        review_groups = [
            group
            for group in parser.groups
            if group["role"] == "group" and group["aria_label"] == "Review actions"
        ]

        self.assertNotIn('class="btn-toolbar', section)
        self.assertEqual(len(review_groups), 1)
        buttons = review_groups[0]["buttons"]
        self.assertIsInstance(buttons, list)
        self.assertEqual(
            [" ".join(str(button["text"]).split()) for button in buttons],
            ["Approve", "Archive"],
        )
        self.assertEqual(
            [
                {"btn", "btn-primary"}.issubset(button["classes"])
                for button in buttons
            ],
            [True, False],
        )
        self.assertEqual(
            [
                {"btn", "btn-outline-secondary"}.issubset(button["classes"])
                for button in buttons
            ],
            [False, True],
        )

    def test_core_css_keeps_pointer_group_states_from_restacking_joined_buttons(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        pointer_state_selector = (
            ".btn-group > .btn:hover:not(:focus-visible):not(.active),\n"
            ".btn-group > .btn:focus:not(:focus-visible):not(.active),\n"
            ".btn-group > .btn:active:not(:focus-visible):not(.active),\n"
            ".btn-group-vertical > .btn:hover:not(:focus-visible):not(.active),\n"
            ".btn-group-vertical > .btn:focus:not(:focus-visible):not(.active),\n"
            ".btn-group-vertical > .btn:active:not(:focus-visible):not(.active)"
        )
        checked_hover_selector = (
            ".btn-group > .btn-check:checked + .btn:hover,\n"
            ".btn-group > .btn-check:focus + .btn:hover,\n"
            ".btn-group-vertical > .btn-check:checked + .btn:hover,\n"
            ".btn-group-vertical > .btn-check:focus + .btn:hover"
        )

        self.assertIn("z-index: auto;", self.css_rule_body(css, pointer_state_selector))
        self.assertIn("z-index: 1;", self.css_rule_body(css, checked_hover_selector))

    def test_grouped_button_active_press_does_not_translate_one_segment(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.read_output("assets/css/moo-ui.css")
        grouped_active_selector = (
            '.btn-group > .btn:not(:disabled):not(.disabled):not([aria-disabled="true"]):active,\n'
            '.btn-group-vertical > .btn:not(:disabled):not(.disabled):not([aria-disabled="true"]):active'
        )

        self.assertIn("transform: none;", self.css_rule_body(css, grouped_active_selector))

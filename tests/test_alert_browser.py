from __future__ import annotations

import unittest
from xml.etree import ElementTree

from markupsafe import Markup

from playwright.sync_api import expect, sync_playwright

from build import compile_style, create_environment
from tests.helpers import ROOT
from tests.helpers.browser_harness import (
    BrowserCase,
    BrowserEvidence,
    launch_certification_browser,
    new_case_context,
    skip_if_browser_launch_is_sandboxed,
)


CONTROL_STYLES = """input => {
    const style = getComputedStyle(input);
    const mark = getComputedStyle(input, '::after');
    return {
        border: style.borderTopColor,
        width: style.borderTopWidth,
        background: style.backgroundColor,
        image: style.backgroundImage,
        opacity: style.opacity,
        shadow: style.boxShadow,
        mark: mark.content === 'none' ? null : [mark.content, mark.borderColor, mark.borderWidth, mark.transform],
    };
}"""


class AlertIconBrowserTests(unittest.TestCase):
    def test_explicit_icon_dimensions_are_preserved(self):
        skip_if_browser_launch_is_sandboxed()
        css = compile_style(ROOT / "scss/moo-ui.scss")
        default_renderer = create_environment().globals["render_icon"]

        def render_icon(name, position):
            icon = ElementTree.fromstring(str(default_renderer("info", position)))
            if name == "framed-info":
                icon.set("width", "3rem")
                icon.set("height", "3rem")
            elif name == "rectangular-info":
                icon.set("width", "24")
                icon.set("height", "32")
            elif name == "width-only-info":
                icon.set("width", "24")
            elif name == "height-only-info":
                icon.set("height", "32")
            return Markup(ElementTree.tostring(icon, encoding="unicode"))

        markup = create_environment(icon_renderer=render_icon).from_string("""
            {% from "components/alert.html.jinja" import alert %}
            {% for icon in ["info", "framed-info", "rectangular-info", "width-only-info", "height-only-info"] %}
                {{ alert(icon, description="Original message", icon=icon, variant="info") }}
            {% endfor %}
        """).render()
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for theme, direction, width in (("light", "ltr", 1040), ("dark", "rtl", 390)):
                    with self.subTest(theme=theme, direction=direction):
                        context = new_case_context(browser, BrowserCase(
                            "alert-icon-dimensions", {"width": width, "height": 844}, theme, direction,
                        ))
                        try:
                            page = context.new_page()
                            evidence = BrowserEvidence(page)
                            page.set_content(
                                f'<html lang="en" dir="{direction}"><head><style>{css}</style></head>'
                                f'<body><main class="moo-ui bg-body p-4" data-bs-theme="{theme}">'
                                f'{markup}</main></body></html>',
                            )
                            dimensions = page.locator(".alert-icon svg").evaluate_all("""icons =>
                                icons.map(icon => {
                                    const rect = icon.getBoundingClientRect();
                                    return [rect.width, rect.height];
                                })""")
                            root_font_size = page.locator("html").evaluate("""root =>
                                parseFloat(getComputedStyle(root).fontSize)""")
                            expected_dimensions = [
                                [root_font_size, root_font_size],
                                [3 * root_font_size, 3 * root_font_size],
                                [24, 32],
                                [24, root_font_size],
                                [root_font_size, 32],
                            ]
                            self.assertEqual(len(dimensions), len(expected_dimensions))
                            for actual, expected in zip(dimensions, expected_dimensions):
                                for actual_size, expected_size in zip(actual, expected):
                                    self.assertAlmostEqual(actual_size, expected_size, delta=0.1)
                            self.assertTrue(page.evaluate("""() =>
                                document.documentElement.scrollWidth <= innerWidth"""))
                            evidence.assert_clean()
                        finally:
                            context.close()
            finally:
                browser.close()


class AlertCheckboxBrowserTests(unittest.TestCase):
    def test_semantic_border_preserves_control_states_and_keyboard_focus(self):
        skip_if_browser_launch_is_sandboxed()
        # Compile styles only; this contract neither rebuilds catalog assets
        # nor depends on the last local development package.
        css = compile_style(ROOT / "scss/moo-ui.scss")
        variants = ("info", "default", "destructive", "warning", "success")
        markup = create_environment().from_string("""
            {% from "components/alert.html.jinja" import alert %}
            {% from "components/checkbox.html.jinja" import checkbox %}
            {% from "components/switch.html.jinja" import switch %}
            {% from "components/radio_group.html.jinja" import radio_group %}
            {% macro controls(prefix) %}
                {% for state in ["normal", "checked", "mixed", "disabled", "invalid", "required"] %}
                    {{ checkbox(prefix ~ '-' ~ state, state,
                        checked=state == "checked", disabled=state == "disabled",
                        invalid=state == "invalid",
                        input_attrs="required" if state == "required" else "") }}
                {% endfor %}
                {{ switch(prefix ~ '-switch', "Switch") }}
                {{ radio_group(prefix ~ '-radio', "Radio", [
                    {"id": prefix ~ '-radio', "label": "Radio"}]) }}
            {% endmacro %}
            {{ controls("outside") }}
            {% for variant in variants %}
                {{ alert(variant, variant=variant, action=controls(variant)) }}
            {% endfor %}
        """).render(variants=variants)

        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for theme, direction, width in (("light", "ltr", 1040), ("dark", "rtl", 390)):
                    with self.subTest(theme=theme, direction=direction):
                        case = BrowserCase("alert-checkbox", {"width": width, "height": 844}, theme, direction)
                        context = new_case_context(browser, case)
                        try:
                            page = context.new_page()
                            evidence = BrowserEvidence(page)
                            page.set_content(
                                f'<html lang="en" dir="{direction}"><head><style>{css}</style></head>'
                                f'<body><main class="moo-ui bg-body p-4" data-bs-theme="{theme}" '
                                f'dir="{direction}">{markup}</main></body></html>',
                            )
                            page.evaluate("""() => {
                                for (const input of document.querySelectorAll('[id$="-mixed"]')) {
                                    input.indeterminate = true;
                                }
                            }""")
                            outside = {
                                state: page.locator(f"#outside-{state}").evaluate(CONTROL_STYLES)
                                for state in ("normal", "checked", "mixed", "disabled", "invalid", "required", "switch", "radio")
                            }
                            page.keyboard.press("Tab")
                            expect(page.locator("#outside-normal")).to_be_focused()
                            ring = page.locator("#outside-normal").evaluate(CONTROL_STYLES)["shadow"]
                            self.assertNotEqual(ring, "none")

                            for variant in variants:
                                with self.subTest(variant=variant):
                                    choice = page.locator(f"#{variant}-normal")
                                    foreground = choice.evaluate("input => getComputedStyle(input.closest('.alert')).color")
                                    for state in ("normal", "disabled"):
                                        style = page.locator(f"#{variant}-{state}").evaluate(CONTROL_STYLES)
                                        self.assertEqual(style["border"], foreground)
                                        for prop in ("width", "background", "image", "opacity", "mark"):
                                            self.assertEqual(style[prop], outside[state][prop])
                                    for state in ("checked", "mixed", "invalid", "required", "switch", "radio"):
                                        self.assertEqual(
                                            page.locator(f"#{variant}-{state}").evaluate(CONTROL_STYLES), outside[state],
                                        )
                                    choice.focus()
                                    self.assertEqual(choice.evaluate(CONTROL_STYLES)["shadow"], ring)
                                    outside_choice = page.locator("#outside-normal")
                                    outside_choice.focus()
                                    outside_choice.press("Space")
                                    checked = outside_choice.evaluate(CONTROL_STYLES)
                                    choice.press("Space")
                                    expect(choice).to_be_checked()
                                    self.assertEqual(choice.evaluate(CONTROL_STYLES), checked)
                                    choice.press("Space")
                                    expect(choice).not_to_be_checked()
                                    self.assertEqual(choice.evaluate(CONTROL_STYLES)["border"], foreground)
                                    outside_choice.press("Space")
                                    expect(outside_choice).not_to_be_checked()
                            evidence.assert_clean()
                        finally:
                            context.close()
            finally:
                browser.close()

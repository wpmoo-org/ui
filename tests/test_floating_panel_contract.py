from __future__ import annotations

import base64
import unittest

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT
from tests.helpers.browser_harness import launch_certification_browser


class FloatingPanelContractTests(unittest.TestCase):
    def test_macro_escapes_identifiers_labels_and_storage_keys(self) -> None:
        template = create_environment().from_string(
            '{% from "components/card.html.jinja" import floating_panel %}'
            '{% call floating_panel(id, title, storage_key=key) %}Content{% endcall %}'
        )
        output = template.render(id='panel"<&', title='Title"<&', key='key"<&')
        self.assertIn('id="panel&#34;&lt;&amp;"', output)
        self.assertIn('aria-label="Title&#34;&lt;&amp;"', output)
        self.assertIn('data-floating-panel-key="key&#34;&lt;&amp;"', output)
        self.assertIn(' hidden', output)
        self.assertNotIn(' hidden', template.render(id="panel", title="Title", key=""))
        for values in (
            dict(id="", title="Title", key=""),
            dict(id="two words", title="Title", key=""),
            dict(id="panel", title=" ", key=""),
            dict(id="panel", title="Title", key="x" * 257),
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                template.render(**values)

    def test_button_controls_are_independent_and_escaped(self) -> None:
        environment = create_environment()
        template = environment.from_string(
            '{% from "components/button.html.jinja" import button %}'
            '{{ button("Open", floating_panel_open=target) }}'
        )
        self.assertIn('data-floating-panel-open="panel&#34;&lt;&amp;"',
                      template.render(target='panel"<&'))
        for options in (
            'element="a"', 'type="submit"', 'toggle=true', 'dropdown=true',
            'collapse_target="other"', 'tooltip="Hint"', 'popover_content="Hint"',
            'dialog_target="other"', 'dismiss="modal"', 'toast_target="other"',
            'sheet_target="other"', 'floating_panel_dismiss="other"',
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                environment.from_string(
                    '{% from "components/button.html.jinja" import button %}'
                    '{{ button("Open", floating_panel_open="panel", ' + options + ') }}'
                ).render()

    def test_module_import_is_side_effect_free(self) -> None:
        import subprocess

        result = subprocess.run(
            ["node", "--input-type=module", "--eval",
             'import Panel from "./src/js/components/floating-panel.js"; '
             'if (typeof Panel.getOrCreateInstance !== "function" || '
             'typeof Panel.getInstance !== "function") process.exit(1);'],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_owner_isolation_storage_fallback_and_disposal(self) -> None:
        template = create_environment().from_string('''
            {% from "components/card.html.jinja" import floating_panel %}
            {% from "components/button.html.jinja" import button %}
            <!doctype html><html><body>
            <main class="moo-ui" data-bs-theme="light">
                {{ button("Unavailable", disabled=true, floating_panel_open="panel") }}
                {{ button("Open", floating_panel_open="panel") }}
                {{ button("Alternate", floating_panel_open="panel") }}
                {{ button("Outside dismiss", floating_panel_dismiss="panel") }}
                {% call floating_panel("panel", "Panel", storage_key="contract") %}
                    <div hidden>{{ button("Hidden action") }}</div>
                    {{ button("Dismiss", floating_panel_dismiss="panel") }}
                {% endcall %}
                <section class="moo-ui" data-bs-theme="dark">
                    {{ button("Other owner", floating_panel_open="panel") }}
                </section>
            </main></body></html>
        ''')
        encoded = base64.b64encode(
            (ROOT / "src/js/components/floating-panel.js").read_bytes()
        ).decode()
        module_url = "data:text/javascript;base64," + encoded
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                page = browser.new_page()
                page.route("http://floating.invalid/**", lambda route: route.fulfill(
                    body=template.render(), content_type="text/html"))
                page.goto("http://floating.invalid/probe")
                page.evaluate('''() => {
                    Object.defineProperty(window, "localStorage", {
                        get() { throw new DOMException("Blocked", "SecurityError"); },
                    });
                    const launcher = document.querySelector('[data-floating-panel-open]:not(:disabled)');
                    launcher.setAttribute("aria-controls", "original");
                    launcher.setAttribute("aria-expanded", "mixed");
                }''')
                expect(page.locator("#panel")).to_be_hidden()
                self.assertTrue(page.evaluate('''async url => {
                    const { default: Panel } = await import(url);
                    window.Panel = Panel;
                    const absent = Panel.getInstance(document.getElementById("panel"));
                    window.panel = Panel.getOrCreateInstance(document.getElementById("panel"));
                    return absent === null && Panel.getInstance(document.getElementById("panel")) === window.panel;
                }''', module_url))
                panel = page.locator("#panel")
                launcher = page.get_by_role("button", name="Open", exact=True)
                expect(panel).to_be_visible()
                expect(launcher).to_have_attribute("aria-controls", "panel")
                self.assertTrue(page.evaluate('''() =>
                    Panel.getOrCreateInstance(document.getElementById("panel")) === window.panel'''))
                page.get_by_role("button", name="Outside dismiss", exact=True).click()
                expect(panel).to_be_visible()
                page.get_by_role("button", name="Dismiss", exact=True).click()
                expect(panel).to_be_hidden()
                expect(launcher).to_be_focused()
                expect(launcher).to_have_attribute("aria-expanded", "false")
                page.get_by_role("button", name="Other owner", exact=True).click()
                expect(panel).to_be_hidden()
                alternate = page.get_by_role("button", name="Alternate", exact=True)
                alternate.click()
                page.get_by_role("button", name="Dismiss", exact=True).click()
                expect(alternate).to_be_focused()
                alternate.click()
                alternate.evaluate("element => element.disabled = true")
                page.get_by_role("button", name="Dismiss", exact=True).click()
                expect(launcher).to_be_focused()
                self.assertTrue(page.evaluate('''() => {
                    const previous = window.panel;
                    previous.dispose();
                    window.panel = Panel.getOrCreateInstance(document.getElementById("panel"));
                    previous.dispose();
                    previous.dispose();
                    return Panel.getOrCreateInstance(document.getElementById("panel")) === window.panel;
                }'''))
                expect(panel).to_have_attribute("data-floating-panel-ready", "true")
                expect(panel).to_be_hidden()
                launcher.click()
                expect(panel).to_be_visible()
                expect(page.get_by_role("button", name="Dismiss", exact=True)).to_be_focused()
                page.evaluate("window.panel.dispose()")
                self.assertTrue(page.evaluate('Panel.getInstance(document.getElementById("panel")) === null'))
                expect(launcher).to_have_attribute("aria-controls", "original")
                expect(launcher).to_have_attribute("aria-expanded", "mixed")
                expect(panel).not_to_have_attribute("data-floating-panel-ready", "true")
                self.assertIsNone(panel.get_attribute("data-floating-panel-state"))
                self.assertTrue(panel.evaluate("element => element.hidden"))
                launcher.click()
                expect(panel).to_be_hidden()
            finally:
                browser.close()

    def test_reinitialization_reads_cross_tab_preferences_and_preserves_unsaved_intent(self) -> None:
        template = create_environment().from_string('''
            {% from "components/card.html.jinja" import floating_panel %}
            {% from "components/button.html.jinja" import button %}
            <!doctype html><html><body><main class="moo-ui" data-bs-theme="light">
                {{ button("Open", floating_panel_open="panel") }}
                {% call floating_panel("panel", "Panel", storage_key="shared") %}
                    {{ button("Dismiss", floating_panel_dismiss="panel") }}
                {% endcall %}
            </main></body></html>
        ''')
        module_url = "data:text/javascript;base64," + base64.b64encode(
            (ROOT / "src/js/components/floating-panel.js").read_bytes()
        ).decode()
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                context = browser.new_context()
                context.route("http://floating.invalid/**", lambda route: route.fulfill(
                    body=template.render(), content_type="text/html"))
                first, second = context.new_page(), context.new_page()
                for page in (first, second):
                    page.goto("http://floating.invalid/probe")
                    page.evaluate('''async url => {
                        window.Panel = (await import(url)).default;
                        window.panel = Panel.getOrCreateInstance(document.getElementById("panel"));
                    }''', module_url)
                second.get_by_role("button", name="Dismiss", exact=True).click()
                expect(first.locator("#panel")).to_be_visible()
                first.evaluate('''() => {
                    window.panel.dispose();
                    window.panel = Panel.getOrCreateInstance(document.getElementById("panel"));
                }''')
                expect(first.locator("#panel")).to_be_hidden()
                second.get_by_role("button", name="Open", exact=True).click()
                first.evaluate('''() => {
                    window.panel.dispose();
                    window.panel = Panel.getOrCreateInstance(document.getElementById("panel"));
                }''')
                expect(first.locator("#panel")).to_be_visible()
                first.evaluate('''() => Object.defineProperty(Storage.prototype, "setItem", {
                    value() { throw new DOMException("Full", "QuotaExceededError"); },
                })''')
                first.get_by_role("button", name="Dismiss", exact=True).click()
                self.assertIsNone(first.evaluate("localStorage.getItem('moo-floating-panel:shared')"))
                first.evaluate('''() => {
                    window.panel.dispose();
                    window.panel = Panel.getOrCreateInstance(document.getElementById("panel"));
                }''')
                expect(first.locator("#panel")).to_be_hidden()
                first.get_by_role("button", name="Open", exact=True).click()
                expect(first.locator("#panel")).to_be_visible()
                context.close()
            finally:
                browser.close()

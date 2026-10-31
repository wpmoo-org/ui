from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase
from tests.helpers.browser_harness import launch_certification_browser


class FloatingPanelTests(CatalogTestCase):
    def test_local_dismissal_reloads_account_isolation_and_reopening(self):
        build = self.run_build()
        self.assertEqual(build.returncode, 0, build.stderr)
        template = create_environment().from_string('''
            {% from "components/card.html.jinja" import card, floating_panel %}
            {% from "components/button.html.jinja" import button %}
            {% from "components/collapsible.html.jinja" import collapsible %}
            <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
            <link rel="stylesheet" href="/moo-ui.css"></head><body>
            <main class="moo-ui" data-bs-theme="{{ theme }}" dir="{{ direction }}">
              {{ button("Get started", floating_panel_open="preparation") }}
              {% for item in range(100) %}<p>Background content {{ item }}</p>{% endfor %}
              {% call floating_panel("preparation", "Preparation", storage_key="account-" + account) %}
                {% call card(size="sm") %}
                  {{ collapsible("steps", "Preparation", "Saved task details", open=true) }}
                  {{ button("Dismiss", floating_panel_dismiss="preparation") }}
                {% endcall %}
              {% endcall %}
            </main>
            <script src="/bootstrap.js"></script>
            <script type="module">import FloatingPanel from '/floating-panel.js';
              window.panel = FloatingPanel.getOrCreateInstance(document.querySelector('aside'));
            </script></body></html>''')
        assets = {
            '/moo-ui.css': ((ROOT / 'dist/assets/css/moo-ui.css').read_bytes(), 'text/css'),
            '/bootstrap.js': ((ROOT / 'vendor/bootstrap/dist/js/bootstrap.bundle.min.js').read_bytes(), 'text/javascript'),
            '/floating-panel.js': ((ROOT / 'src/js/components/floating-panel.js').read_bytes(), 'text/javascript'),
        }
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for theme, direction, width in (('light', 'ltr', 1440), ('dark', 'rtl', 390)):
                    with self.subTest(theme=theme, direction=direction):
                        context = browser.new_context(viewport={'width': width, 'height': 844})
                        try:
                            page = context.new_page()

                            def serve(route):
                                parsed = urlparse(route.request.url)
                                if parsed.path == '/probe':
                                    account = parse_qs(parsed.query).get('account', ['a'])[0]
                                    route.fulfill(body=template.render(theme=theme, direction=direction, account=account), content_type='text/html')
                                elif parsed.path in assets:
                                    body, kind = assets[parsed.path]
                                    route.fulfill(body=body, content_type=kind)
                                else:
                                    route.fulfill(status=404, body='Unknown fixture asset')

                            page.route('http://floating.invalid/**', serve)
                            page.goto('http://floating.invalid/probe?account=a')
                            panel = page.locator('aside')
                            page.wait_for_function("!!document.querySelector('[data-floating-panel-ready]')")
                            expect(panel).to_be_visible()
                            self.assertEqual(panel.evaluate('e => getComputedStyle(e).position'), 'fixed')
                            box = panel.bounding_box()
                            self.assertGreaterEqual(box['x'], -1)
                            self.assertLessEqual(box['x'] + box['width'], width + 1)
                            page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)')
                            scroll = page.evaluate('window.scrollY')
                            page.get_by_role('button', name='Dismiss', exact=True).click()
                            expect(panel).to_be_hidden()
                            self.assertEqual(page.evaluate('window.scrollY'), scroll)
                            page.reload()
                            page.wait_for_function("!!document.querySelector('[data-floating-panel-ready]')")
                            expect(panel).to_be_hidden()
                            page.goto('http://floating.invalid/probe?account=b')
                            page.wait_for_function("!!document.querySelector('[data-floating-panel-ready]')")
                            expect(panel).to_be_visible()
                            page.goto('http://floating.invalid/probe?account=a')
                            page.wait_for_function("!!document.querySelector('[data-floating-panel-ready]')")
                            expect(panel).to_be_hidden()
                            page.get_by_role('button', name='Get started', exact=True).click()
                            expect(panel).to_be_visible()
                            self.assertIsNone(page.evaluate("localStorage.getItem('moo-floating-panel:account-a')"))
                            self.assertEqual(page.locator('[aria-modal=true],.modal-backdrop,.offcanvas-backdrop').count(), 0)
                        finally:
                            context.close()
            finally:
                browser.close()

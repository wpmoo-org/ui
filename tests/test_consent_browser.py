from __future__ import annotations

import json
from urllib.parse import quote, unquote, urlparse

from playwright.sync_api import expect, sync_playwright

from build import create_environment
from tests.helpers import ROOT, CatalogTestCase
from tests.helpers.browser_harness import launch_certification_browser
from tests.test_consent import CONFIG

PAGE = '''
{% from "blocks/consent.html.jinja" import consent_card, consent_placeholder, consent_trigger %}
<!doctype html><html dir="{{ direction }}"><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="/moo-ui.css"></head><body>
<div class="moo-ui" data-bs-theme="light" dir="{{ direction }}">
  {{ consent_card("consent", config) }}
  <main class="container py-4">
    <header>{{ consent_trigger("consent") }}</header>
    <div class="ratio ratio-16x9" data-consent-embed id="embed">
      <div>
        {{ consent_placeholder("video", "external_media", "Video", "Loads from Example.") }}
        <img alt="" data-consent-category="external_media" data-consent-src="/photo.svg" hidden>
        <iframe id="unsafe-frame" title="Unsafe" data-consent-category="external_media" data-consent-src="javascript:window.unsafeRan=1" hidden></iframe>
      </div>
    </div>
    <script type="text/plain" data-consent-category="statistics">window.statisticsLoaded = (window.statisticsLoaded || 0) + 1;</script>
  </main>
</div>
<script src="/bootstrap.js"></script>
<script type="module">
  import { initConsent } from "/consent.js";
  window.events = [];
  for (const name of ["ready", "change", "open", "close"]) {
    document.addEventListener(`moo:consent:${name}`, (event) => window.events.push([name, event.detail]));
  }
  window.consent = initConsent(document, { reload: () => { window.reloads = (window.reloads || 0) + 1; } });
  document.body.dataset.ready = "true";
</script>
</body></html>'''

PHOTO = b'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="9"></svg>'


class ConsentBrowserTests(CatalogTestCase):
    def test_consent_card_lifecycle(self) -> None:
        build = self.run_build()
        self.assertEqual(build.returncode, 0, build.stderr)
        template = create_environment().from_string(PAGE)
        assets = {
            "/moo-ui.css": ((ROOT / "dist/assets/css/moo-ui.css").read_bytes(), "text/css"),
            "/bootstrap.js": ((ROOT / "vendor/bootstrap/dist/js/bootstrap.bundle.min.js").read_bytes(), "text/javascript"),
            "/consent.js": ((ROOT / "src/js/components/consent.js").read_bytes(), "text/javascript"),
            "/photo.svg": (PHOTO, "image/svg+xml"),
        }

        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for direction, width in (("ltr", 1280), ("rtl", 375)):
                    with self.subTest(direction=direction, width=width):
                        context = browser.new_context(viewport={"width": width, "height": 800}, reduced_motion="reduce")
                        try:
                            self.run_lifecycle(context, template.render(config=CONFIG, direction=direction), assets)
                        finally:
                            context.close()
            finally:
                browser.close()

    def run_lifecycle(self, context, html: str, assets: dict) -> None:
        page = context.new_page()
        requested: list[str] = []
        foreign: list[str] = []

        def serve(route):
            path = urlparse(route.request.url).path
            requested.append(path)
            if path == "/probe":
                route.fulfill(body=html, content_type="text/html")
            elif path in assets:
                body, kind = assets[path]
                route.fulfill(body=body, content_type=kind)
            else:
                route.fulfill(status=404, body="Unknown fixture asset")

        def load() -> None:
            page.goto("http://consent.invalid/probe")
            page.wait_for_function("document.body.dataset.ready === 'true'")

        def record() -> dict | None:
            for cookie in context.cookies():
                if cookie["name"] == "moo_consent":
                    return json.loads(unquote(cookie["value"]))
            return None

        page.route("http://consent.invalid/**", serve)
        page.on("request", lambda request: foreign.append(request.url)
                if not request.url.startswith(("http://consent.invalid/", "data:")) else None)
        card = page.locator("#consent")
        statistics = page.locator("#consent-category-statistics")
        media = page.locator("#consent-category-external_media")

        # First visit: shown, nothing optional loaded, focus not taken.
        load()
        expect(card).to_be_visible()
        expect(statistics).not_to_be_checked()
        expect(media).not_to_be_checked()
        self.assertFalse(page.evaluate("document.querySelector('#consent').contains(document.activeElement)"))
        self.assertIsNone(page.evaluate("window.statisticsLoaded ?? null"))
        self.assertNotIn("/photo.svg", requested)
        page.keyboard.press("Escape")
        expect(card).to_be_visible()

        # Save choices with one category on.
        statistics.check()
        page.locator("#consent-save").click()
        expect(card).to_be_hidden()
        stored = record()
        self.assertEqual(stored["v"], 1)
        self.assertEqual(stored["r"], CONFIG["revision"])
        self.assertEqual(stored["c"], {"statistics": 1, "external_media": 0})
        self.assertEqual(page.evaluate("window.statisticsLoaded"), 1)
        self.assertNotIn("/photo.svg", requested)
        change = page.evaluate("window.events.filter(([name]) => name === 'change').at(-1)[1]")
        self.assertEqual(change["granted"], ["statistics"])
        self.assertEqual(change["source"], "save")

        # A reload keeps the choice and runs the gate once.
        load()
        expect(card).to_be_hidden()
        self.assertEqual(page.evaluate("window.statisticsLoaded"), 1)
        self.assertTrue(page.evaluate("window.consent.granted('statistics') && window.consent.granted('functional')"))

        # Placeholder: Load activates only this embed and stores nothing.
        page.locator("#video-load").click()
        expect(page.locator("img[data-consent-category]")).to_be_visible()
        self.assertEqual(record()["c"]["external_media"], 0)

        # The trigger reopens with stored choices, traps focus, Escape returns it.
        trigger = page.locator("[data-consent-open]")
        trigger.click()
        expect(card).to_be_visible()
        expect(page.locator("#consent-title")).to_be_focused()
        expect(statistics).to_be_checked()
        for _ in range(20):
            page.keyboard.press("Tab")
            self.assertTrue(page.evaluate("document.querySelector('#consent').contains(document.activeElement)"))
        page.keyboard.press("Escape")
        expect(card).to_be_hidden()
        expect(trigger).to_be_focused()

        # Withdrawal removes the category's first-party cookies and reloads.
        context.add_cookies([{"name": "_pk_id.1", "value": "x", "url": "http://consent.invalid/"}])
        trigger.click()
        page.locator("#consent-decline").click()
        self.assertEqual(record()["c"], {"statistics": 0, "external_media": 0})
        self.assertEqual(page.evaluate("window.reloads"), 1)
        self.assertNotIn("_pk_id.1", [cookie["name"] for cookie in context.cookies()])

        # A new revision asks again, with nothing pre-ticked.
        stale = {**record(), "r": "000000000000", "c": {"statistics": 1, "external_media": 1}}
        page.evaluate("value => { document.cookie = `moo_consent=${value}; Path=/`; }", quote(json.dumps(stale)))
        load()
        expect(card).to_be_visible()
        expect(statistics).not_to_be_checked()
        self.assertFalse(page.evaluate("window.consent.granted('statistics')"))

        # Accept all grants every optional category in place; a failing site
        # callback does not stop the save.
        page.evaluate("window.consent.whenGranted('external_media', () => { throw new Error('site bug'); })")
        page.locator("#consent-accept").click()
        self.assertEqual(page.evaluate("window.events.filter(([name]) => name === 'change').at(-1)[1].source"), "accept-all")
        expect(page.locator("img[data-consent-category]")).to_be_visible()
        expect(page.locator("[data-consent-placeholder]")).to_be_hidden()
        self.assertEqual(record()["c"], {"statistics": 1, "external_media": 1})
        # Only web addresses are activated; a javascript: source stays inert.
        self.assertIsNone(page.locator("#unsafe-frame").get_attribute("src"))
        self.assertIsNone(page.evaluate("window.unsafeRan ?? null"))
        self.assertEqual(foreign, [])

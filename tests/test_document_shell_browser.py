"""Document shell mode: the document scrolls and the footer follows the content."""

import unittest
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from build import create_environment
from tests.helpers.browser_harness import BrowserEvidence, launch_certification_browser


ROOT = Path(__file__).resolve().parents[1]
MEASURE = """
() => {
  const root = document.querySelector('[data-layout="app"]');
  const main = root.querySelector('[data-slot="page"] > main');
  const footer = root.querySelector('[data-slot="page"] > footer');
  return {
    mode: root.dataset.shellMode,
    rootOverflow: getComputedStyle(root).overflow,
    mainOverflowY: getComputedStyle(main).overflowY,
    mainScrollTop: main.scrollTop,
    documentScrollable: document.documentElement.scrollHeight > document.documentElement.clientHeight,
    footerTop: footer.getBoundingClientRect().top,
    footerBottom: footer.getBoundingClientRect().bottom,
    innerHeight: window.innerHeight,
  };
}
"""


class DocumentShellBrowserTests(unittest.TestCase):
    def test_document_scrolls_and_footer_follows_content(self):
        html = create_environment().from_string(
            (ROOT / "tests/fixtures/certification/layout-app.html.jinja").read_text()
        ).render(fixture_shell_mode="document", fixture_navigation="none")
        assets = {
            "/document.html": (html.encode(), "text/html"),
            "/dist/assets/css/moo-ui.css": ((ROOT / "dist/assets/css/moo-ui.css").read_bytes(), "text/css"),
            "/vendor/bootstrap/dist/js/bootstrap.bundle.min.js": (
                (ROOT / "vendor/bootstrap/dist/js/bootstrap.bundle.min.js").read_bytes(),
                "text/javascript",
            ),
            "/dist/js/sidebar.js": ((ROOT / "dist/js/sidebar.js").read_bytes(), "text/javascript"),
        }
        with sync_playwright() as playwright:
            browser = launch_certification_browser(playwright)
            try:
                for width, height in ((1280, 720), (390, 480)):
                    for short in (False, True):
                        with self.subTest(width=width, short=short):
                            context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce")
                            try:
                                page = context.new_page()
                                evidence = BrowserEvidence(page)

                                def serve(route):
                                    path = urlparse(route.request.url).path
                                    if path in assets:
                                        body, content_type = assets[path]
                                        route.fulfill(body=body, content_type=content_type)
                                    else:
                                        route.fulfill(status=404, body="Missing fixture asset")

                                page.route("http://moo-core.invalid/**", serve)
                                page.goto("http://moo-core.invalid/document.html", wait_until="load")
                                page.wait_for_function("document.body.dataset.layoutReady === 'true'")
                                if short:
                                    page.add_style_tag(content=".layout-certification-main { min-height: 0; }")
                                result = page.evaluate(MEASURE)
                                self.assertEqual(result["mode"], "document")
                                self.assertEqual(result["rootOverflow"], "visible")
                                self.assertEqual(result["mainOverflowY"], "visible")
                                if short:
                                    self.assertFalse(result["documentScrollable"])
                                    self.assertAlmostEqual(result["footerBottom"], result["innerHeight"], delta=1)
                                else:
                                    self.assertTrue(result["documentScrollable"])
                                    self.assertGreater(result["footerTop"], result["innerHeight"])
                                    page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
                                    result = page.evaluate(MEASURE)
                                    self.assertEqual(result["mainScrollTop"], 0)
                                    self.assertAlmostEqual(result["footerBottom"], result["innerHeight"], delta=1)
                                evidence.assert_clean()
                            finally:
                                context.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()

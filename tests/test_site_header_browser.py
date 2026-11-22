import unittest

from playwright.sync_api import sync_playwright

from tests.helpers.browser_harness import (
    BrowserEvidence,
    launch_certification_browser,
    serve_repository,
    skip_if_browser_launch_is_sandboxed,
)

TOLERANCE = 2


class SiteHeaderBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        skip_if_browser_launch_is_sandboxed()
        cls.server = serve_repository()
        cls.base_url = cls.server.__enter__()
        cls.manager = sync_playwright()
        cls.playwright = cls.manager.__enter__()
        cls.browser = launch_certification_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.manager.__exit__(None, None, None)
        cls.server.__exit__(None, None, None)

    def _page(self, slug, width):
        page = self.browser.new_page(viewport={"width": width, "height": 800})
        evidence = BrowserEvidence(page)
        response = page.goto(
            f"{self.base_url}/site-dist/blocks/previews/{slug}/", wait_until="networkidle"
        )
        self.assertTrue(response.ok)
        return page, evidence

    def _wide_geometry(self, slug):
        page, evidence = self._page(slug, 1280)
        try:
            return page.evaluate("""() => {
              const rect = el => { const r = el.getBoundingClientRect(); return {left: r.left, right: r.right}; };
              const nav = document.querySelector('nav.navbar');
              const bar = nav.querySelector(':scope > .container');
              const brand = bar.querySelector(':scope > .navbar-brand');
              return {
                dir: getComputedStyle(nav).direction,
                container: rect(bar),
                brand: rect(brand),
                mark: rect(brand.querySelector('.sidebar-brand-mark')),
                text: rect(brand.querySelector('.sidebar-brand-mark ~ span')),
                action: rect(bar.querySelector('.offcanvas-body .btn-primary')),
                togglerVisible: getComputedStyle(bar.querySelector('[data-bs-toggle=offcanvas]')).display !== 'none',
              };
            }""")
        finally:
            evidence.assert_clean()
            page.close()

    def test_ltr_and_rtl_wide_headers_mirror_each_other(self):
        ltr = self._wide_geometry("site-header")
        rtl = self._wide_geometry("site-header-rtl")
        self.assertEqual((ltr["dir"], rtl["dir"]), ("ltr", "rtl"))
        for geometry in (ltr, rtl):
            self.assertFalse(geometry["togglerVisible"])
        # The lockup follows the page direction: the mark sits at its inline start.
        self.assertLess(ltr["mark"]["right"], ltr["text"]["left"] + TOLERANCE)
        self.assertGreater(rtl["mark"]["left"] + TOLERANCE, rtl["text"]["right"])
        self.assertAlmostEqual(ltr["container"]["left"], rtl["container"]["left"], delta=TOLERANCE)
        self.assertAlmostEqual(ltr["container"]["right"], rtl["container"]["right"], delta=TOLERANCE)
        # Brand at the inline-start edge, actions at the inline-end edge.
        self.assertAlmostEqual(ltr["brand"]["left"], ltr["container"]["left"] + 12, delta=16)
        self.assertAlmostEqual(
            rtl["container"]["right"] - rtl["brand"]["right"],
            ltr["brand"]["left"] - ltr["container"]["left"],
            delta=TOLERANCE,
        )
        self.assertAlmostEqual(
            ltr["container"]["right"] - ltr["action"]["right"],
            rtl["action"]["left"] - rtl["container"]["left"],
            delta=TOLERANCE,
        )
        self.assertLess(ltr["brand"]["right"], ltr["action"]["left"])
        self.assertLess(rtl["action"]["right"], rtl["brand"]["left"])

    def _open_drawer(self, slug):
        page, evidence = self._page(slug, 390)
        page.locator("nav.navbar [data-bs-toggle=offcanvas]").click()
        page.wait_for_selector('.offcanvas.show:not(.showing)')
        geometry = page.evaluate("""() => {
          const drawer = document.querySelector('.offcanvas.show');
          const close = drawer.querySelector('.offcanvas-header .btn-close').getBoundingClientRect();
          const d = drawer.getBoundingClientRect();
          const cs = getComputedStyle(drawer);
          return {viewport: innerWidth, borderLeft: parseFloat(cs.borderLeftWidth), borderRight: parseFloat(cs.borderRightWidth), drawer: {left: d.left, right: d.right},
                  closeCenter: (close.left + close.right) / 2, drawerCenter: (d.left + d.right) / 2};
        }""")
        evidence.assert_clean()
        page.close()
        return geometry

    def test_drawer_opens_from_the_inline_end_edge_with_close_at_inline_end(self):
        ltr = self._open_drawer("site-header")
        rtl = self._open_drawer("site-header-rtl")
        self.assertAlmostEqual(ltr["drawer"]["right"], ltr["viewport"], delta=TOLERANCE)
        self.assertGreater(ltr["closeCenter"], ltr["drawerCenter"])
        self.assertAlmostEqual(rtl["drawer"]["left"], 0, delta=TOLERANCE)
        self.assertLess(rtl["closeCenter"], rtl["drawerCenter"])
        # The border sits on the content-facing edge in both directions.
        self.assertGreater(rtl["borderRight"], 0)
        self.assertEqual(rtl["borderLeft"], 0)
        self.assertGreater(ltr["borderLeft"], 0)
        self.assertEqual(ltr["borderRight"], 0)


if __name__ == "__main__":
    unittest.main()

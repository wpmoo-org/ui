from __future__ import annotations

from tests.helpers import DIST, CatalogTestCase


class BuildTests(CatalogTestCase):
    def test_build_creates_static_entrypoints(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((DIST / "index.html").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.css").is_file())
        self.assertTrue((DIST / "assets/css/moo-ui.min.css").is_file())
        self.assertTrue((DIST / "assets/css/catalog.css").is_file())
        self.assertTrue((DIST / "assets/css/moo.css").is_file())
        self.assertTrue((DIST / "assets/css/moo.min.css").is_file())
        self.assertFalse((DIST / "assets/css/moo-core.css").exists())
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js").is_file()
        )
        self.assertTrue(
            (DIST / "assets/js/bootstrap.bundle.min.js.map").is_file()
        )
        self.assertTrue((DIST / "llms.txt").is_file())
        self.assertTrue((DIST / "sitemap.xml").is_file())
        self.assertTrue((DIST / "robots.txt").is_file())

    def test_build_writes_canonical_sitemap(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
        robots = (DIST / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/components/button/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/blocks/sidebar-floating/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/utils/scroll-fade/</loc>",
            sitemap,
        )
        self.assertIn(
            "<loc>https://ui.wpmoo.org/llms.txt</loc>",
            sitemap,
        )
        self.assertNotIn(".html", sitemap)
        self.assertNotIn("/blocks/previews/", sitemap)
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        self.assertIn(
            "Sitemap: https://ui.wpmoo.org/sitemap.xml",
            robots,
        )

    def test_build_uses_one_shared_catalog_shell(self) -> None:
        result = self.run_build()

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.read_output("index.html")
        self.assertEqual(index.count('data-moo-shell="catalog"'), 1)
        self.assertEqual(index.count("<header"), 1)
        self.assertEqual(index.count("<footer"), 0)
        self.assertIn('href="components/button/"', index)
        self.assertIn('href="components/card/"', index)
        self.assertIn('id="main-content"', index)
        self.assertIn('href="#main-content"', index)
        self.assertIn('id="main-content" tabindex="-1"', index)

        introduction = self.read_output("introduction.html")
        self.assertEqual(introduction.count("<footer"), 0)

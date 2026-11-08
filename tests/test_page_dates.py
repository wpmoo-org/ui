from __future__ import annotations

import importlib.util
import json
import re
import unittest
import xml.etree.ElementTree as ET

import build as site_build

from tests.helpers import ROOT, SITE_DIST, CatalogTestCase

_SPEC = importlib.util.spec_from_file_location("record_page_dates", ROOT / "scripts/record-page-dates.py")
record_page_dates = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(record_page_dates)

SITEMAP_NS = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class PageContentHashTests(unittest.TestCase):
    """The hash follows page content, not navigation around it."""

    PAGE = (
        '<body><nav>Catalog</nav><main id="main-content">'
        "<h1>Item</h1><p>Show a row.</p>"
        '<img src="../assets/images/item.webp?v=1" alt="">'
        '<nav class="moo-doc-pagination"><a href="../empty/">Empty</a></nav>'
        '<aside class="moo-doc-toc"><nav><a href="#usage">Usage</a></nav></aside>'
        "<script>window.x = 1</script>"
        "</main></body>"
    )

    def test_navigation_outline_scripts_and_asset_versions_are_ignored(self):
        other = (
            self.PAGE.replace("Empty", "Input")
            .replace("Usage", "Usage and more")
            .replace("window.x = 1", "window.x = 2")
            .replace("?v=1", "?v=2")
            .replace("<nav>Catalog</nav>", "<nav>Catalog menu</nav>")
        )
        self.assertEqual(record_page_dates.page_hash(self.PAGE), record_page_dates.page_hash(other))

    def test_text_and_media_changes_change_the_hash(self):
        for changed in (
            self.PAGE.replace("Show a row.", "Show a list row."),
            self.PAGE.replace("item.webp", "item-v2.webp"),
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(record_page_dates.page_hash(self.PAGE), record_page_dates.page_hash(changed))

    def test_stale_routes_report_changed_and_removed_pages(self):
        registry = {"a/": {"updated": "2026-01-01", "hash": "h1"}, "gone/": {"updated": "2026-01-01", "hash": "h3"}}
        self.assertEqual(record_page_dates.stale_routes(registry, {"a/": "h2", "b/": "h4"}), ["a/", "b/", "gone/"])
        self.assertEqual(record_page_dates.stale_routes({"a/": {"hash": "h1"}}, {"a/": "h1"}), [])


class PageDatesContractTests(CatalogTestCase):
    """Recorded dates match the built pages and reach sitemap, page and JSON-LD."""

    @classmethod
    def setUpClass(cls) -> None:
        result = cls().run_build()
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.registry = json.loads(site_build.PAGE_DATES.read_text(encoding="utf-8"))

    def test_recorded_dates_match_current_page_content(self):
        stale = record_page_dates.stale_routes(self.registry, record_page_dates.current_hashes())
        self.assertEqual(stale, [], "run scripts/record-page-dates.py --write")
        for route, entry in self.registry.items():
            with self.subTest(route=route):
                self.assertRegex(entry["updated"], r"^\d{4}-\d{2}-\d{2}$")

    def test_sitemap_lastmod_comes_from_the_registry(self):
        xml = (SITE_DIST / "sitemap.xml").read_text(encoding="utf-8")
        lastmod = {
            url.findtext("sitemap:loc", namespaces=SITEMAP_NS): url.findtext("sitemap:lastmod", default="", namespaces=SITEMAP_NS)
            for url in ET.fromstring(xml.encode()).findall("sitemap:url", SITEMAP_NS)
        }
        expected = {site_build.canonical_url(route): entry["updated"] for route, entry in self.registry.items()}
        self.assertEqual({url: date for url, date in lastmod.items() if date}, expected)
        # The Sitemap page lists the dates themselves and stays undated.
        self.assertEqual(lastmod[site_build.canonical_url("sitemap/")], "")

    def test_component_article_carries_date_modified(self):
        html = (SITE_DIST / "components/item/index.html").read_text(encoding="utf-8")
        article = next(
            item
            for item in map(json.loads, re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL))
            if item["@type"] == "TechArticle"
        )
        self.assertEqual(article["dateModified"], self.registry["components/item/"]["updated"])


if __name__ == "__main__":
    unittest.main()

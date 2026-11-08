from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin

from tests.helpers import SITE_DIST, CatalogTestCase

SITEMAP_NS = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
XSL_NS = "http://www.w3.org/1999/XSL/Transform"


class SitemapPageTests(CatalogTestCase):
    """The XML sitemap stays machine-readable; people get a styled view and a page."""

    @classmethod
    def setUpClass(cls) -> None:
        result = cls().run_build()
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.xml = (SITE_DIST / "sitemap.xml").read_text(encoding="utf-8")
        cls.entries = {
            url.findtext("sitemap:loc", namespaces=SITEMAP_NS): url.findtext(
                "sitemap:lastmod", default="", namespaces=SITEMAP_NS
            )
            for url in ET.fromstring(cls.xml.encode()).findall("sitemap:url", SITEMAP_NS)
        }

    def test_xml_sitemap_references_its_published_stylesheet(self) -> None:
        lines = self.xml.splitlines()
        self.assertEqual(lines[0], '<?xml version="1.0" encoding="UTF-8"?>')
        self.assertEqual(lines[1], '<?xml-stylesheet type="text/xsl" href="sitemap.xsl"?>')
        stylesheet = ET.parse(SITE_DIST / "sitemap.xsl").getroot()
        self.assertEqual(stylesheet.tag, f"{{{XSL_NS}}}stylesheet")
        source = (SITE_DIST / "sitemap.xsl").read_text(encoding="utf-8")
        # The styled view links the HTML page and stays out of search results.
        self.assertIn('<meta name="robots" content="noindex, follow"/>', source)
        self.assertIn('href="sitemap/"', source)

    def test_sitemap_page_lists_every_sitemap_page_with_its_date(self) -> None:
        page_url = "https://ui.wpmoo.org/sitemap/"
        self.assertIn(page_url, self.entries)
        html = (SITE_DIST / "sitemap/index.html").read_text(encoding="utf-8")
        tables = re.findall(r"<table.*?</table>", html, re.DOTALL)
        rows = [row for table in tables for row in re.findall(r"<tr>(.*?)</tr>", table, re.DOTALL)[1:]]
        listed = {}
        for row in rows:
            href = re.search(r'<a href="([^"]+)"', row).group(1)
            date = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)[-1]
            listed[urljoin(page_url, href)] = re.sub(r"<[^>]+>", "", date).strip()
        expected = {
            url: (lastmod or "—")
            for url, lastmod in self.entries.items()
            if not url.endswith(".txt")
        }
        self.assertEqual(listed, expected)

    def test_sitemap_page_is_linked_from_the_catalog_navigation(self) -> None:
        html = (SITE_DIST / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r'<a[^>]*href="sitemap/"')

from __future__ import annotations

import json
import re
import unittest
from html import unescape
from unittest import mock

import build as site_build

from tests.helpers import SITE_DIST, CatalogTestCase

GUIDES = json.loads(
    (site_build.SITE_REGISTRY / "component-guides.json").read_text(encoding="utf-8")
)
JSON_LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


def structured_data(html: str) -> list[dict[str, object]]:
    return [json.loads(match) for match in JSON_LD.findall(html)]


class ComponentGuideContractTests(CatalogTestCase):
    """Site usage guides: registry facts reach the rendered page and metadata."""

    @classmethod
    def setUpClass(cls) -> None:
        result = cls().run_build()
        if result.returncode != 0:
            raise AssertionError(result.stderr)

    def test_guided_component_renders_guide_before_reference(self) -> None:
        for slug, guide in GUIDES.items():
            with self.subTest(slug=slug):
                html = self.read_output(f"components/{slug}/index.html")
                section = re.search(
                    r"<section[^>]*data-moo-component-guide[^>]*>(.*?)</section>",
                    html,
                    re.DOTALL,
                )
                self.assertIsNotNone(section)
                body = section.group(1)
                self.assertIn(f'aria-labelledby="{slug}-guide-title"', section.group(0))
                reference = html.find("data-moo-component-reference")
                self.assertLess(section.start(), reference)

                # Every keyboard key renders through the Kbd component.
                keys = [key for entry in guide.get("keyboard", []) for key in entry["keys"]]
                self.assertEqual(re.findall(r"<kbd>([^<]*)</kbd>", body), keys)

                # Related and alternative components link to catalog pages.
                linked = set(re.findall(r'href="(?:\.\./)*components/([a-z-]+)/"', body))
                expected = set(guide.get("related", [])) | {
                    item["slug"] for item in guide.get("whenNotToUse", []) if item.get("slug")
                }
                self.assertEqual(linked, expected)

    def test_guided_component_uses_guide_title_and_description(self) -> None:
        for slug, guide in GUIDES.items():
            with self.subTest(slug=slug):
                html = self.read_output(f"components/{slug}/index.html")
                title = re.search(r"<title>([^<]*)</title>", html).group(1)
                self.assertEqual(unescape(title), f"{guide['metaTitle']} — Moo UI")
                description = re.search(r'<meta name="description" content="([^"]*)">', html)
                self.assertEqual(unescape(description.group(1)), guide["metaDescription"])

    def test_unguided_component_keeps_registry_metadata(self) -> None:
        catalog = {entry["slug"]: entry for entry in site_build.load_catalog()}
        slug = next(slug for slug in sorted(catalog) if slug not in GUIDES)
        html = self.read_output(f"components/{slug}/index.html")
        self.assertNotIn("data-moo-component-guide", html)
        title = re.search(r"<title>([^<]*)</title>", html).group(1)
        self.assertEqual(unescape(title), f"{catalog[slug]['label']} — Moo UI")

    def test_component_pages_carry_article_and_breadcrumb_data(self) -> None:
        html = self.read_output("components/accordion/index.html")
        canonical = "https://ui.wpmoo.org/components/accordion/"
        items = {item["@type"]: item for item in structured_data(html)}
        self.assertEqual(set(items), {"TechArticle", "BreadcrumbList"})
        self.assertEqual(items["TechArticle"]["url"], canonical)
        trail = [entry["item"] for entry in items["BreadcrumbList"]["itemListElement"]]
        self.assertEqual(
            trail,
            ["https://ui.wpmoo.org/", "https://ui.wpmoo.org/components/", canonical],
        )

    def test_home_page_describes_the_website(self) -> None:
        items = structured_data(self.read_output("index.html"))
        self.assertEqual([item["@type"] for item in items], ["WebSite"])
        self.assertEqual(items[0]["url"], "https://ui.wpmoo.org/")

    def test_sitemap_dates_only_pages_with_a_declared_update(self) -> None:
        sitemap = (SITE_DIST / "sitemap.xml").read_text(encoding="utf-8")
        entries = re.findall(r"<url>(.*?)</url>", sitemap, re.DOTALL)
        dated = {
            re.search(r"<loc>([^<]*)</loc>", entry).group(1): re.search(
                r"<lastmod>([^<]*)</lastmod>", entry
            ).group(1)
            for entry in entries
            if "<lastmod>" in entry
        }
        self.assertEqual(
            dated,
            {
                f"https://ui.wpmoo.org/components/{slug}/": guide["updated"]
                for slug, guide in GUIDES.items()
            },
        )

    def test_non_indexed_pages_carry_no_structured_data(self) -> None:
        for path in ("acceptance/rc2/index.html", "404.html"):
            with self.subTest(path=path):
                html = (SITE_DIST / path).read_text(encoding="utf-8")
                self.assertEqual(structured_data(html), [])


class ComponentGuideRegistryTests(unittest.TestCase):
    """The loader refuses guides that point at components the catalog lacks."""

    LABELS = {"accordion": "Accordion", "tabs": "Tabs"}

    def load(self, guides: dict[str, object]) -> dict[str, dict[str, object]]:
        payload = json.dumps(guides)
        with mock.patch.object(site_build.Path, "read_text", return_value=payload), \
                mock.patch.object(site_build.Path, "exists", return_value=True):
            return site_build.load_component_guides(self.LABELS)

    def guide(self, **overrides: object) -> dict[str, object]:
        return {
            "updated": "2026-11-08",
            "metaTitle": "Title",
            "metaDescription": "Description",
            "summary": "Summary",
            "whenToUse": ["Use"],
            **overrides,
        }

    def test_valid_guide_gains_the_catalog_label(self) -> None:
        guides = self.load({"accordion": self.guide(related=["tabs"])})
        self.assertEqual(guides["accordion"]["label"], "Accordion")

    def test_unknown_component_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown component 'drawer'"):
            self.load({"drawer": self.guide()})

    def test_unknown_link_target_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "links unknown component 'drawer'"):
            self.load({"accordion": self.guide(related=["drawer"])})
        with self.assertRaisesRegex(ValueError, "links unknown component 'drawer'"):
            self.load({"accordion": self.guide(whenNotToUse=[{"text": "x", "slug": "drawer"}])})

    def test_update_date_must_be_iso(self) -> None:
        with self.assertRaisesRegex(ValueError, "updated must be YYYY-MM-DD"):
            self.load({"accordion": self.guide(updated="08.11.2026")})

    def test_missing_required_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "accordion needs summary"):
            self.load({"accordion": self.guide(summary="")})


if __name__ == "__main__":
    unittest.main()

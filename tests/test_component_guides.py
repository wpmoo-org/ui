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

    @staticmethod
    def section(html: str, marker: str) -> re.Match[str] | None:
        return re.search(
            rf"<section[^>]*{marker}[^>]*>(.*?)</section>",
            html,
            re.DOTALL,
        )

    def test_guide_about_precedes_usage(self) -> None:
        # The about part opens the page: after the first example, before Usage.
        for slug, guide in GUIDES.items():
            with self.subTest(slug=slug):
                html = self.read_output(f"components/{slug}/index.html")
                about = self.section(html, r"data-moo-component-guide(?=[\s>])")
                self.assertIsNotNone(about)
                self.assertIn(f'aria-labelledby="{slug}-guide-title"', about.group(0))
                # The page outline lists the section by its short label.
                self.assertRegex(
                    html,
                    rf'<a[^>]*href="#{slug}-guide-title"[^>]*>(?:\s|<span>)*About(?:\s|</span>)*</a>',
                )
                usage = re.search(r'<h2[^>]*id="usage"', html)
                self.assertIsNotNone(usage)
                self.assertLess(about.start(), usage.start())

                alternatives = {
                    item["slug"] for item in guide.get("whenNotToUse", []) if item.get("slug")
                }
                linked = set(re.findall(r'href="(?:\.\./)*components/([a-z-]+)/"', about.group(1)))
                self.assertEqual(linked, alternatives)

    def test_guide_details_close_the_page_before_reference(self) -> None:
        for slug, guide in GUIDES.items():
            with self.subTest(slug=slug):
                html = self.read_output(f"components/{slug}/index.html")
                details = self.section(html, "data-moo-component-guide-details")
                if not guide.get("keyboard") and not guide.get("related"):
                    self.assertIsNone(details)
                    continue
                self.assertIsNotNone(details)
                self.assertLess(details.start(), html.find("data-moo-component-reference"))

                # Every keyboard key renders through the Kbd component.
                keys = [key for entry in guide.get("keyboard", []) for key in entry["keys"]]
                self.assertEqual(re.findall(r"<kbd>([^<]*)</kbd>", details.group(1)), keys)

                linked = set(re.findall(r'href="(?:\.\./)*components/([a-z-]+)/"', details.group(1)))
                self.assertEqual(linked, set(guide.get("related", [])))

    def test_guided_component_uses_guide_title_and_description(self) -> None:
        for slug, guide in GUIDES.items():
            with self.subTest(slug=slug):
                html = self.read_output(f"components/{slug}/index.html")
                title = re.search(r"<title>([^<]*)</title>", html).group(1)
                self.assertEqual(unescape(title), f"{guide['metaTitle']} — Moo UI")
                description = re.search(r'<meta name="description" content="([^"]*)">', html)
                self.assertEqual(unescape(description.group(1)), guide["metaDescription"])

    def test_unguided_component_keeps_registry_metadata(self) -> None:
        # Without a guide entry, a component page falls back to the Core
        # registry label and description.
        catalog = site_build.load_catalog()
        entry = next(item for item in catalog if item["slug"] == "badge")
        metadata = site_build.page_metadata(
            site_build.PAGES / "components/badge.html.jinja",
            site_build.Path("components/badge.html"),
            [],
            catalog,
            [],
            [],
            [],
            guides={},
        )
        self.assertEqual(metadata["title"], f"{entry['label']} — Moo UI")
        self.assertEqual(metadata["description"], entry["description"])

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

    def test_missing_required_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "accordion needs summary"):
            self.load({"accordion": self.guide(summary="")})


if __name__ == "__main__":
    unittest.main()

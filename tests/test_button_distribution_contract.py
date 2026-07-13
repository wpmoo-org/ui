from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ButtonHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class TestButtonDistributionContract(unittest.TestCase):
    def setUp(self):
        self.html_path = ROOT / "html/components/button.html"
        self.css_path = ROOT / "moo_ui/static/src/components/button/button.css"

    def test_standalone_html_loads_shared_css_and_button_api(self):
        source = self.html_path.read_text()
        parser = ButtonHtmlParser()
        parser.feed(source)

        links = [attrs.get("href", "") for tag, attrs in parser.tags if tag == "link"]
        self.assertTrue(any("bootstrap@5.3.3" in href for href in links))
        self.assertIn("../../moo_ui/static/src/tokens/tokens.css", links)
        self.assertIn("../../moo_ui/static/src/components/button/button.css", links)

        classes = " ".join(attrs.get("class", "") for _, attrs in parser.tags)
        for marker in (
            "moo-ui",
            "btn",
            "btn-primary",
            "btn-outline-secondary",
            "btn-ghost",
            "btn-danger",
            "btn-secondary",
            "btn-link",
            "btn-xs",
            "btn-icon-xs",
            "btn-icon-sm",
            "btn-icon-lg",
            "rounded-pill",
        ):
            self.assertIn(marker, classes)
        self.assertNotIn("moo-button", classes)

        buttons = [attrs for tag, attrs in parser.tags if tag == "button"]
        self.assertTrue(any("disabled" in attrs for attrs in buttons))
        self.assertTrue(any(attrs.get("aria-label") == "Add item" for attrs in buttons))
        self.assertIn('dir="rtl"', source)
        self.assertIn('data-icon="inline-start"', source)
        self.assertIn('data-icon="inline-end"', source)

    def test_distribution_does_not_ship_react_tailwind_or_odoo_selectors(self):
        source = self.html_path.read_text().lower()
        css = self.css_path.read_text()

        for forbidden in ("react", "radix", "base ui", "tailwind", "lucide-react"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("o_moo_ui", css)
        self.assertNotIn(".moo-button", css)
        self.assertIn(".moo-ui .btn", css)


if __name__ == "__main__":
    unittest.main()

import ast
from pathlib import Path
import unittest


ADDON = Path(__file__).resolve().parents[1]


class TestMooUiButtonContract(unittest.TestCase):
    def setUp(self):
        self.manifest = ast.literal_eval((ADDON / "__manifest__.py").read_text())
        self.template = (ADDON / "components/button.xml").read_text()

    def test_manifest_loads_minimal_button_assets(self):
        self.assertEqual(self.manifest["depends"], ["web"])
        self.assertEqual(
            self.manifest["data"],
            ["components/icon.xml", "components/sidebar.xml", "components/button.xml"],
        )
        self.assertEqual(
            self.manifest["assets"]["web.assets_frontend"],
            [
                "moo_ui/static/src/tokens/tokens.css",
                "moo_ui/static/src/components/icon/icon.scss",
                "moo_ui/static/src/components/button/button.css",
                "moo_ui/static/src/components/sidebar/sidebar.js",
                "moo_ui/static/src/components/sidebar/sidebar.scss",
            ],
        )

    def test_button_template_maps_the_public_api(self):
        self.assertIn('<template id="button"', self.template)
        self.assertIn("<button", self.template)
        self.assertNotIn("<a", self.template)
        self.assertIn("variant or 'default'", self.template)
        self.assertIn("size or 'default'", self.template)
        self.assertIn("type or 'button'", self.template)
        self.assertIn('<t t-out="0"/>', self.template)
        self.assertNotIn("t-raw", self.template)

        for variant in ("default", "outline", "ghost", "destructive", "secondary", "link"):
            self.assertIn(variant, self.template)
        for size in ("default", "xs", "sm", "lg", "icon", "icon-xs", "icon-sm", "icon-lg"):
            self.assertIn(size, self.template)
        for marker in (
            "btn",
            "btn-primary",
            "btn-outline-secondary",
            "btn-ghost",
            "btn-danger",
            "btn-xs",
            "btn-icon",
            "button_attrs",
            "disabled",
        ):
            self.assertIn(marker, self.template)
        self.assertNotIn("moo-button", self.template)


if __name__ == "__main__":
    unittest.main()

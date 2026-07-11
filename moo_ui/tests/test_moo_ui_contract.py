import ast
import unittest
from pathlib import Path


ADDON_ROOT = Path(__file__).resolve().parents[1]


class TestMooUiContract(unittest.TestCase):

    def test_manifest_declares_minimal_frontend_addon(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertEqual(manifest['version'], '19.0.1.0.0')
        self.assertEqual(manifest['depends'], ['web'])
        self.assertFalse(manifest['application'])
        self.assertTrue(manifest['installable'])

    def test_manifest_loads_icon_template_and_tokens(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertIn('views/icon_templates.xml', manifest['data'])
        self.assertIn(
            'moo_ui/static/src/scss/tokens.scss',
            manifest['assets']['web.assets_frontend'],
        )

    def test_icon_template_is_generic_and_escaped(self):
        template = (ADDON_ROOT / 'views/icon_templates.xml').read_text()

        self.assertIn('id="icon"', template)
        self.assertIn('class="o_moo_ui_icon"', template)
        self.assertNotIn('olympiad', template.lower())
        self.assertNotIn('kita', template.lower())
        self.assertNotIn('mentor', template.lower())

    def test_tokens_are_scoped_and_bootstrap_backed(self):
        styles = (ADDON_ROOT / 'static/src/scss/tokens.scss').read_text()

        self.assertIn('.o_moo_ui_scope', styles)
        self.assertIn('--moo-ui-background:', styles)
        self.assertIn('var(--bs-body-bg', styles)


if __name__ == '__main__':
    unittest.main()

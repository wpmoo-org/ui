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

    def test_manifest_loads_sidebar_template(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertIn('views/sidebar_templates.xml', manifest['data'])

    def test_sidebar_templates_define_compound_api(self):
        template = (ADDON_ROOT / 'views/sidebar_templates.xml').read_text()

        for template_id in (
            'sidebar_layout',
            'sidebar',
            'sidebar_inset',
            'sidebar_trigger',
            'sidebar_header',
            'sidebar_content',
            'sidebar_footer',
        ):
            self.assertIn(f'id="{template_id}"', template)

        for marker in (
            't-out="0"',
            'o_moo_ui_scope',
            'o_moo_ui_sidebar_layout',
            'o_moo_ui_sidebar',
            'o_moo_ui_sidebar_inset',
            'o_moo_ui_sidebar_trigger',
            'offcanvas-lg offcanvas-start',
            'offcanvas-title',
            'visually-hidden',
            'data-moo-ui-sidebar-compact-toggle',
            'data-bs-toggle="offcanvas"',
        ):
            self.assertIn(marker, template)

    def test_sidebar_templates_stay_generic_and_safe(self):
        template = (ADDON_ROOT / 'views/sidebar_templates.xml').read_text()
        lower_template = template.lower()

        for forbidden in (
            'olympiad',
            'kita',
            'mentor',
            'jury',
            'parent',
            'erzieher',
            't-raw',
            'markup',
            't-att-t-call',
            'onclick=',
        ):
            self.assertNotIn(forbidden, lower_template)


if __name__ == '__main__':
    unittest.main()

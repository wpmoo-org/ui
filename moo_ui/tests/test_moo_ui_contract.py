import ast
import unittest
from pathlib import Path


ADDON_ROOT = Path(__file__).resolve().parents[1]

CORE_COMPONENTS = {
    'card': (
        'card',
        'card_header',
        'card_title',
        'card_description',
        'card_content',
        'card_footer',
    ),
    'badge': ('badge',),
    'empty': ('empty',),
    'button': ('button',),
    'avatar': ('avatar',),
    'dialog': ('dialog',),
    'drawer': ('drawer',),
    'separator': ('separator',),
    'skeleton': ('skeleton',),
    'alert': ('alert',),
    'breadcrumb': ('breadcrumb',),
    'dropdown_menu': ('dropdown_menu',),
    'command': ('command',),
    'tabs': ('tabs',),
    'pagination': ('pagination',),
    'label': ('label',),
    'field': ('field',),
    'input': ('input',),
    'input_group': ('input_group',),
    'textarea': ('textarea',),
    'select': ('select',),
    'checkbox': ('checkbox',),
    'radio_group': ('radio_group',),
    'switch': ('switch',),
    'slider': ('slider',),
    'tooltip': ('tooltip',),
    'popover': ('popover',),
    'accordion': ('accordion',),
    'collapsible': ('collapsible',),
    'progress': ('progress',),
    'spinner': ('spinner',),
    'kbd': ('kbd',),
    'aspect_ratio': ('aspect_ratio',),
    'attachment': ('attachment',),
}


class TestMooUiContract(unittest.TestCase):

    def test_manifest_declares_minimal_frontend_addon(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertEqual(manifest['version'], '19.0.1.0.0')
        self.assertEqual(manifest['depends'], ['web'])
        self.assertFalse(manifest['application'])
        self.assertTrue(manifest['installable'])

    def test_manifest_loads_icon_template_and_tokens(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertIn('components/icon.xml', manifest['data'])
        self.assertIn(
            'moo_ui/static/src/scss/tokens.scss',
            manifest['assets']['web.assets_frontend'],
        )

    def test_icon_template_is_generic_and_escaped(self):
        template = (ADDON_ROOT / 'components/icon.xml').read_text()

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

        self.assertIn('components/sidebar.xml', manifest['data'])

    def test_manifest_loads_typography_template_and_styles(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())

        self.assertIn('components/typography.xml', manifest['data'])
        self.assertIn(
            'moo_ui/static/src/components/typography/typography.scss',
            manifest['assets']['web.assets_frontend'],
        )

    def test_typography_templates_define_basic_text_api(self):
        template = (ADDON_ROOT / 'components/typography.xml').read_text()

        for template_id in (
            'typography_h1',
            'typography_h2',
            'typography_h3',
            'typography_h4',
            'typography_p',
            'typography_lead',
            'typography_large',
            'typography_small',
            'typography_muted',
            'typography_inline_code',
            'typography_blockquote',
            'typography_list',
        ):
            self.assertIn(f'id="{template_id}"', template)

        for marker in (
            't-out="0"',
            'o_moo_ui_typography_h1',
            'o_moo_ui_typography_p',
            'o_moo_ui_typography_muted',
            'o_moo_ui_typography_inline_code',
            'o_moo_ui_typography_blockquote',
            'o_moo_ui_typography_list',
        ):
            self.assertIn(marker, template)

    def test_typography_styles_are_generic_and_token_backed(self):
        styles = (ADDON_ROOT / 'static/src/components/typography/typography.scss').read_text()

        for marker in (
            '.o_moo_ui_typography_h1',
            '.o_moo_ui_typography_h2',
            '.o_moo_ui_typography_p',
            '.o_moo_ui_typography_lead',
            '.o_moo_ui_typography_muted',
            '.o_moo_ui_typography_inline_code',
            '.o_moo_ui_typography_blockquote',
            '.o_moo_ui_typography_list',
            'var(--moo-ui-foreground)',
            'var(--moo-ui-muted)',
        ):
            self.assertIn(marker, styles)

        self.assertNotIn('--moo-account-', styles)
        self.assertNotIn('vw', styles)
        self.assertNotRegex(styles, r'letter-spacing:\s*-')

    def test_sidebar_templates_define_compound_api(self):
        template = (ADDON_ROOT / 'components/sidebar.xml').read_text()

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
        template = (ADDON_ROOT / 'components/sidebar.xml').read_text()
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

    def test_manifest_loads_sidebar_interaction_and_styles_after_tokens(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())
        assets = manifest['assets']['web.assets_frontend']

        self.assertEqual(assets[0], 'moo_ui/static/src/scss/tokens.scss')
        self.assertLess(
            assets.index('moo_ui/static/src/components/sidebar/sidebar.js'),
            assets.index('moo_ui/static/src/components/sidebar/sidebar.scss'),
        )

    def test_sidebar_interaction_uses_odoo_public_interaction_contract(self):
        script = (ADDON_ROOT / 'static/src/components/sidebar/sidebar.js').read_text()

        for marker in (
            'import { browser } from "@web/core/browser/browser";',
            'import { cookie } from "@web/core/browser/cookie";',
            'import { registry } from "@web/core/registry";',
            'import { Interaction } from "@web/public/interaction";',
            'export class MooUiSidebar extends Interaction',
            'static selector = "[data-moo-ui-sidebar-layout]"',
            'data-moo-ui-sidebar-compact-toggle',
            'data-moo-ui-sidebar-group-trigger',
            'registry.category("public.interactions").add("moo_ui.sidebar", MooUiSidebar)',
            'browser.localStorage',
            'cookie.set',
            'browser.matchMedia',
            'closeFlyouts',
            'openActiveGroups',
        ):
            self.assertIn(marker, script)

        self.assertIn('if (active) {\n            this.closeFlyouts();', script)
        self.assertIn('this.openActiveGroups();', script)
        self.assertNotIn('if (!active) {\n            this.closeFlyouts();', script)

        for forbidden in (
            'mobileOpen',
            'backdrop',
            'focus trap',
            'cloneNode',
            'o_moo_ui_sidebar_mobile_open',
        ):
            self.assertNotIn(forbidden, script)

    def test_sidebar_styles_are_generic_and_token_backed(self):
        styles = (ADDON_ROOT / 'static/src/components/sidebar/sidebar.scss').read_text()

        for marker in (
            '.o_moo_ui_sidebar_layout',
            '.o_moo_ui_sidebar',
            '.o_moo_ui_sidebar_inset',
            '.o_moo_ui_sidebar_trigger',
            '.o_moo_ui_sidebar_header',
            '.o_moo_ui_sidebar_content',
            '.o_moo_ui_sidebar_footer',
            '.o_moo_ui_sidebar_layout_compact',
            '--moo-ui-sidebar-width',
            '--moo-ui-sidebar-compact-width',
            'var(--moo-ui-foreground)',
            'min-height: 100vh',
            'position: sticky',
            'height: 100vh',
            'overflow: visible',
        ):
            self.assertIn(marker, styles)

        self.assertNotIn('--moo-account-', styles)

    def test_manifest_loads_core_component_templates_and_assets(self):
        manifest = ast.literal_eval((ADDON_ROOT / '__manifest__.py').read_text())
        data_files = manifest['data']
        assets = manifest['assets']['web.assets_frontend']

        for component in CORE_COMPONENTS:
            self.assertIn(f'components/{component}.xml', data_files)
            self.assertIn(
                f'moo_ui/static/src/components/{component}/{component}.scss',
                assets,
            )

        self.assertIn(
            'moo_ui/static/src/components/command/command.js',
            assets,
        )
        self.assertIn(
            'moo_ui/static/src/components/tooltip/tooltip.js',
            assets,
        )
        self.assertIn(
            'moo_ui/static/src/components/popover/popover.js',
            assets,
        )

    def test_core_component_templates_define_safe_generic_api(self):
        for component, template_ids in CORE_COMPONENTS.items():
            template = (ADDON_ROOT / f'components/{component}.xml').read_text()
            lower_template = template.lower()

            for template_id in template_ids:
                self.assertIn(f'id="{template_id}"', template)
                self.assertIn(f'o_moo_ui_{template_id}', template)

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

    def test_core_component_styles_are_token_backed_and_generic(self):
        for component in CORE_COMPONENTS:
            styles = (ADDON_ROOT / f'static/src/components/{component}/{component}.scss').read_text()

            self.assertIn('.o_moo_ui_scope', styles)
            self.assertIn('var(--moo-ui-', styles)
            self.assertNotIn('--moo-account-', styles)
            self.assertNotIn('olympiad', styles.lower())
            self.assertNotIn('kita', styles.lower())

    def test_interactive_components_use_public_interaction_contract(self):
        for component in ('command', 'tooltip', 'popover'):
            script = (ADDON_ROOT / f'static/src/components/{component}/{component}.js').read_text()

            self.assertIn('import { registry } from "@web/core/registry";', script)
            self.assertIn('import { Interaction } from "@web/public/interaction";', script)
            self.assertIn(f'registry.category("public.interactions").add("moo_ui.{component}"', script)
            self.assertNotIn('olympiad', script.lower())
            self.assertNotIn('kita', script.lower())

    def test_command_interaction_has_native_input_fallback(self):
        script = (ADDON_ROOT / 'static/src/components/command/command.js').read_text()

        for marker in (
            'this.input = this.el.querySelector("[data-moo-ui-command-input]")',
            'this.onNativeInput = (ev) => this.onInput(ev)',
            'this.input.addEventListener("input", this.onNativeInput)',
            'this.input.removeEventListener("input", this.onNativeInput)',
            'Boolean(query && !item.textContent.toLowerCase().includes(query))',
        ):
            self.assertIn(marker, script)


if __name__ == '__main__':
    unittest.main()

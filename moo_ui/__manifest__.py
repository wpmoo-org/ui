# Part of Moo UI. See LICENSE file for full copyright and licensing details.

{
    'name': 'Moo UI',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Reusable QWeb and Bootstrap UI components for Odoo',
    'author': 'WPMoo',
    'website': 'https://www.wpmoo.org',
    'license': 'OPL-1',
    'depends': ['web'],
    'data': [
        'components/icon.xml',
        'components/sidebar.xml',
        'components/button.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'moo_ui/static/src/tokens/tokens.css',
            'moo_ui/static/src/components/icon/icon.scss',
            'moo_ui/static/src/components/button/button.css',
            'moo_ui/static/src/components/sidebar/sidebar.js',
            'moo_ui/static/src/components/sidebar/sidebar.scss',
        ],
    },
    'application': False,
    'installable': True,
}

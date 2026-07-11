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
        'views/icon_templates.xml',
        'views/sidebar_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'moo_ui/static/src/scss/tokens.scss',
            'moo_ui/static/src/interactions/sidebar.js',
            'moo_ui/static/src/scss/sidebar.scss',
        ],
    },
    'application': False,
    'installable': True,
}

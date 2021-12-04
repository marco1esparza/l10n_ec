# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extras Ecommerce para Ecuador',
    'version': '1.6',
    'summary': 'ecommerce the ecuadorian way',
    'category': 'Localization',
    'description': '''         
        - Validaciones extras
        - Manejo de RUC/CED en ecommerce
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'website_sale',
        'l10n_ec',
    ],   
    'data': [
        #Data
        #wizard
        #Views
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
    'post_init_hook': '_l10n_ec_set_ecommerce_labels',
}

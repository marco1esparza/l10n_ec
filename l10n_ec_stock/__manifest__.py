# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extras de Inventario para Ecuador',
    'version': '1.0',
    'category': 'Stock',
    'summary': 'Configuración contable para valoración de inventario para Ecuador',
    'description': '''
        Autores:
            Ing. Andres Calle
    ''',
    'author': 'TRESCLOUD CIA LTDA',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'l10n_ec',
        'stock',
    ],
    'data': [
        #Data
        'data/stock_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}

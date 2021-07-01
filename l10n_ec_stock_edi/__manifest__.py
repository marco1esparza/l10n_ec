# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extras de Inventario En Documentos Electronicos',
    'version': '1.0',
    'category': 'Stock',
    'summary': 'Extras de inventario en Documentos electronicos de ecuador.',
    'description': '''
        Autores:
            Ing. Andres Calle
    ''',
    'author': 'TRESCLOUD CIA LTDA',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'l10n_ec_edi',
        'sale_stock',
    ],
    'data': [
        # views
        'views/report_invoice.xml',
    ],
    'installable': True,
    'auto_install': True,
}

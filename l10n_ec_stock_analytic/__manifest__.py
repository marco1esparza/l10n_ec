# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cuentas analíticas en inventario',
    'version': '1.0',
    'category': 'Stock',
    'summary': 'Cuentas analíticas en inventario',
    'description': '''
        Este metodo agrega la cuenta analítica en la cabecera de los picking y validaciones
        de cuentas analíticas en el proceso de creación de apuntes contables.
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'sale_stock_analytic',
        'stock_inventory_analytic',
        'l10n_ec_analytic'
    ],
    'data': [
        #Views
        'views/stock_picking_view.xml'
    ],
    'installable': True
}

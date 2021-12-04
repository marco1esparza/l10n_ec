# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extras del Punto de Venta para Ecuador',
    'version': '1.0',
    'summary': 'Even easier Accounting by Trescloud',
    'category': 'Localization',
    'description': '''
        - Bypass a la restriccion de conciliacion de asientos de la misma empresa, cuando el origen es el punto de venta.
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'point_of_sale',
        'l10n_ec_account_extended',
        ],   
    'data': [
        ],
    'installable': True,
    'auto_install': True,
    'application': True
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Factura de Venta con rubros Personalizados',
    'version': '1.0',
    'summary': 'Contabilidad aún más fácil por Trescloud',
    'category': 'Localization',
    'description': '''
        - Agregando opción para personalizar la factura.
        - Agregando líneas personalizadas.
        - Validaciones
        - XML y Ride de facturas electrónicas en base a las líneas personalizadas.
        - Notas de crédito personalizadas.
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec_edi',
        ],   
    'data': [
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/account_move_view.xml',
        'views/report_invoice.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': True
}

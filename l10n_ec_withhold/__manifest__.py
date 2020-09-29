# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Retenciones ecuatorianas',
    'version': '1.0',
    'category': 'Localization',
    'summary': 'SRI electronic withholds, sales withholds, etc',
    'description': '''
        Característica:
            Agrega las características básicas para la emisión de Retenciones en ventas y compras.
            
        Funcionalidad:
            Registro de retenciones en facturas de clientes emitidas por los clientes. Generación de
            retenciones para facturas de proveedores, impresión, eliminación y anulación de retenciones.
        
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec_edi'
    ],
    'data': [
        #Data
        'data/account_journal_data.xml',
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/account_move_view.xml',
        'views/account_journal_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

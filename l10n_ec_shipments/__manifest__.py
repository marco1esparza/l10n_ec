# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Guia de Remision ecuatorianas',
    'version': '1.0',
    'category': 'Localization',
    'summary': 'SRI electronic shipments',
    'description': '''
        Característica:
            Agrega las características básicas para la emisión de Guias de Remision.
            
        Funcionalidad:
        
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'stock',
        'l10n_ec_edi',
    ],
    'data': [
        #Data
        'data/account_journal_data.xml',
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/l10n_ec_stock_carrier_view.xml',
        'views/res_company_view.xml',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
        'views/report_invoice.xml',
    ],
    'installable': True,
    'auto_install': False,
    # Se hace uso del post_init_hook para al finalizar la instalacion del modulo, se ejecute el metodo _assign_default_edi_shipment_account_id
    # para que asigne la cuenta transitoria para Guias de Remisiones en las compañias existentes (Metodo existente en __init__.py)
    'post_init_hook': '_assign_default_edi_shipment_account_id',
}

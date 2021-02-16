# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Guia de Remision ecuatorianas',
    'version': '1.0',
    'category': 'Localization',
    'summary': 'SRI electronic waybills',
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
        'security/l10n_ec_multicompany_security.xml',
        #Views
        'views/l10n_ec_stock_carrier_view.xml',
        'views/res_company_view.xml',
        'views/account_move_view.xml',
        'views/stock_picking_view.xml',
        'views/report_invoice.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': '_assign_default_edi_waybill_account_id',
}

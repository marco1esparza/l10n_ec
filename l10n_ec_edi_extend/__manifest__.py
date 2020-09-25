# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Facturas ecuatorianas extend',
    'version': '1.0',
    'category': 'Localization',
    'description': '''        
        Autores:
            Ing. Andres Calle
            Ing. Patricio Rangles
            Ing. José Miguel Rivero
            Ing. Santiago Orozco        
    ''',
    'author': 'TRESCLOUD CIA LTDA',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'l10n_ec_edi',
    ],    
    'data': [
        #Views
        'views/account_move_view.xml',
    ],
    'installable': False,
}

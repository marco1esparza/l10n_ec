# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reports',
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
        'base',
        'account_reports',
        'l10n_ec_edi'
    ],
    'data': [
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/menu_view.xml',
        'views/res_company_view.xml',
        #Wizard
        'wizard/wizard_generate_ats_view.xml',
    ],
    'installable': True,
}

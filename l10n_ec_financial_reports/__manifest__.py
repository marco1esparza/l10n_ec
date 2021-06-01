# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reportes Financieros para Ecuador',
    'version': '1.0',
    'category': 'Localization',
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
        'account_reports',
        ],
    'data': [
        # Data
        'data/account_financial_report_data.xml',
    ],
    'installable': True,
}

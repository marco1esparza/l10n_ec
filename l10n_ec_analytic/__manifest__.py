# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cuentas analíticas',
    'version': '1.0',
    'category': 'Account',
    'summary': 'Cuentas analíticas',
    'description': '''
        Este metodo agrega la política analítica en las cuentas contables.
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec'
    ],
    'data': [
        #Views
        'views/account_account_view.xml'
    ],
    'installable': True,
    #Post Init para establecer politica analitica en las cuentas contables
    #al momento de instalar el modulo
    'post_init_hook': '_set_account_analytic_policy'
}

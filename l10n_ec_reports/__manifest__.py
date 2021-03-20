# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reports',
    'version': '1.1',
    'category': 'Localization',
    'description': '''
        Autores:
            Ing. Andres Calle
            Ing. José Miguel Rivero
    ''',
    'author': 'TRESCLOUD CIA LTDA',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'account_reports',
        'l10n_ec_withhold'
        ],
    'data': [
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/menu_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/l10n_ec_account_tax_form_header_view.xml',
        #Wizard
        'wizard/l10n_ec_reports_base_file_report.xml',
        'wizard/wizard_generate_ats_view.xml',
        'wizard/l10n_ec_account_tax_report_wizard_view.xml',
        'wizard/l10n_ec_show_a_tax_report_wizard_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}

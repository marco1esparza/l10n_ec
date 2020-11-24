# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Reports',
    'version': '1.1',
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
        #Data
        'data/l10n_ec_sri_tax_support_data.xml',
        'data/l10n_latam_document_type_data.xml',
        #Security
        'security/ir.model.access.csv',
        #Views
        'views/menu_view.xml',
        'views/res_company_view.xml',
        'views/l10n_ec_sri_tax_support_view.xml',
        'views/account_move_view.xml',
        'views/res_partner_view.xml',
        'views/l10n_ec_account_tax_form_header_view.xml',
        #Wizard
        'wizard/base_file_report.xml',
        'wizard/wizard_generate_ats_view.xml',
        'wizard/l10n_ec_account_tax_report_wizard_view.xml',
    ],
    'installable': True,
}

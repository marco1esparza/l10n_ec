# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extras Contables para Ecuador',
    'version': '1.2',
    'summary': 'Even easier Accounting by Trescloud',
    'category': 'Localization',
    'description': '''         
        - Validaciones extras, para que su auxiliar contable no cometa errores
        - Automatización de retención del IVA posiciones fiscales
        - Automatización de retención de la renta
        - Nuevos tipos de Contribuyentes
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'account_reports', #Se agrega esta dependencia pues el modulo hace herencia al modelo 'account.report' que es creado por el modulo account_reports
        'l10n_ec_edi',
        'l10n_ec_withhold',
        ],   
    'data': [
        #Views
        'views/account_account_view.xml',
        'views/account_move_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_view.xml',
        'views/menu_view.xml',
        'views/res_users_view.xml',
        #wizard
        'wizard/account_move_reversal_view.xml',
        #Reports
        'reports/report_account_move_templates.xml',
        'reports/report_payment_receipt_templates.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
    # Post Init para asignacion de impuesto a compañia.
    'post_init_hook': '_post_install_hook_setup_profit_withhold_taxes',
}

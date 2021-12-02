# -*- coding: utf-8 -*-
{
    'name': 'Ecuadorian Checks Layout',
    'version': '1.0',
    'author': 'TRESCLOUD',
    'category': 'Accounting/Localizations/Check',
    'summary': 'Print EC Checks',
    'description': """
This module allows to print your payments on pre-printed checks for all banks of Ecuador
A sample check layout is included that fits most Banco del Pinchincha checks, and the user
can specify the location of each field for other banks, in this way it fits all banks of Ecuador
    """,
    'website': 'https://www.trescloud.com',
    'depends': ['account_check_printing', 'l10n_ec_edi'],
    'data': [
        #data
        'data/ec_check_printing.xml',
        #reports
        'report/print_check.xml',
        'report/print_check_ec.xml',
        #views
        'views/account_journal_view.xml',
        'views/account_payment_views.xml',
        'wizard/print_prenumbered_checks_view.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_ec_check_printing/static/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_post_install_hook_configure_ecuadorian_checks',
}

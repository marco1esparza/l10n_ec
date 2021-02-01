# -*- coding: utf-8 -*-
{
    'name': 'Ecuadorian Checks Layout',
    'version': '1.0',
    'author': 'TRESCLOUD',
    'category': 'Accounting/Localizations/Check',
    'summary': 'Print EC Checks',
    'description': """
This module allows to print your payments on pre-printed checks.
You can configure the output (specific bank paper format, etc.) in each bank journal, and manage the
checks numbering (if you use pre-printed checks without numbers) in journal settings.

Supported formats
-----------------
- Banco Pichincha #1
- Banco Pichincha #1
- Banco Produbanco
- Banco Internacional
- Banco Pacifico
    """,
    'website': 'https://www.trescloud.com',
    'depends': ['account_check_printing', 'l10n_ec_edi'],
    'data': [
        'data/ec_check_printing.xml',
        'report/print_check.xml',
        'report/print_check_ec.xml',
        'views/account_journal_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

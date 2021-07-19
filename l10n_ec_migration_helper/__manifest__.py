# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Migration to v14 of Ecuador Accounting by Trescloud',
    'version': '5.5',
    'description': '''
Functional\n
----------\n
This module automates the migration process of Ecuadorian Accounting to current Odoo release, use as follows\n
- Start the shell:
Option A: /home/andrescalle/virtualenv13/bin/python3 /home/andrescalle/git13/odoo/odoo-bin shell -c /home/andrescalle/git13/odoo.conf -d serca13
Option B:  python3 odoo-bin shell -d mydb

- Run the script
module = self.env['ir.module.module'].search([('name','=','l10n_ec_migration_helper')])
self.env['l10n_ec.migration.helper'].migration_main() 


Authors:
    Ing. Andres Calle <andres.calle@trescloud.com>
    ''',
    'author': 'TRESCLOUD',
    'category': 'Localization',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'base',
        'l10n_ec',
        'l10n_ec_edi',
        'l10n_ec_withhold',
        'l10n_ec_account_extended',
    ],   
    'data': [
        #Other data
        #Views
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

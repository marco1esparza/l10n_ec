# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # Migracion de v13 a v14
    map_deprecated_modules(env)
    uninstall_deprecated_modules(env)

@openupgrade.logging()
def map_deprecated_modules(env):
    openupgrade.update_module_names(
        env.cr, [
            ('l10n_ec_hr','l10n_ec_hr_payroll'),
            ('l10n_ec_account_check','l10n_ec_check_printing'),
            ('l10n_ec_financial_reports','trescloud_financial_reports'),
            ], merge_modules=True,)
    
@openupgrade.logging()
def uninstall_deprecated_modules(env):
    """Se eliminan modulos pues es más facil reinstalarlos cuando se
    completen las pruebas de los mismos, no se pierde data.
    """
    modules = env['ir.module.module'].search(
        [('state', 'in', ['installed','to upgrade']),
         ('name', 'in', [
            'mass_operation_abstract', #provista por Odoo Enterprise
            'mass_editing', #provista por Odoo Enterprise
             ]),
         ])
    for module in modules:
        module.module_uninstall()
        
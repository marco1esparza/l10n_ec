# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade

@openupgrade.migrate()
def migrate(env, version):
    setup_account_check_printing_layout(env)

@openupgrade.logging()
def setup_account_check_printing_layout(env):
    #Crea el impuesto 351 como copia del 346 para microempresas, y setea valores correspondientes
    for company in env['res.company'].search([('country_code','=','EC')]):
        company.account_check_printing_layout = 'l10n_ec_check_printing.action_print_check_ec'

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade

@openupgrade.migrate()
def migrate(env, version):
    create_tax351(env)

@openupgrade.logging()
def create_tax351(env):
    #Crea el impuesto 351 como copia del 346 para microempresas, y setea valores correspondientes
    for company in env['res.company'].search([('country_code','=','EC')]):
        tax346 = env['account.tax'].search([
            ('type_tax_use','=','purchase'),
            ('l10n_ec_code_ats','=',346),
            ('amount','=',-1.75), #antes aquí decía 2.00
            ], limit=1)
        tax351 = env['account.tax'].search([
            ('type_tax_use','=','purchase'),
            ('l10n_ec_code_ats','=',351),
            ('amount','=',-1.75), #antes aquí decía 2.00
            ])
        if tax346 and not tax351:
            ctx = env._context.copy()
            ctx.update({
                'default_l10n_ec_code_ats', '351',
                'default_l10n_ec_code_ats', '351',
                'default_l10n_ec_code_ats', '351',
                })
            tax351 = tax346.with_context(ctx),copy()

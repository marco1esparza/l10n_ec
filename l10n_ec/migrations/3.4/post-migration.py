# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade

@openupgrade.migrate()
def migrate(env, version):
    fix_3440_tax(env)

@openupgrade.logging()
def fix_3440_tax(env):
    #los clientes de v14 venían con el impuesto con 2.0 por ciento, y eran rechazados por el SRI
    taxes_3440 = env['account.tax'].search([
        ('l10n_ec_code_ats','=',3440),
        ('name','=','3440 2.75% OTRAS RETENCIONES APLICABLES EL 2,75%'),
        ('amount','=',-2.0), #antes aquí decía 2.00
        ])
    taxes_3440.write({'amount': -2.75})

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade

@openupgrade.migrate()
def migrate(env, version):
    setup_account_check_printing_layout(env)
    setup_account_check_beneficiary_name(env)

@openupgrade.logging()
def setup_account_check_printing_layout(env):
    companies = env['res.company'].search([])
    env['account.chart.template']._l10n_ec_configure_ecuadorian_checks(companies)

@openupgrade.logging()
def setup_account_check_beneficiary_name(env):
    #fills the check beneficiary
    #asume que el numero de cheque esta correctamente llenado
    for payment in env['account.payment'].search([('check_number','!=',False)]):
        payment.l10n_ec_check_beneficiary_name = payment.partner_id.commercial_partner_id.name





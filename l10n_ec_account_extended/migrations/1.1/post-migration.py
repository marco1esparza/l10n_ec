# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade


@openupgrade.logging()
def create_tax_343(env):
    '''
    Creando el impuesto 343
    '''
    companies = env['res.company'].search([])
    for company in companies:
        tax343A = env['account.tax'].search([('l10n_ec_code_ats','=','343A'), ('company_id', '=', company.id)])
        if tax343A:
            tax = tax343A.copy()
            tax.name = 'Otras Retenciones Aplicables el 1%'
            tax.description = 'Otras 1%'
            tax.l10n_ec_code_base = 343
            tax.l10n_ec_code_applied = 393
            tax.l10n_ec_code_ats = 343

@openupgrade.migrate(use_env=True)
def migrate(env, version):
    create_tax_343(env)
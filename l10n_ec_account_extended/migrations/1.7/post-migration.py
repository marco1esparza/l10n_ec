# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade

@openupgrade.migrate()
def migrate(env, version):
    remove_facturx(env)
    
@openupgrade.logging()
def remove_facturx(env):
    # remover el edi format "Factur-X", pues no lo ocupamos para Ecuador
    ecuador = env['res.country'].search([('code','=','EC')])
    companies = env['res.company'].search([('country_id','in',ecuador)])
    for company in companies:
        sales_journal = env['account.journal'].search([('type','=','sale'),('company_id','=',company.id)])
        for journal in sales_journal:
            facturx = journal.edi_format_ids.filtered(lambda e: e.code == 'facturx_1_0_05')
            if facturx:
                journal.edi_format_ids = journal.edi_format_ids - facturx

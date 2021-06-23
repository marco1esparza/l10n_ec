# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade

@openupgrade.migrate()
def migrate(env, version):
    fix_partner_in_amls(env)
    
@openupgrade.logging()
def fix_partner_in_amls(env):
    # sets aml partner the same as am partner in invoices
    openupgrade.logged_query(env.cr,'''
        update account_move_line
        set partner_id = am.commercial_partner_id
        from account_move_line aml
        left join account_move am on aml.move_id = am.id
        where am.move_type in ('in_invoice','in_refund','out_invoice','out_refund')
        and aml.partner_id is not null --para excluir filas de notas y secciones 
        and account_move_line.id = aml.id
        and am.commercial_partner_id <> aml.partner_id
        ''')

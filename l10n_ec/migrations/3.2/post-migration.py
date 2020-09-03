# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

def l10n_ec_set_doc_type_no_update_true(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_record_ids = env['ir.model.data'].search([
        ('model', 'in', ['l10n_latam.document.type']),
        ('module', 'like', 'l10n_ec')
    ]).ids
    if xml_record_ids:
        cr.execute("update ir_model_data set noupdate = 't' where id in %s", (tuple(xml_record_ids),))

def migrate(cr, version):
    l10n_ec_set_doc_type_no_update_true(cr)
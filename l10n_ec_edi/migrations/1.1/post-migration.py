# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

def printer_point_no_gap(env):
    #sets with no gap all sequences linked to a printer point
    sequences = env['ir.sequence'].search([('l10n_ec_printer_id', '!=', False)])
    sequences.write({'implementation': 'no_gap'})

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    printer_point_no_gap(env)
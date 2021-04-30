# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api
from odoo import SUPERUSER_ID


def _compute_amount_withholding(cr):
    '''
    Se computa para retenciones de ventas, para poder obtener el total registrado en lal vista lista.
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    withholdings = env['account.move'].search([('move_type', '=', 'entry'),
                                               ('l10n_ec_withhold_type', '=',  'out_withhold'),
                                               ('l10n_latam_document_type_id', '=', '07')])

    for rec in withholdings:
        rec._compute_amount()


def migrate(cr, version):
    _compute_amount_withholding(cr)
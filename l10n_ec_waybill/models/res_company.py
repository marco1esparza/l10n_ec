# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    days_for_valid_waybill = fields.Integer(string='Valid days of a waybill', default=15, help='Number of days of validity of the waybill.')
    l10n_ec_edi_waybill_account_id = fields.Many2one('account.account', string='Account EDI Waybills', help='')
    
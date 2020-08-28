# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class L10NECPaymentMethod(models.Model):
    _name = 'l10n.ec.payment.method'
    _rec_name = 'l10n_ec_name'
    _order = 'sequence'
    _inherit = ['mail.thread']
    
    #Columns
    sequence = fields.Integer(
        string='Sequence'
        )
    l10n_ec_code = fields.Char(
        string='Code',
        size=2,
        track_visibility='onchange',
        help='Field of two digits that indicate the code for this payment method'
        )
    l10n_ec_name = fields.Char(
        string='Name',
        size=255,
        track_visibility='onchange',
        help=''
        )
    active = fields.Boolean(
        string='Active',
        default=True,
        track_visibility='onchange',
        help=''
        )

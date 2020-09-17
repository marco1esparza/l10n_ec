# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class L10NECPaymentMethod(models.Model):
    
    _name = 'l10n_ec.payment.method'
    _description = "SRI Payment Method"
    _order = 'active DESC, sequence, id'
    _inherit = ['mail.thread']
    
    sequence = fields.Integer(
        default=10,
        help="The first Payment Method is used by default when creating new invoices",
        )
    code = fields.Char(
        string='Code',
        size=2,
        required=True,
        track_visibility='onchange',
        )
    name = fields.Char(
        string='Name',
        size=255,
        required=True,
        track_visibility='onchange',
        )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the Payment Method without removing it.",
        track_visibility = 'onchange',
        )
    
    
    
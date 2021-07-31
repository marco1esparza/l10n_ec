# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    l10n_ec_account_type = fields.Selection(
        required=True,
    )

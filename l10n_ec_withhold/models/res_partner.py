# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    property_l10n_ec_profit_withhold_tax_id = fields.Many2one(
        'account.tax',
        company_dependent=True,
        string='Force profit withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'),('type_tax_use', '=', 'purchase')],
        help='If set forces the vat withhold tax on applicable purchases (also a withhold is required on document type). '
        'The profit withhold prevalence order is payment method (credit cards retains 0%), then partner, then product'
        )

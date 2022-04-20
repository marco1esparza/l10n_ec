# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Vendor Withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'), ('type_tax_use', '=', 'purchase')],
        help='Default withholding tax when the product is purchased'
        )
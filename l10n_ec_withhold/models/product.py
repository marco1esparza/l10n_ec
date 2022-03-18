# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    #Columns
    withhold_tax_ids = fields.Many2many(
        'account.tax',
        'product_withhold_taxes_rel',
        'prod_id',
        'tax_id',
        string='Vendor Withholdings',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'), ('type_tax_use', '=', 'purchase')],
        help='Default withholding tax when the product is purchased'
        )
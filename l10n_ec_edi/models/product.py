# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    #TODO ANGEL, debe tener el sufjio l10n_ec, ser un campo property
    withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Vendor Withhold',
        domain=[('tax_group_id.l10n_ec_type', 'in', ('withhold_income_sale', 'withhold_income_purchase')), ('type_tax_use', '=', 'none')],
        help='Default withholding tax when the product is purchased'
        )

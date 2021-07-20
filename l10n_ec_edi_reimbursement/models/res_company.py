# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    refund_product_id = fields.Many2one(
        'product.product',
        string='Producto de reembolso',
        help='Producto para realizar reembolsos como intermediario.'
        )

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_code(self):
        """
        This function check if the product had this values in this order:
        1) default_code
        2) ean13
        and return the first one
        """
        if self.default_code:
            return self.default_code
        elif self.barcode:
            return self.barcode
        else:
            return ''
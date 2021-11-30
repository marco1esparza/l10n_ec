# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def l10n_ec_get_product_codes(self):
        #Returns main and secondary product codes, for electronic documents, to be inherited in custom modules
        main_code = self.barcode or self.default_code or ''
        aux_code = ''
        if self:
            main_code = self.barcode or self.default_code or ''
            aux_code = ''
            if self.barcode:
                aux_code = self.default_code
        return main_code, aux_code

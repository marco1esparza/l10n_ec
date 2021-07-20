# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def l10n_ec_get_product_codes(self):
        '''
        Metodo que devuelve el codigo principal y el codigo secundario del producto.
        '''
        self.ensure_one()
        main_code = self.barcode or self.default_code
        aux_code = self.barcode and self.default_code or ''
        return main_code, aux_code

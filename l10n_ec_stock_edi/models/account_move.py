# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_invoiced_lot_values(self):
        '''
        Heredamos el metodo, para obtener el lot_id del super y poder agregar el Barcode del producto.
        '''
        self.ensure_one()

        lot_values = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft' or self.country_code != 'EC':
            return lot_values

        for value in lot_values:
            lot_id = value.get('lot_id', False)
            if lot_id:
                lot = self.env['stock.production.lot'].browse(lot_id)
                barcode = lot.product_id.barcode
                value.update({'barcode': barcode})
        return lot_values

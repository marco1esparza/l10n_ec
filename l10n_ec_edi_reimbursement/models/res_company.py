# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def get_default_refund_product_id(self):
        '''
        Este método se encarga de configurar el "Producto para Descuento Post-Venta" en la compañía
        El data estaba en este módulo pero fue necesario moverlo al inmediato inferior pues a la hora
        de instalar daba error pues dice que el xml_id que se espera en el return no existe.
        '''
        product = self.env.ref('l10n_ec_edi_reimbursement.refund_default_product', False)
        if product:
            product = product.id
        return product

    #Columns
    refund_product_id = fields.Many2one(
        'product.product',
        string='Producto de reembolso',
        default=get_default_refund_product_id,
        help='Producto para realizar reembolsos como intermediario.'
        )

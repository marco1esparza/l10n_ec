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

    def _create_account_refund_product(self):
        '''
        Metodo que asigna la cuenta para el producto de reembolso.
        '''
        for company in self.filtered(lambda x: x.country_code == 'EC'):
            product_id = company.refund_product_id or \
                         self.env.ref('l10n_ec_edi_reimbursement.refund_default_product', raise_if_not_found=False)
            if product_id:
                product_id = product_id.with_company(company)
                account = self.env['account.account'].search([('code', '=', '11040401'),
                                                              ('company_id', '=', company.id)])
                if account:
                    product_id.property_account_income_id = account
                    product_id.property_account_expense_id = account

    #Columns
    refund_product_id = fields.Many2one(
        'product.product',
        string='Producto de reembolso',
        default=get_default_refund_product_id,
        help='Producto para realizar reembolsos como intermediario.'
        )

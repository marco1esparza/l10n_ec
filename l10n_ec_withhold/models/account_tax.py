# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_is_zero

class AccountTax(models.Model):
    _inherit = "account.tax"
    
    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        #alter base amount for computing withholds over vat, jsut before computation
        if self.tax_group_id.l10n_ec_type == 'withhold_vat':
            vat_percentage = 0.12 #TODO v15 Agregar soporte para IVA 14%
            base_amount = base_amount * vat_percentage
        res = super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity, product, partner)
        return res
     
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
        #alter base amount for vat withhold after computation, to store the correct base amount 
        res = super(AccountTax, self).compute_all(price_unit, currency, quantity, product, partner, is_refund, handle_price_include)
        withhold_vat = self.filtered(lambda tax: tax.tax_group_id.l10n_ec_type == 'withhold_vat')
        if withhold_vat:
            for tax in res['taxes']:
                if tax['id'] == withhold_vat.id:
                    vat_percentage = 0.12 #TODO v15 Agregar soporte para IVA 14%
                    if withhold_vat.company_id.tax_calculation_rounding_method == 'round_globally':
                        tax['base'] = tax['base'] * vat_percentage
                    else: #redondeo por línea
                        prec = self.env['decimal.precision'].precision_get('Account')
                        tax['base'] = float_round(tax['base'] * vat_percentage, precision_digits=prec)
        return res

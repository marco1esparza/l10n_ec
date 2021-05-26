# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_is_zero

class AccountTax(models.Model):
    _inherit = "account.tax"

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
        # - alter base amount for vat withhold after computation, to store the correct base amount
        # - compute vat withold as globally rounding
        res = super(AccountTax, self).compute_all(price_unit, currency, quantity, product, partner, is_refund, handle_price_include)
        withhold_vat = self.filtered(lambda tax: tax.tax_group_id.l10n_ec_type == 'withhold_vat')
        if withhold_vat:
            for tax in res['taxes']:
                if tax['id'] == withhold_vat.id:
                    vat_percentage = 0.12 #TODO v15 Agregar soporte para IVA 14%
                    tax['base'] = float_round(tax['base'] * vat_percentage, precision_rounding=currency.rounding)
                    tax['amount'] = withhold_vat._compute_amount(tax['base'], price_unit, quantity, product, partner)
        return res

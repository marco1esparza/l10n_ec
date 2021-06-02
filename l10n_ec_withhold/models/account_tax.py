# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round

class AccountTax(models.Model):
    _inherit = "account.tax"

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, is_refund=False, handle_price_include=True):
        # - alter base amount for vat withhold after computation, to store the correct base amount
        # - compute vat withold as globally rounding
        res = super(AccountTax, self).compute_all(price_unit, currency, quantity, product, partner, is_refund, handle_price_include)
        withholds = self.filtered(lambda t: t.tax_group_id.l10n_ec_type in ('withhold_vat', 'withhold_income_tax'))
        if withholds:
            for tax in res['taxes']:
                if tax['id'] in withholds.ids:
                    sign = 1
                    base = tax['base']
                    if currency.is_zero(base):
                        sign = self._context.get('force_sign', 1)
                    elif base < 0:
                        sign = -1
                    withhold = withholds.filtered(lambda t: t.id == tax['id'])
                    if withhold.l10n_ec_type == 'withhold_vat':
                        vat_percentage = 0.12
                        tax['base'] = float_round(tax['base'] * vat_percentage, precision_rounding=currency.rounding)
                    tax_amount = withhold.with_context(force_price_include=False)._compute_amount(tax['base'], sign * price_unit, quantity, product, partner)
                    prec = currency.rounding * 1e-5
                    tax['amount'] = float_round(tax_amount, precision_rounding=prec)
        return res

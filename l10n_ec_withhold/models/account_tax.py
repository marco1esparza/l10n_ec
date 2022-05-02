# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountTax(models.Model):
    _inherit = "account.tax"
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # Improves Odoo to support withholding taxes, with several conditions:
        # - Do not show withholding taxes in invoice lines, due to historic setup those taxes are configured as purchase taxes
        # - Show only sales withhold taxes on sales withholds
        # - Show only purchase withhold taxes on purchase withholds
        context = self._context or {}
        if context.get('l10n_ec_withhold_type_ctx') == 'in_withhold':
            args += [('type_tax_use', '=', 'purchase'),('l10n_ec_type', 'in', ['withhold_vat','withhold_income_tax'])]
        elif context.get('l10n_ec_withhold_type_ctx') == 'out_withhold':
            args += [('type_tax_use', '=', 'none'),('l10n_ec_type', 'in', ['withhold_vat','withhold_income_tax'])]
        return super(AccountTax, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

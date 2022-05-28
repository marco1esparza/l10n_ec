# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class AccountTax(models.Model):
    _inherit = "account.tax"
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        # Improves Odoo to support withholding taxes, with several conditions:
        # - Do not show withholding taxes in invoice lines
        # - Show only sales withhold taxes on sales withholds
        # - Show only purchase withhold taxes on purchase withholds
        context = self._context or {}
        if context.get('l10n_ec_withhold_type_ctx') == 'in_withhold':
            args += [('type_tax_use', '=', 'none'),('tax_group_id.l10n_ec_type', 'in', ['withhold_vat_purchase', 'withhold_income_purchase'])]
        elif context.get('l10n_ec_withhold_type_ctx') == 'out_withhold':
            args += [('type_tax_use', '=', 'none'),('tax_group_id.l10n_ec_type', 'in', ['withhold_vat_sale', 'withhold_income_sale'])]
        return super(AccountTax, self)._search(args, offset, limit, order, count=count, access_rights_uid=access_rights_uid)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression

class AccountTax(models.Model):
    _inherit = "account.tax"

    def name_get(self):
        '''
        Se modifica el name_get para que se muestre el Codigo ATS, Codigo Aplicado o Codigo Base segun el Impuesto
        '''
        if self.env.company.country_id != self.env.ref('base.ec'):
            return super(AccountTax, self).name_get()
        result = []
        for tax in self:
            if tax.company_id.country_id == self.env.ref('base.ec'):
                new_name = (tax.l10n_ec_code_ats and '[' + tax.l10n_ec_code_ats + '] '
                            or (tax.l10n_ec_code_applied and '[' + tax.l10n_ec_code_applied + '] '
                                or (tax.l10n_ec_code_base and '[' + tax.l10n_ec_code_base + '] ' or ''))) + (
                                   tax.name or (tax.description or ''))
                result.append((tax.id, new_name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''
        Se modifica el name_search para que se buscar el Codigo ATS, Codigo Aplicado o Codigo Base segun el Impuesto
        '''
        args = args or []
        if self.env.company.country_id != self.env.ref('base.ec'):
            return super().name_search(name, args, operator, limit)
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('active', 'ilike', True), ('description', operator, name), ('name', operator, name)]
        else:
            domain = [('active', 'ilike', True), '|', '|', '|', '|', ('description', operator, name),
                      ('name', operator, name),
                      ('l10n_ec_code_ats', '=', name), ('l10n_ec_code_applied', '=', name), ('l10n_ec_code_base', '=', name)]
        taxes = self.search(expression.AND([domain, args]), limit=limit)
        return taxes.name_get()

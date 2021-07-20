# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        # Override to setup withhold taxes in company configuration
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        self._l10n_ec_setup_profit_withhold_taxes(company)
        return res

    def _l10n_ec_setup_profit_withhold_taxes(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            
            company.l10n_ec_fallback_profit_withhold_services = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '3440'),
                ('l10n_ec_type', '=', 'withhold_income_tax'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company.id)
            ], limit=1)

            company.l10n_ec_profit_withhold_tax_credit_card = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '332G'),
                ('l10n_ec_type', '=', 'withhold_income_tax'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company.id)
            ], limit=1)

            company.l10n_ec_fallback_profit_withhold_goods = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '312'),
                ('l10n_ec_type', '=', 'withhold_income_tax'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company.id)
            ], limit=1)
            
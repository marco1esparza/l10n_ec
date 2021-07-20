# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        # Setup the reimbursement product and its accounts
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        self._l10n_ec_setup_reimbursement_product(company)
        return res

    def _l10n_ec_setup_reimbursement_product(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            
            #setup reimbursement product for this company
            product = self.env.ref('l10n_ec_edi_reimbursement.refund_default_product', False)
            product = product.with_company(company)
            company.refund_product_id = product
            
            #setup specific accounts for the product in this company
            account = self.env['account.account'].search([('code', '=', '11040401'),
                                                          ('company_id', '=', company.id)])
            if account:
                product.property_account_income_id = account
                product.property_account_expense_id = account
            
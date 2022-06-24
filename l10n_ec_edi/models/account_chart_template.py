# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        # Creates journals for purchase liquidation, sale withholds, purchase withhold
        res = super(AccountChartTemplate, self).generate_journals(acc_template_ref, company, journals_dict=journals_dict)
        self._l10n_ec_configure_ecuadorian_journals(company)
        return res
    
    def _l10n_ec_configure_ecuadorian_journals(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            new_journals = [
                {'name': 'Retenciones de Clientes',
                 'code': 'RVNTA',
                 'type': 'general',
                 'l10n_ec_withhold_type': 'out_withhold',
                 'l10n_ec_entity': False, 
                 'l10n_ec_emission': False},
                {'name': '001-001 Retenciones',
                 'code': 'RCMPR',
                 'type': 'general',
                 'l10n_ec_withhold_type': 'in_withhold',
                 'l10n_ec_entity': '001',
                 'l10n_ec_emission': '001'},
                {'name':'001-001 Liquidaciones de Compra',
                 'code':'LIQCO',
                 'type': 'purchase',
                 'l10n_ec_withhold_type': False,
                 'l10n_ec_entity': '001',
                 'l10n_ec_emission': '001'},
                ]
            for new_journal in new_journals:
                journal = self.env['account.journal'].search([
                    ('code', '=', new_journal['code']),
                    ('company_id', '=', company.id)])
                if not journal:
                    journal = self.env['account.journal'].create({
                        'name': new_journal['name'],
                        'code': new_journal['code'],
                        'type': new_journal['type'],
                        'l10n_ec_withhold_type': new_journal['l10n_ec_withhold_type'],
                        'l10n_ec_entity': new_journal['l10n_ec_entity'],
                        'l10n_ec_emission': new_journal['l10n_ec_emission'],
                        'l10n_latam_use_documents': True,
                        'company_id': company.id,
                        'show_on_dashboard': True
                    })
    
    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        # Override to setup withhold taxes in company configuration
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        self._l10n_ec_configure_ecuadorian_withhold_contributor_type(company)
        self._l10n_ec_setup_profit_withhold_taxes(company)
        return res
    
    def _l10n_ec_configure_ecuadorian_withhold_contributor_type(self, companies):
        # Set proper profit withhold tax on RIMPE on contributor type
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            tax_rimpe = self.env['account.tax'].search([
                ('l10n_ec_code_base', '=', '343'),
                ('company_id', '=', company.id)
                ], limit=1)
            rimpe_contributor = self.env.ref('l10n_ec_edi.l10n_ec_contributor_type_13', raise_if_not_found=False) # RIMPE Contributor
            if tax_rimpe and rimpe_contributor:
                rimpe_contributor.profit_withhold_tax_id = tax_rimpe.id

    def _l10n_ec_setup_profit_withhold_taxes(self, companies):
        # Sets fallback taxes for purchase withholds
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            company.l10n_ec_fallback_profit_withhold_services = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '3440'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
                ('company_id', '=', company.id),
                ], limit=1)
            company.l10n_ec_profit_withhold_tax_credit_card = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '332G'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
                ('company_id', '=', company.id),
                ], limit=1)
            company.l10n_ec_fallback_profit_withhold_goods = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '312'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_purchase'),
                ('company_id', '=', company.id),
                ], limit=1)

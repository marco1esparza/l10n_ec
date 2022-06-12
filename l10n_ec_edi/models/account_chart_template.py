# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        # Override to setup ecuadorian withhold data.
        res = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        self._l10n_ec_configure_ecuadorian_withhold_journal(company)
        return res

    def _l10n_ec_configure_ecuadorian_withhold_journal(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            #Create withhold journals
            new_journals = [
                {'code': 'RVNTA', 'name': 'Retenciones de clientes', 'l10n_ec_withhold_type': 'out_withhold',
                 'l10n_ec_entity': False, 'l10n_ec_emission': False},
                {'code': 'RCMPR', 'name': '001-001 Retenciones', 'l10n_ec_withhold_type': 'in_withhold',
                 'l10n_ec_entity': '001', 'l10n_ec_emission': '001'}
                ]
            for new_journal in new_journals:
                journal = self.env['account.journal'].search([
                    ('code', '=', new_journal['code']),
                    ('company_id', '=', company.id)])
                if not journal:
                    journal = self.env['account.journal'].create({
                        'name': new_journal['name'],
                        'code': new_journal['code'],
                        'l10n_ec_withhold_type': new_journal['l10n_ec_withhold_type'],
                        'l10n_latam_use_documents': True,
                        'type': 'general',
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
        #TODO ANDRES: Clean up the contributor types list, to a minimum
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            #Create withhold Distribution Type
            tax_rimpe_id = False
            tax_rimpe = self.env['account.tax'].search([('l10n_ec_code_base', '=', '343')], limit=1)
            if tax_rimpe:
                tax_rimpe_id = tax_rimpe.id
            new_distribution_types = [
                {'sequence': 1, 'name': 'SOCIEDADES - PERSONAS JURIDICAS', 'profit_withhold_tax_id': False},
                {'sequence': 2, 'name': 'CONTRIBUYENTES ESPECIALES', 'profit_withhold_tax_id': False},
                {'sequence': 3, 'name': 'SECTOR PUBLICO Y EP', 'profit_withhold_tax_id': False},
                {'sequence': 4, 'name': 'PERSONA NATURAL OBLIGADA A LLEVAR CONTABILIDAD', 'profit_withhold_tax_id': False},
                {'sequence': 5, 'name': 'PERSONA NATURAL NO OBLIGADA - ARRIENDOS', 'profit_withhold_tax_id': False},
                {'sequence': 6, 'name': 'PERSONA NATURAL NO OBLIGADA - PROFESIONALES', 'profit_withhold_tax_id': False},
                {'sequence': 7, 'name': 'PERSONA NATURAL NO OBLIGADA - LIQUIDACIONES DE COMPRAS', 'profit_withhold_tax_id': False},
                {'sequence': 8, 'name': 'PERSONA NATURAL NO OBLIGADAS - EMITE FACTURA O NOTA DE VENTA', 'profit_withhold_tax_id': False},
                {'sequence': 13, 'name': 'CONTRIBUYENTE REGIMEN RIMPE', 'profit_withhold_tax_id': tax_rimpe_id},
                {'sequence': 14, 'name': 'OTRAS - Sin cálculo automático de retención de IVA', 'profit_withhold_tax_id': False}
                ]
            for new_distribution_type in new_distribution_types:
                distribution_type = self.env['l10n_ec.contributor.type'].search([
                    ('name', '=', new_distribution_type['name']),
                    ('company_id', '=', company.id)])
                if not distribution_type:
                    distribution_type = self.env['l10n_ec.contributor.type'].create({
                        'sequence': new_distribution_type['sequence'],
                        'name': new_distribution_type['name'],
                        'profit_withhold_tax_id': new_distribution_type['profit_withhold_tax_id'],
                        'company_id': company.id
                    })

    def _l10n_ec_setup_profit_withhold_taxes(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            
            company.l10n_ec_fallback_profit_withhold_services = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '3440'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company.id)
            ], limit=1)

            company.l10n_ec_profit_withhold_tax_credit_card = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '332G'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company.id)
            ], limit=1)

            company.l10n_ec_fallback_profit_withhold_goods = self.env['account.tax'].search([
                ('l10n_ec_code_ats', '=', '312'),
                ('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', company.id)
            ], limit=1)
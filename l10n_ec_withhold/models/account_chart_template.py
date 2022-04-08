# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        # Override to configure ecuadorian withhold data.
        res = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        self._l10n_ec_configure_ecuadorian_withhold_journal(company)
        return res

    def _l10n_ec_configure_ecuadorian_withhold_journal(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            #Create withhold journals
            new_journals = [
                {'code': 'RVNTA','name': 'Retenciones en ventas', 'l10n_ec_withhold': 'sale'},
                {'code': 'RCMPR','name': 'Retenciones en compras', 'l10n_ec_withhold': 'purchase'}
                ]
            for new_journal in new_journals:
                journal = self.env['account.journal'].search([
                    ('code', '=', new_journal['code']),
                    ('company_id', '=', company.id)])
                if not journal:
                    journal = self.env['account.journal'].create({
                        'name': new_journal['name'],
                        'code': new_journal['code'],
                        'l10n_ec_withhold': new_journal['l10n_ec_withhold'],
                        'l10n_latam_use_documents': True,
                        'type': 'general',
                        'company_id': company.id,
                        'show_on_dashboard': True
                    })                    
    
    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        # Override to setup withhold taxes in company configuration
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        self._l10n_ec_configure_ecuadorian_withhold_contributor_type(company)
        return res
    
    def _l10n_ec_configure_ecuadorian_withhold_contributor_type(self, companies):
        ecuadorian_companies = companies.filtered(lambda r: r.country_code == 'EC')
        for company in ecuadorian_companies:
            self = self.with_company(company)
            #Create withhold Distribution Type
            tax_rimpe_id = False
            tax_rimpe = self.env['account.tax'].search([('l10n_ec_code_base', '=', '343')], limit=1)
            if tax_rimpe:
                tax_rimpe_id = tax_rimpe.id
            new_distribution_types = [
                {'sequence': 1, 'name': 'SOCIEDADES - PERSONAS JURIDICAS', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 2, 'name': 'CONTRIBUYENTES ESPECIALES', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 3, 'name': 'SECTOR PUBLICO Y EP', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 4, 'name': 'PERSONA NATURAL OBLIGADA A LLEVAR CONTABILIDAD', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 5, 'name': 'PERSONA NATURAL NO OBLIGADA - ARRIENDOS', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 6, 'name': 'PERSONA NATURAL NO OBLIGADA - PROFESIONALES', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 7, 'name': 'PERSONA NATURAL NO OBLIGADA - LIQUIDACIONES DE COMPRAS', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 8, 'name': 'PERSONA NATURAL NO OBLIGADAS - EMITE FACTURA O NOTA DE VENTA', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 9, 'name': 'EMPRESA EXTRANJERA - VENTA LOCAL', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 10, 'name': 'PERSONA EXTRANJERA - VENTA LOCAL', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 11, 'name': 'EMPRESA EXTRANJERA - EXPORTACION', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 12, 'name': 'PERSONA EXTRANJERA - EXPORTACION', 'property_l10n_ec_profit_withhold_tax_id': False},
                {'sequence': 13, 'name': 'CONTRIBUYENTE REGIMEN RIMPE', 'property_l10n_ec_profit_withhold_tax_id': tax_rimpe_id},
                {'sequence': 14, 'name': 'OTRAS - Sin cálculo automático de retención de IVA', 'property_l10n_ec_profit_withhold_tax_id': False}
                ]
            for new_distribution_type in new_distribution_types:
                distribution_type = self.env['contributor.type'].search([
                    ('name', '=', new_distribution_type['name']),
                    ('company_id', '=', company.id)])
                if not distribution_type:
                    distribution_type = self.env['contributor.type'].create({
                        'sequence': new_distribution_type['sequence'],
                        'name': new_distribution_type['name'],
                        'property_l10n_ec_profit_withhold_tax_id': new_distribution_type['property_l10n_ec_profit_withhold_tax_id'],
                        'company_id': company.id
                    })

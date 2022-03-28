# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"
    
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        # Override to configure ecuadorian withhold data.
        res = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        self._l10n_ec_configure_ecuadorian_withhold(company)
        return res

    def _l10n_ec_configure_ecuadorian_withhold(self, companies):
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

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """
        Override to configure ecuadorian waybill data.
        """
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        self._l10n_ec_configure_ecuadorian_waybill(company)
        return res

    def _l10n_ec_configure_ecuadorian_waybill(self, companies):
        accounts_codes = [
            '999901', #Cuenta transitoria para guias de remision
            ]
        for company in companies:
            self = self.with_company(company)
            #Set waybill account
            waybill_account = self.env['account.account'].search([
                ('code', '=', '999901'),
                ('company_id', '=', company.id)
                ])
            if not waybill_account:
                expense_type = self.env.ref('account.data_account_type_expenses')
                waybill_account = self.env['account.account'].create({
                    'code': '999901',
                    'name': '(No Usar) Guia Remision Transitoria',
                    'user_type_id': expense_type.id,
                    'company_id': company.id,
                })
            accounts = {
                code: self.env['account.account'].search(
                    [('company_id', '=', company.id), ('code', 'like', '%s%%' % code)], limit=1)
                for code in accounts_codes
                }
            company.write({
                'l10n_ec_edi_waybill_account_id': accounts['999901'].id,
                })
            #Create waybill journals
            new_journals = [{'code': 'GRMSN','name': 'Guía de Remisión'}]
            for new_journal in new_journals:
                journal = self.env['account.journal'].search([
                    ('code', '=', new_journal['code']),
                    ('company_id', '=', company.id)])
                if not journal:
                    journal = self.env['account.journal'].create({
                        'name': new_journal['name'],
                        'code': new_journal['code'],
                        'l10n_latam_use_documents': True,
                        'type': 'general',
                        'company_id': company.id,
                    })
            
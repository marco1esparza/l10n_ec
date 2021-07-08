# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Company(models.Model):
    _inherit = 'res.company'
    
    def _localization_use_documents(self):
        """ This method is to be inherited by localizations and return True if localization use documents """
        self.ensure_one()
        return True if self.country_id == self.env.ref('base.ec') else super()._localization_use_documents()

    @api.model
    def create_account_withholding_profit(self):
        company_ids = self.env['res.company'].search([])
        company_ids._create_account_withholding_profit()

    def _create_account_withholding_profit(self):
        '''
        Metodo que asigna la cuentas contables a retenciones.
        '''
        for company in self.filtered(lambda x: x.country_code == 'EC'):
            withholding_id = self.env['account.tax'].search([('l10n_ec_code_ats', '=', '3440'),
                                                             ('company_id', '=', company.id)])
            if withholding_id:
                withholding_id = withholding_id.with_company(company)
                account = self.env['account.account'].search([('code', '=', '2114010204'),
                                                              ('company_id', '=', company.id)])
                for line in withholding_id.invoice_repartition_line_ids:
                    line.account_id = account

            withholding_id = self.env['account.tax'].search([('l10n_ec_code_ats', '=', '332G'),
                                                             ('company_id', '=', company.id)])
            if withholding_id:
                withholding_id = withholding_id.with_company(company)
                account = self.env['account.account'].search([('code', '=', '2114010210'),
                                                              ('company_id', '=', company.id)])
                for line in withholding_id.invoice_repartition_line_ids:
                    line.account_id = account

            withholding_id = self.env['account.tax'].search([('l10n_ec_code_ats', '=', '312'),
                                                             ('company_id', '=', company.id)])
            if withholding_id:
                withholding_id = withholding_id.with_company(company)
                account = self.env['account.account'].search([('code', '=', '2114010202'),
                                                              ('company_id', '=', company.id)])
                for line in withholding_id.invoice_repartition_line_ids:
                    line.account_id = account

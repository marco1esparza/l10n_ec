# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _set_account_analytic_policy(cr, registry):
    '''
    Este metodo establece la politica analitica en las cuentas contables
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids = env['res.company'].search([])
    for company in company_ids:
        if company.country_code == 'EC':
            accounts = env['account.account'].search([])
            for account in accounts:
                if account.code:
                    if account.code.startswith(('1', '2', '3')):
                        account.analytic_policy = 'never'
                    elif account.code.startswith(('4', '5', '6', '7', '8')):
                        account.analytic_policy = 'posted'

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID


def _post_install_hook_setup_profit_withhold_taxes(cr, registry):
    # Setup defaul profit withhold taxes per company
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([])
    for company in companies:
        if company.country_code == 'EC':
            env['account.chart.template']._l10n_ec_setup_profit_withhold_taxes(company)
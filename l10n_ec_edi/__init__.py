from . import models
from . import wizard
from odoo import api, SUPERUSER_ID


def _post_install_hook_configure_ecuadorian_data(cr, registry):
    # Force setup as l10n_ec_edi module was not installed at moment of creation of first company
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([])
    for company in companies:
        if company.country_code == 'EC':
            env['account.chart.template']._l10n_ec_configure_ecuadorian_journals(company)
            env['account.chart.template']._l10n_ec_configure_ecuadorian_withhold_contributor_type(company)
            env['account.chart.template']._l10n_ec_setup_profit_withhold_taxes(company)

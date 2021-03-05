# -*- coding: utf-8 -*-

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID

def _post_install_hook_configure_ecuadorian_checks(cr, registry):
    '''
    - For all existing companies executes the ecuadorian configuration for check printing
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})    
    companies = env['res.company'].search([])
    for company in companies:
        env['account.chart.template']._l10n_ec_configure_ecuadorian_checks(company)
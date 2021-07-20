# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _post_install_hook_l10n_ec_setup_reimbursement_product(cr, registry):
    '''
    Este método se encarga de configurar el "Producto para Descuento Post-Venta"
    en las compañía existentes al instalar el modulo
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].search([])
    for company in companies:
        if company.country_code == 'EC':
            env['account.chart.template']._l10n_ec_setup_reimbursement_product(company)


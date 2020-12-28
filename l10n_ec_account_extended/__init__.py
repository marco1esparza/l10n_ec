# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID


def _assign_default_company_tax(cr, registry):
    '''
    Este método se encarga de asignar los impuestos por defecto a la compañía
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids = env['res.company'].search([])
    for company in company_ids:
        if not company.l10n_ec_fallback_profit_withhold_goods:
            tax = env['res.company'].search([
                ('company_id', '=', company.id),
                ('name', '=', '312 1.75% TRANSFERENCIA DE BIENES MUEBLES DE NATURALEZA CORPORAL')
            ])
            if tax:
                company.write({
                    'l10n_ec_fallback_profit_withhold_goods': tax[0].id,
                })

        if not company.l10n_ec_fallback_profit_withhold_services:
            tax = env['res.company'].search([
                ('company_id', '=', company.id),
                ('name', '=', '3440 2.75% OTRAS RETENCIONES APLICABLES EL 2,75%')
            ])
            if tax:
                company.write({
                    'l10n_ec_fallback_profit_withhold_services': tax[0].id,
                })

    if not company.l10n_ec_profit_withhold_tax_credit_card:
        tax = env['res.company'].search([
            ('company_id', '=', company.id),
            ('name', '=', '332G 0% PAGOS CON TARJETA DE CREDITO')
        ])
        if tax:
            company.write({
                'l10n_ec_fallback_profit_withhold_goods': tax[0].id,
            })

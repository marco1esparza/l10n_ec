# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from odoo import api, SUPERUSER_ID


def _assign_default_edi_shipment_account_id(cr, registry):
    '''
    Este método se encarga de configurar la "Cuenta Transitoria para Guia de Remision"
    en las compañía existentes al instalar el modulo.
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids_without_default_l10n_ec_edi_shipments_account_id = env['res.company'].search([
        ('l10n_ec_edi_shipments_account_id', '=', False),
        ('country_code', '=', 'EC'),
    ])
    default_l10n_ec_edi_shipments_account_id = env.ref('l10n_ec.ec999', raise_if_not_found=False)
    if default_l10n_ec_edi_shipments_account_id:
        company_ids_without_default_l10n_ec_edi_shipments_account_id.write({
            'l10n_ec_edi_shipments_account_id': default_l10n_ec_edi_shipments_account_id.id,
        })
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _assign_default_refund_product_id(cr, registry):
    '''
    Este método se encarga de configurar el "Producto para Descuento Post-Venta"
    en las compañía existentes al instalar el modulo
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids_without_default_refund_product_id = env['res.company'].search([
        ('refund_product_id', '=', False)
    ])
    default_refund_product_id = env.ref('l10n_ec_edi_reimbursement.refund_default_product', raise_if_not_found=False)
    if default_refund_product_id:
        company_ids_without_default_refund_product_id.write({
            'refund_product_id': default_refund_product_id.id,
        })

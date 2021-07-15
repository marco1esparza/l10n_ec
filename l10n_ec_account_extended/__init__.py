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
    company_ids._create_withholding_profit()

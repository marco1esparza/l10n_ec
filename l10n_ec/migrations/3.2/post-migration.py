# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

def reconfigure_vat_withhold_taxes(env):
    '''
    Para la retención del IVA ya no usaremos impuestos de tipo "codigo python", sino de tipo "porcentaje"
    '''
    taxes_to_setup = env['account.tax'].search([('amount_type','=','code')])
    taxes_to_setup.write({'amount_type': 'percent'})

def reconfigure_vat_withhold_templates(env):
    '''
    Para la retención del IVA ya no usaremos impuestos de tipo "codigo python", sino de tipo "porcentaje"
    '''
    taxes_to_setup = env['account.tax.template'].search([('amount_type','=','code')])
    taxes_to_setup.write({'amount_type': 'percent'})

def uninstall_account_tax_python(env):
    '''
    Desinstala el modulo auth_signup_verify_email
    para evitar que la redefinicion que hacen con el mensaje
    del login permanezca
    '''
    module = env['ir.module.module'].search(
        [('name', '=', 'account_tax_python')],
        limit=1
    )
    if module and module.state == 'installed':
        module.button_uninstall()

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    reconfigure_vat_withhold_taxes(env)
    reconfigure_vat_withhold_templates(env)
    uninstall_account_tax_python(env)
    
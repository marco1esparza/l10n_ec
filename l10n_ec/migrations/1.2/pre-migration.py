# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    # Migracion de v13 a v14
    map_deprecated_modules(env)
    uninstall_deprecated_modules(env)
    remove_exported_ir_model_data(env)

@openupgrade.logging()
def map_deprecated_modules(env):
    openupgrade.update_module_names(
        env.cr, [
            ('l10n_ec_hr','l10n_ec_hr_payroll'),
            ('l10n_ec_account_check','l10n_ec_check_printing'),
            ('l10n_ec_financial_reports','trescloud_financial_reports'),
            ], merge_modules=True,)
    whatsapp_module = env['ir.module.module'].search([('name','=','gtica_whatsapp_live_free'),
                                                      ('state','in',['installed','to upgrade','to install'])])
    if whatsapp_module:
        #borramos vistas que ahora son innecesarias
        env.ref('gtica_whatsapp_live_free.assets_frontend').unlink()
        env.ref('gtica_whatsapp_live_free.res_config_settings_whatsapp_livechat').unlink()
        env.ref('gtica_whatsapp_live_free.gtica_whatsapp_frontend_layout').unlink()
        openupgrade.update_module_names(
            env.cr, [
                ('gtica_whatsapp_live_free','website_whatsapp_icon'), #migracion fm
                ], merge_modules=True,)
    
@openupgrade.logging()
def uninstall_deprecated_modules(env):
    """Se eliminan modulos pues es más facil reinstalarlos cuando se
    completen las pruebas de los mismos, no se pierde data.
    """
    modules = env['ir.module.module'].search(
        [('state', 'in', ['installed','to upgrade']),
         ('name', 'in', [
            'mass_operation_abstract', #provista por Odoo Enterprise
            'mass_editing', #provista por Odoo Enterprise
             ]),
         ])
    for module in modules:
        module.module_uninstall()
        
@openupgrade.logging()
def remove_exported_ir_model_data(env):
    openupgrade.logged_query(env.cr,'''
        -- Removemos registros de ir_model_data que fueron creados por procesos de exportacion
        -- desde v13 se usa un mecanismo mas detallado para darles nombres y por otro lado
        -- con tantas migarciones de versiones, sqls, etc, muchos de estos registros ya no existen
        DELETE
        FROM ir_model_data
        WHERE module = '__export__'
        ''')

    
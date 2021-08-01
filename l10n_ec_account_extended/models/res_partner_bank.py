# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    @api.model
    def create(self, vals):
        # Al instalar modulos con data de bancos (incluyendo datos de prueba) ponemos un valor por
        # defecto para que no genere errores
        installing_modules = self._context.get('install_mode',False)
        if installing_modules and not vals.get('l10n_ec_account_type'):
            vals.update({'l10n_ec_account_type': 'checking'})
        return super().create(vals)
    
    l10n_ec_account_type = fields.Selection(
        required=True, #para forzar que siempre se abra el form, inhabilitando así el quick create
        )

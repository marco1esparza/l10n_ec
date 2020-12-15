# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import models, api, fields, _

class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        '''
        Modificamos el metodo para buscar usando las nomenclaturas:
        - 52022%COMPUTACION: El comodin puede estar en cualquier parte de la
        combinacion codigo + nombre
        - 5202210107 EQUIPO DE COMPUTACION: Busca por codigo + nombre
        '''
        args = args or []
        domain = []
        result = super(AccountAccount, self).name_search(name, args=args,operator=operator, limit=limit)
        if name:
            # Se agrega el soporte para buscar por codigo + nombre
            domain = [
                ('stored_display_name', 'ilike', name)
                ]
            accounts = self.search(domain + args, limit=limit)
            return accounts.name_get()
        return result

    @api.depends('name', 'code')
    def _compute_stored_display_name(self):
        """
        Calcula el codigo + nombre de la cuenta para almacenarlo en bbdd y
        poder realizar busquedas con este criterio
        """
        for account in self:
            name = account.code + ' ' + account.name
            account.stored_display_name = name
    
    stored_display_name = fields.Char(
        compute="_compute_stored_display_name",
        store=True,
        help=u"Campo técnico calculado y almacenado en la bbdd que contiene "
             u"el valor del código + nombre de la cuenta contable"
             )


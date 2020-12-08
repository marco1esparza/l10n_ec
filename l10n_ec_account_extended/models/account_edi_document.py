# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _l10n_ec_set_access_key(self):
        # Heredamos el metodo para poder validar la longitud y unicidad en Numero de Autorizaciones
        self.ensure_one()
        res = super()._l10n_ec_set_access_key()
        if self.l10n_ec_access_key:
            auth_len = len(self.l10n_ec_access_key)
            if auth_len != 49:
                #no se toman en cuenta autorizaciones de 10 caracteres pues esas no generan documento edi
                #no se toman en cuenta autorizaciones de 42 caracteres pues en el esquema offline ya no se usan
                raise UserError(_("El número de Autorización es incorrecto, presenta %s dígitos, deben ser 49") % auth_len)
            move_count = self.search(
                [('l10n_ec_access_key', '=', self.l10n_ec_access_key),
                 ('id', '!=', self.id)])
            if move_count:
                raise UserError(_("El número de Autorización (%s) debe ser único") % self.l10n_ec_access_key)
        return res

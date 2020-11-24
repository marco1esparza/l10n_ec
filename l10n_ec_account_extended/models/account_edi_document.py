# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _l10n_ec_set_access_key(self):
        # Heredamos el metodo para poder validar la longitud y unicidad en Numero de Autorizaciones
        #TODO V14, evaluar como hacer la validación en el write del campo para facturas de compra (o para documentos que no son electronicos)... talvez validarlo al generar el ATS nada mas para alivianar la carga?
        self.ensure_one()
        res = super()._l10n_ec_set_access_key()
        if self.l10n_ec_access_key:
            auth_len = len(self.l10n_ec_access_key)
            if not auth_len in (10, 42, 49):
                raise UserError(_("El número de Autorización es incorrecto, presenta %s dígitos") % auth_len)
            if auth_len == 42:
                move_count = self.env['account.move'].search(
                    [('l10n_ec_authorization', '=', self.l10n_ec_access_key),
                     ('state', '=', 'posted'),
                     ('id', '!=', self.id)])
                if move_count:
                    raise UserError(_("El número de Autorización (%s) debe ser único") % self.l10n_ec_access_key)
        return res

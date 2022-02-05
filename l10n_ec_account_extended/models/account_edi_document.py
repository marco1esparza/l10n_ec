# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


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

    #TODO: Se comenta solo por 1 semana para procesar unos doc electonicos de mas de 5 dias
#     def _prepare_jobs(self):
#         #For Ecuador do not attempt again a document after 5 days (for not being blacklisted by SRI)
#         to_process = []
#         today = fields.Date.context_today(self)
#         date_filter = today - timedelta(days=5)
#         # if user manually sent the document with button "send now" just call super, do not limit the 5 days
#         manual = self._context.get('default_move_type', False)  # hack, if in the account.move form there will be a default_type context
#         for edi in self:
#             if not manual:
#                 if edi.move_id.country_code == 'EC':
#                     if edi.move_id.invoice_date < date_filter:
#                         continue  # skip document, too old
#                     if edi.move_id.invoice_date > today:
#                         continue  # skip document, too new... in the future!
#             to_process_one = super(AccountEdiDocument, edi)._prepare_jobs()
#             to_process.extend(to_process_one)
#         return to_process
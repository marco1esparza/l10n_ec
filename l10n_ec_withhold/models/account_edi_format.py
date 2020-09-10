# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

#     def _is_compatible_with_journal(self, journal):
#         '''
#         Invocamos el _is_compatible_with_journal para que el diario de retenciones en compras tenga formato edi y se generen doc elec
#         '''
#         if journal.id == self.env.ref('l10n_ec_withhold.withhold_purchase').id:
#             return True
#         return super(AccountEdiFormat, self)._is_compatible_with_journal(journal)

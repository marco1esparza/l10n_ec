# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'    
    
    def l10n_ec_get_invoice_lines(self):
        '''
        Si es una factura personalizada se cambia las move_lines por las custom_lines
        '''
        if self.move_id.l10n_ec_invoice_custom:
            return self.move_id.l10n_ec_custom_line_ids
        return super(AccountEdiDocument, self).l10n_ec_get_invoice_lines()

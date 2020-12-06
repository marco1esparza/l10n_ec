# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _reverse_moves_post_hook(self, moves):
        '''
        Invocamos el metodo _reverse_moves_post_hook para remover impuestos de retencion de iva y renta en las notas de credito
        '''
        for invoice_line in moves.invoice_line_ids:
            for tax_line in invoice_line.tax_ids:
                if tax_line.tax_group_id.l10n_ec_type in ('withhold_vat', 'withhold_income_tax'):
                    #(3, ID) cut the link to the linked record with id = ID (delete the relationship between 
                    #the two objects but does not delete the target object itself)
                    invoice_line.tax_ids = [(3, tax_line.id)]
                    invoice_line.recompute_tax_line = True
        moves.with_context(check_move_validity=False)._onchange_invoice_line_ids()
        return super(AccountMoveReversal, self)._reverse_moves_post_hook(moves)

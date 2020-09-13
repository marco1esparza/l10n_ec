# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nEcAccountWithholdLine(models.Model):
    _name = 'l10n_ec.account.withhold.line'

    @api.onchange('invoice_id')
    def onchange_invoice_id(self):
        ''' 
        Este metodo setea las bases de iva y renta en las retenciones pues cuando existe mas de una factura
        se suman las bases de iva o renta de todas ellas y se muestra el total como valor sugerido en la base
        al agregar nuevas lineas de retencion
        '''
        if self.tax_id:
            #IVA
            if self.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
                self.base = self.invoice_id.l10n_ec_vat_doce_subtotal
            #RENTA
            elif self.tax_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
                self.base = self.invoice_id.amount_untaxed

    @api.onchange('tax_id','base')
    def onchange_tax(self):
        ''' 
        Este método setea el porcentage de la retención y calcula el importe
        '''
        #TODO: implementar o remover las sig dos lineas
#         if self.tax_id:
#             self.account_id = self.tax_id._get_withhold_account_for_sale()
        self.amount = abs(self.base * self.tax_id.amount / 100)

    #Columns
    tax_id = fields.Many2one(
        'account.tax',
        string='Tax'
        )
    account_id = fields.Many2one(
        'account.account',
        string='Account'
        )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice'
        )
    base = fields.Monetary(
        string='Base',
        currency_field='company_currency_id'
        )
    amount = fields.Monetary(
        string='Amount',
        currency_field='company_currency_id'
        )
    company_id = fields.Many2one(
        related='move_id.company_id',
        string='Company',
        store=True,
        readonly=True
        )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True,
        store=True,
        help='Utility field to express amount currency'
        )
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        index=True,
        required=True,
        readonly=True,
        auto_join=True,
        ondelete='cascade',
        help='The move of this entry line.'
        )

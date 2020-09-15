# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nEcAccountWithholdLine(models.Model):
    _name = 'l10n_ec.account.withhold.line'


    #TODO JOSE, implementar un default_get o algo así que alimente el invoice_id cuando solo hay una factura en la cabecera
    
    @api.onchange('invoice_id','tax_id')
    def onchange_invoice_id(self):
        #Sets the "base amount" according to invoice_id and tax
        base = 0.0
        if self.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
            base = self.invoice_id.l10n_ec_vat_doce_subtotal
        elif self.tax_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
            base = self.invoice_id.amount_untaxed
        self.base = base
    
    @api.onchange('base','tax_id')
    def onchange_base(self):
        #Recomputes amount according to base and tax
        percentage = (-1) * self.tax_id.amount/100 or 0.0
        amount = self.base * percentage
        accounts = self.tax_id.invoice_repartition_line_ids.mapped('account_id')
        account_id = accounts[0].id if accounts else False        
        self.write({
            'account_id': account_id,
            'amount': amount,
            })
    
    tax_id = fields.Many2one('account.tax', string='Tax',
        index=True, ondelete="restrict",
        required=True,
        )
    account_id = fields.Many2one('account.account', string='Account',
        index=True, ondelete="restrict",
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
        currency_field='company_currency_id',
        )
    company_id = fields.Many2one(related='move_id.company_id', store=True, readonly=True)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
        readonly=True, store=True,
        help='Utility field to express amount currency')
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
    
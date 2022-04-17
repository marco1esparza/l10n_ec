# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WizardAccountWithhold(models.TransientModel):
    _name = 'wizard.account.withhold'
    _check_company_auto = True
    
    @api.model
    def default_get(self, data_fields):
        res = {}
        invoice_id = self.env.context.get('active_id', False)
        if not invoice_id or not self.env.context.get('active_model') == 'account.move':
            return res
        if 'account_withhold_line_ids' in data_fields:
            invoice = self.env['account.move'].browse(invoice_id)
            default_values = invoice._l10n_ec_prepare_withold_default_values()
            res.update(
                journal_id=default_values['journal_id'], 
                l10n_latam_document_type_id=default_values['l10n_latam_document_type_id'], 
                date=fields.Date.context_today(self),
                company_id=invoice.company_id.id, 
                account_withhold_line_ids=default_values['account_withhold_line_ids']
                )
        return res
    
    def action_generate_withhold(self):
        #TODO: implementar el caso de ventas "out_withhold"
        account_move_line_obj = self.env['account.move.line']
        invoice = self.env['account.move'].browse(self.env.context.get('active_id'))
        l10n_ec_withhold_type = 'in_withhold'
        default_values = {
            'invoice_date': self.date,
            'journal_id': self.journal_id.id,
            'invoice_payment_term_id': None,
            'move_type': 'entry',
            'line_ids': [(5, 0, 0)],
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_ec_invoice_payment_method_ids':  [(5, 0, 0)],
            'l10n_ec_authorization': False,
            'l10n_ec_withhold_origin_ids': [(6, 0, invoice.ids)],
            'l10n_ec_withhold_type': l10n_ec_withhold_type
        }
        invoice = invoice.with_context(include_business_fields=False) #don't copy sale/purchase links
        withhold = invoice.copy(default=default_values)
        #TODO: arreglar las lineas de asiento todavia no se generan
        #Retenciones en compras
        lines = self.env['account.move.line']
        if withhold.l10n_ec_withhold_type == 'in_withhold':
            if withhold.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.filtered(lambda x: x.state == 'posted'):
                raise ValidationError(u'Solamente se puede tener una retención aprobada por factura de proveedor.')
            total = 0.0
            for line in self.account_withhold_line_ids:
                tax_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda x:x.repartition_type == 'tax')
                vals = {
                    'name': withhold.name,
                    'move_id': withhold._origin.id,
                    'partner_id': withhold.partner_id.id,
                    'account_id': line.account_id.id,
                    'date_maturity': False,
                    'quantity': 1.0,
                    'amount_currency': line.amount, #Withholds are always in company currency
                    'price_unit': line.amount,
                    'debit': 0.0,
                    'credit': line.amount,
                    'tax_base_amount': line.base,
                    'is_rounding_line': False,
                    'tax_line_id': line.tax_id.id, #originator tax
                    'tax_repartition_line_id': tax_line.id,
                    'tax_tag_ids': [(6, 0, tax_line.tag_ids.ids)],
                }
                total += line.amount
                line = account_move_line_obj.with_context(check_move_validity=False).create(vals)
                lines += line
            if self.account_withhold_line_ids:
                vals = {
                    'name': withhold.name,
                    'move_id': withhold._origin.id,
                    'partner_id': withhold.partner_id.id,
                    'account_id': withhold.partner_id.property_account_payable_id.id,
                    'date_maturity': False,
                    'quantity': 1.0,
                    'amount_currency': total, #Withholds are always in company currency
                    'price_unit': total,
                    'debit': total,
                    'credit': 0.0,
                    'tax_base_amount': 0.0,
                    'is_rounding_line': False
                }
                line = account_move_line_obj.with_context(check_move_validity=False).create(vals)
                lines += line
            withhold.line_ids = lines
            withhold._post(soft=False)
        return invoice.l10n_ec_action_view_withholds()

    #Columns
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal',
        check_company=True,
        help=''
        )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', 
        string='Document Type',
        help=''
        )
    l10n_latam_document_number = fields.Char(
        string='Document Number',
        help=''
        )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        help=''
        )
    company_id = fields.Many2one(
        'res.company', 
        required=True,
        default=lambda self: self.env.company,
        help=''
        )
    account_withhold_line_ids = fields.One2many(
        'wizard.account.withhold.line',
        'wizard_id',
        string='Withhold Lines',
        copy=False
        )


class WizardAccountWithholdLine(models.TransientModel):
    _name = 'wizard.account.withhold.line'

    #Columns
    @api.onchange('invoice_id', 'tax_id')
    def onchange_invoice_id(self):
        #Sets the "base amount" according to invoice_id and tax
        base = 0.0
        if self.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
            base = self.invoice_id.l10n_ec_vat_doce_subtotal
        elif self.tax_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
            base = self.invoice_id.amount_untaxed
        self.base = base
    
    @api.onchange('base', 'tax_id')
    def onchange_base(self):
        #Recomputes amount according to base and tax
        percentage = (-1) * self.tax_id.amount/100 or 0.0
        amount = self.base * percentage
        accounts = self.tax_id.invoice_repartition_line_ids.mapped('account_id')
        account_id = accounts[0].id if accounts else False        
        self.write({
            'account_id': account_id,
            'amount': amount
            })
    
    #Columns
    tax_id = fields.Many2one(
        'account.tax',
        string='Tax',
        index=True,
        ondelete='restrict'
        )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice'
        )
    account_id = fields.Many2one(
        'account.account', 
        string='Account',
        index=True,
        ondelete='restrict',
        )
    base = fields.Monetary(
        string='Base',
        currency_field='company_currency_id'
        )
    amount = fields.Monetary(
        string='Amount',
        currency_field='company_currency_id',
        )
    company_id = fields.Many2one(
        related='wizard_id.company_id',
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
    wizard_id = fields.Many2one(
        'wizard.account.withhold',
        string='Wizard',
        index=True,
        required=True,
        readonly=True,
        auto_join=True,
        ondelete='cascade',
        help='The move of this entry line.'
        )
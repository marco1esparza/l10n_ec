# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}

class L10n_ecWizardAccountWithhold(models.TransientModel):
    _name = 'l10n_ec.wizard.account.withhold'
    _check_company_auto = True
    
    @api.model
    def default_get(self, data_fields):
        res = {}
        invoice_id = self.env.context.get('active_id', False)
        if not invoice_id or not self.env.context.get('active_model') == 'account.move':
            return res
        
        invoice_ids = invoice_id #TODO V15.1 en las lineas previas cambiar invoice_id por invoice_ids para que se invoque desde el tree
        invoices = self.env['account.move'].search([('id','in',[invoice_ids])])
        self._validate_related_invoices(invoices)
        default_values = self._prepare_withold_default_values(invoices)
        res.update(default_values)
        return res
    
    def _validate_related_invoices(self, invoices):
        # Let's test the source invoices for missuse
        for invoice in invoices:
            # TODO: v15.1 Move validation to central method as data can change in other browser tabs
            if not invoice.l10n_ec_allow_withhold:
                raise ValidationError(u'The selected document type does not support withholds')
        #TODO V15.1 mover estas validaciones dentro del lazo for por eficiencia y para mostrar mensajes de error con numero de factura
        if any(invoice.state not in ['posted'] for invoice in invoices):
            raise ValidationError(u'Can not create a withhold, some documents are not yet posted')
        if invoices and any(inv.commercial_partner_id != invoices[0].commercial_partner_id for inv in invoices): #and not self.env.context.get('massive_withhold'):
            raise ValidationError(u'Some documents belong to different partners, please correct your selection')
        if invoices and any(MAP_INVOICE_TYPE_PARTNER_TYPE[inv.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type] for inv in invoices):
            raise ValidationError(u'Can not mix documents supplier and customer documents in the same withhold')
        if invoices and any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            #TODO: v15.1 Mas bien validar que sea sobre la moneda de la compañia, es decir dólares
            raise ValidationError(u'A fin de emitir retenciones sobre múltiples facturas, aquellas deben tener la misma moneda.')
            # TODO: v15.1 Decide if needed
            # if len(self) > 1 and invoice.move_type != 'out_invoice':
            #     raise ValidationError(u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')
                    
    def _prepare_withold_default_values(self, invoices):
        #Computes new withhold data for provided invoices
        if invoices[0].move_type == 'in_invoice':
            withhold_type = 'in_withhold'
        elif invoices[0].move_type == 'out_invoice':
            withhold_type = 'out_withhold'
        #TODO V15.2, luego de fusionar con Odoo, para compras, debemos preferir el punto de emision que coincida con la factura
        withhold_journal = self.env['account.journal'].search([
            ('l10n_ec_withhold_type', '=', withhold_type),
            ], order="sequence asc", limit=1)
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([
            ('country_id.code', '=', 'EC'),
            ('l10n_ec_type', '=', withhold_type),
            ], order="sequence asc", limit=1)
        default_values = {
            'journal_id': withhold_journal and withhold_journal.id,
            'l10n_latam_document_type_id': l10n_latam_document_type_id and l10n_latam_document_type_id.id,
            'date': fields.Date.context_today(self),
            'withhold_type': withhold_type,
            'withhold_origin_ids': [(6, 0, invoices.ids)],
            'company_id': invoices[0].company_id.id,
            }
        if withhold_type == 'in_withhold':
            l10n_ec_withhold_line_ids = []
            group_taxes = {}
            for invoice in invoices:
                for line in invoice.line_ids:
                    tax = line._l10n_ec_get_computed_taxes()
                    if tax:
                        tax_line = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
                        group_taxes.setdefault(tax.id, [{}, 0, 0])
                        if tax.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                            group_taxes[tax.id][0].update({
                                'account_id': tax_line.account_id.id,
                                'invoice_id': invoice.id
                            })
                            group_taxes[tax.id][1] += line.debit
                            group_taxes[tax.id][2] += abs(line.debit * tax.amount / 100)
                        if tax.tax_group_id.l10n_ec_type in ['withhold_vat']:
                            group_taxes[tax.id][0].update({
                                'account_id': tax_line.account_id.id,
                                'invoice_id': invoice.id
                            })
                            group_taxes[tax.id][1] += line.price_total - line.price_subtotal
                            group_taxes[tax.id][2] += abs((line.price_total - line.price_subtotal) * tax.amount / 100)
            prec = self.env['decimal.precision'].precision_get('Account') #TODO: V15.1 Replace wwith currency precision
            for tax_id, detail in group_taxes.items():
                l10n_ec_withhold_line_ids.append((0, 0, {
                    'tax_id': tax_id,
                    'account_id': detail[0].get('account_id'),
                    'invoice_id': detail[0].get('invoice_id'),
                    'base': float_round(detail[1], precision_digits=prec),
                    'amount': float_round(detail[2], precision_digits=prec)
                }))
            default_values.update({
                'account_withhold_line_ids': l10n_ec_withhold_line_ids
                })
        return default_values
    
    def action_generate_withhold(self):
        invoices = self.withhold_origin_ids
        default_values = {
            'invoice_date': self.date,
            'journal_id': self.journal_id.id,
            'invoice_payment_term_id': None, #to avoid accidents
            'move_type': 'entry',
            'line_ids': [(5, 0, 0)],
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': self.l10n_latam_document_number,
            'l10n_ec_invoice_payment_method_ids':  [(5, 0, 0)], #TODO v15.2 remove when merging into Odoo branch
            'l10n_ec_withhold_origin_ids': [(6, 0, invoices.ids)], #TODO v15.1 reimplementar, quiza con un campo funcional store false
            'l10n_ec_withhold_type': self.withhold_type,
        }
        invoice = invoices[0]
        invoice = invoice.with_context(include_business_fields=False) #don't copy sale/purchase links
        withhold = invoice.copy(default=default_values)
        lines = self.env['account.move.line'] #empty recordset
        if withhold.l10n_ec_withhold_type == 'in_withhold':
            #TODO REIMPLMENTAR FOR V15.1
            # if withhold.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.filtered(lambda x: x.state == 'posted'):
            #     raise ValidationError(u'Solamente se puede tener una retención aprobada por factura de proveedor.')
            total = 0.0
            for line in self.account_withhold_line_ids:
                tax_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda x:x.repartition_type == 'tax')
                vals = {
                    'name': withhold.name,
                    'move_id': withhold.id,
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
                line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals)
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
                line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals)
                lines += line
            withhold.line_ids = lines
            withhold._post(soft=False)
        return invoice.l10n_ec_action_view_withholds() #TODO V15.2 talvez no retornar pues ya queda en el widget de pago
    
    #TODO: rescatar las validaciones y la parte de ventas(compras ya esta implementado en el wizard), luego borrar el metodo
    def l10n_ec_make_withhold_entry(self):
        '''
        Metodo para hacer asientos de retenciones
        '''
        account_move_line_obj = self.env['account.move.line'] 
        for withhold in self:
            if withhold.country_code == 'EC':



                    #Retenciones en ventas
                    partner = withhold.partner_id.commercial_partner_id
                    if withhold.l10n_ec_withhold_type == 'out_withhold':
                        #Se verifica que el monto total de iva o renta por factura no sobrepase la base gravable
                        for invoice in withhold.l10n_ec_withhold_origin_ids:
                            total_base_vat = 0.0
                            vat_lines = self.env['l10n_ec.account.withhold.line'].search([('move_id','=',withhold.id), ('invoice_id','=',invoice.id), ('tax_id.tax_group_id.l10n_ec_type','=','withhold_vat')])
                            for vat_line in vat_lines:
                                total_base_vat += vat_line.base
                            precision = invoice.company_id.currency_id.decimal_places
                            diff_base_vat = float_compare(total_base_vat, invoice.l10n_ec_vat_doce_subtotal, precision_digits=precision)
                            if diff_base_vat > 0:
                                raise ValidationError(u'La base imponible de la retención de iva es mayor a la base imponible de la factura %s.' % invoice.l10n_latam_document_number)
                            total_base_profit = 0.0
                            profit_lines = self.env['l10n_ec.account.withhold.line'].search([('move_id','=',withhold.id), ('invoice_id','=',invoice.id), ('tax_id.tax_group_id.l10n_ec_type','=','withhold_income_tax')])
                            for profit_line in profit_lines:
                                total_base_profit += profit_line.base
                            diff_base_profit = float_compare(total_base_profit, invoice.amount_untaxed, precision_digits=precision)
                            if diff_base_profit > 0:
                                raise ValidationError(u'La base imponible de la retención de renta es mayor a la base imponible de la factura %s.' % invoice.l10n_latam_document_number)                            
                        if withhold.l10n_ec_withhold_line_ids:
                            #create the account.move.lines
                            #Credit
                            vals = {
                                'name': withhold.name,
                                'move_id': withhold.id,
                                'partner_id': partner.id,
                                'account_id': partner.property_account_receivable_id.id,
                                'date_maturity': False,
                                'quantity': 1.0,
                                'amount_currency': 0.0, #Withholds are always in company currency
                                'price_unit': withhold.l10n_ec_total,
                                'debit': 0.0,
                                'credit': withhold.l10n_ec_total,
                                'tax_base_amount': 0.0,
                                'is_rounding_line': False
                            }
                            account_move_line_obj.with_context(check_move_validity=False).create(vals)
                            for line in withhold.l10n_ec_withhold_line_ids:
                                #Debit
                                tax_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda x:x.repartition_type == 'tax')
                                vals = {
                                    'name': line.tax_id.name + ' ' + line.invoice_id.name,
                                    'move_id': withhold.id,
                                    'partner_id': partner.id,
                                    'account_id': line.account_id.id,
                                    'date_maturity': False,
                                    'quantity': 1.0,
                                    'amount_currency': 0.0, #Withholds are always in company currency
                                    'price_unit': (-1) * line.amount,
                                    'debit': line.amount,
                                    'credit': 0.0,
                                    'tax_base_amount': line.base,
                                    'tax_line_id': line.tax_id.id, #originator tax
                                    'tax_repartition_line_id': tax_line.id,
                                    'tax_tag_ids': [(6, 0, tax_line.tag_ids.ids)],                                    
                                }
                                debit_vals_list = [{
                                    "move_id": withhold.id,
                                    "account_id": account.id,
                                    "debit": tax_amount,
                                    "price_unit": tax_amount * -1,
                                    "price_subtotal": tax_amount * -1,
                                    "price_total": tax_amount * -1,
                                    "quantity": 1,
                                    "credit": 0.0,
                                    "name": name,
                                    "tax_tag_ids": tax_repartition.tag_ids and [(6, 0, tax_repartition.tag_ids.ids)] or [],
                                    "tax_repartition_line_id": tax_repartition.id,
                                    "tax_tag_invert": True,
                                    'tax_base_amount': line.base_amount,
                                },]
                                
                                account_move_line_obj.with_context(check_move_validity=False).create(vals)
                    #Retenciones en compras
                    lines = self.env['account.move.line']
                    if withhold.l10n_ec_withhold_type == 'in_withhold':
                        if withhold.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.filtered(lambda x: x.state == 'posted'):
                            raise ValidationError(u'Solamente se puede tener una retención aprobada por factura de proveedor.')
                        for line in withhold.l10n_ec_withhold_line_ids:
                            vals = {
                                'name': withhold.name,
                                'move_id': withhold._origin.id,
                                'partner_id': partner.id,
                                'account_id': line.account_id.id,
                                'date_maturity': False,
                                'quantity': 1.0,
                                'amount_currency': line.amount, #Withholds are always in company currency
                                'price_unit': line.amount,
                                'debit': 0.0,
                                'credit': line.amount,
                                'tax_base_amount': line.base,
                                'is_rounding_line': False
                            }
                            line = account_move_line_obj.with_context(check_move_validity=False).create(vals)
                            lines += line
                        if withhold.l10n_ec_withhold_line_ids:
                            vals = {
                                'name': withhold.name,
                                'move_id': withhold._origin.id,
                                'partner_id': partner.id,
                                'account_id': withhold.partner_id.property_account_payable_id.id,
                                'date_maturity': False,
                                'quantity': 1.0,
                                'amount_currency': withhold.l10n_ec_total, #Withholds are always in company currency
                                'price_unit': withhold.l10n_ec_total,
                                'debit': withhold.l10n_ec_total,
                                'credit': 0.0,
                                'tax_base_amount': 0.0,
                                'is_rounding_line': False
                            }
                            line = account_move_line_obj.with_context(check_move_validity=False).create(vals)
                            lines += line
                        withhold.line_ids = lines
                        
                        
            origins = []
            l10n_ec_withhold_line_ids = []
            for invoice in self:
                origin = invoice.name #Usamos name en lugar del l10n_latam_document_number para aprovechar el prefijo del tipo de doc
                if invoice.invoice_origin:
                    origin += ';' + invoice.invoice_origin
                origins.append(origin)
                l10n_ec_withhold_line_ids.append((0, 0, {'invoice_id': invoice.id}))
            origin = ','.join(origins)
            default_values.update({
                'invoice_origin': origin,
                'l10n_ec_withhold_line_ids': l10n_ec_withhold_line_ids
            })
                        

                
    journal_id = fields.Many2one(
        'account.journal', 
        string='Journal',
        check_company=True,
        )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type', 
        string='Document Type',
        )
    l10n_latam_document_number = fields.Char(
        string='Document Number',
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
    withhold_origin_ids = fields.Many2many(
        'account.move',
        'l10n_ec_account_invoice_withhold_rel',
        'withhold_id',
        'invoice_id',
        string='Invoices',
        copy=False,
        help='Technical field to limit elegible invoices related to this withhold'
        )
    
    withhold_type = fields.Selection(
        [('out_withhold', 'Sales Withhold'),
         ('in_withhold', 'Purchase Withhold')],
        string='Withhold Type',
        help='Technical field to limit elegible journals and taxes'
        )
    account_withhold_line_ids = fields.One2many(
        'l10n_ec.wizard.account.withhold.line',
        'wizard_id',
        string='Withhold Lines',
        )


class L10n_ecWizardAccountWithholdLine(models.TransientModel):
    _name = 'l10n_ec.wizard.account.withhold.line'

    @api.onchange('invoice_id', 'tax_id')
    def onchange_invoice_id(self):
        #Sets the "base amount" according to linked invoice_id and tax type
        base = 0.0
        if self.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
            base = self.invoice_id.l10n_ec_vat_doce_subtotal
        elif self.tax_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
            base = self.invoice_id.amount_untaxed
        self.base = base
    
    @api.onchange('base', 'tax_id')
    def onchange_base(self):
        #Recomputes amount according to "base amount" and tax percentage
        percentage = (-1) * self.tax_id.amount/100 or 0.0
        amount = self.base * percentage
        accounts = self.tax_id.invoice_repartition_line_ids.mapped('account_id')
        account_id = accounts[0].id if accounts else False
        self.write({
            'account_id': account_id,
            'amount': amount
            })
    
    tax_id = fields.Many2one('account.tax', string='Tax',)
    
    invoice_id = fields.Many2one('account.move', string='Invoice')
    
    account_id = fields.Many2one('account.account', string='Account')
    
    base = fields.Monetary(string='Base')
    
    amount = fields.Monetary(string='Amount')
    
    company_id = fields.Many2one(related='wizard_id.company_id')
    
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    wizard_id = fields.Many2one(
        'l10n_ec.wizard.account.withhold',
        string='Wizard',
        required=True,
        readonly=True,
        auto_join=True,
        help='The move of this entry line.'
        )
    
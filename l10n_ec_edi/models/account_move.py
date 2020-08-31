# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class AccountMove(models.Model):
    _inherit='account.move'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        '''
        Invocamos el método onchange_partner_id para setear la forma de pago
        '''
        res = super(AccountMove, self)._onchange_partner_id()
        if self.l10n_latam_country_code == 'EC':
            l10n_ec_payment_method_id = False
            payment_method_ids = self.env['l10n.ec.payment.method'].search([], order='l10n_ec_code asc')
            if payment_method_ids:
                if self.type in ['out_invoice', 'in_invoice']:
                    l10n_ec_payment_method_id = payment_method_ids[0].id
            self.l10n_ec_payment_method_id = l10n_ec_payment_method_id
        return res

    @api.onchange('l10n_ec_printer_id')
    def onchange_l10n_ec_printer_id(self):
        '''
        Este metodo setea el numero del documento en base al prefijo del punto de impresion
        '''
        if self.l10n_latam_country_code == 'EC':
            if not self.l10n_ec_printer_id:
                self.l10n_ec_printer_id = self._default_l10n_ec_printer_id()
            self.l10n_latam_document_number = self._suggested_internal_number(self.l10n_ec_printer_id.id, self.type)

    @api.onchange('l10n_latam_document_number')
    def onchange_l10n_latam_document_number(self):
        '''
        Este método agrega relleno del numero de factura en caso que lo requiera
        '''
        if self.l10n_latam_country_code == 'EC':
            number_split = self.l10n_latam_document_number.split('-')
            if len(number_split) == 3 and number_split[2] != '':
                if len(number_split[2]) < 17:
                    #Require auto complete
                    pos = 0
                    fill = 9 - len(number_split[2])
                    for car in number_split[2]:
                        if car != '0':
                            break
                        pos = pos + 1
                    number_split[2] = number_split[2][:pos] + '0' * fill + number_split[2][pos:]
                    self.l10n_latam_document_number =  number_split[0] + '-' + number_split[1] + '-' + number_split[2]

    @api.onchange('invoice_date', 'invoice_payment_term_id', 'l10n_ec_payment_method_id', 'invoice_line_ids', 'invoice_date_due')
    def onchange_set_l10n_ec_invoice_payment_method_ids(self):
        '''
        Con el cambio de los plazos al partner computamos las formas de pago a reportar al SRI
        Computamos las formas de pago en base a los plazos de pago
        '''
        self.ensure_one() #se ha probado el programa para una sola factura a la vez
        if self.type in 'out_invoice' and self.l10n_latam_country_code == 'EC':
            in_draft_mode = self != self._origin
            existing_move_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable'))
            existing_lines_index = 0
            new_payment_method_lines = self.env['l10n.ec.invoice.payment.method']
            existing_payment_method_lines = self.l10n_ec_invoice_payment_method_ids
            for line in existing_move_lines:
                #Como es para reportar al SRI se computa en base al date_invoice y no en base al date_start_payment_term
                percentage = 0.0
                if self.amount_total > 0.0:
                    percentage = round((float(line.debit) * 100.0 / float(self.amount_total)), 3)
                l10n_ec_days_payment_term = 0
                if line.date_maturity:
                    invoice_date = self.invoice_date or fields.Date.context_today(self)
                    l10n_ec_days_payment_term = (line.date_maturity - invoice_date).total_seconds() / (3600 * 24)
                if existing_lines_index < len(existing_payment_method_lines):
                    candidate = existing_payment_method_lines[existing_lines_index]
                    existing_lines_index += 1
                    candidate.update({
                        'l10n_ec_payment_method_id': self.l10n_ec_payment_method_id.id,
                        'l10n_ec_days_payment_term':l10n_ec_days_payment_term,
                        'l10n_ec_percentage': percentage,
                        'l10n_ec_amount': line.debit
                    })
                else:
                    create_method = in_draft_mode and self.env['l10n.ec.invoice.payment.method'].new or self.env['l10n.ec.invoice.payment.method'].create
                    candidate = create_method({
                        'l10n_ec_payment_method_id': self.l10n_ec_payment_method_id.id,
                        'l10n_ec_days_payment_term': l10n_ec_days_payment_term,
                        'l10n_ec_percentage': percentage,
                        'l10n_ec_amount': line.debit,
                        'l10n_ec_invoice_id': self.id
                    })
                new_payment_method_lines += candidate
            self.l10n_ec_invoice_payment_method_ids -= existing_payment_method_lines - new_payment_method_lines
            
    def post(self):
        '''
        Invocamos el metodo post para setear el numero de factura en base a la secuencia del punto de impresion
        cuando se usan documentos(opcion del diario) las secuencias del diario no se ocupan
        '''
        res = super(AccountMove, self).post()
        for invoice in self:
            if invoice.l10n_latam_country_code == 'EC':
                invoice.l10n_latam_document_number = invoice._get_internal_number_by_sequence()
                #Facturas de ventas electronicas
                if invoice.type in ('out_invoice') and invoice.l10n_ec_printer_id.l10n_ec_allow_electronic_document:
                    for document in invoice.edi_document_ids:
                        if document.state not in ('sent'):
                            document.edi_format_id = self.env.ref('l10n_ec_edi.ec_edi_format_invoice').id
                            #TODO: implementar estos dos metodos
                            #document.get_access_key()
                            document.attempt_electronic_document()
        return res
    
    def view_credit_note(self):
        '''
        '''
        [action] = self.env.ref('account.action_move_out_refund_type').read()
        action['domain'] = [('id', 'in', self.reversal_move_id.ids)]
        return action

    @api.model
    def _get_internal_number_by_sequence(self):
        '''
        Generates, for the given object and number, a valid autogenerated number
        if the user has not yet manually set one
        '''
        printer_id = self.l10n_ec_printer_id.id or self._default_l10n_ec_printer_id()
        if not printer_id:
            return self.l10n_latam_document_number
        printer_obj = self.env['l10n.ec.sri.printer.point']
        printer = printer_obj.browse(printer_id)
        document_type = {
            'out_invoice': 'invoice',
            'out_refund': 'refund',
            'in_invoice': 'purchClear'
        }.get(self.type)
        return printer_obj.get_next_sequence_number(printer, document_type, self.l10n_latam_document_number)
 
    @api.model
    def _default_l10n_ec_printer_id(self):
        '''
        Este metodo obtiene el punto de emisión configurado en las preferencias del usuario, en caso
        que no tenga, se obtiene el primer punto de impresion que exista generalmente es el 001-001
        '''
        printer_id = False
        if self.l10n_latam_country_code == 'EC':
            printer_id = self.env.user.l10n_ec_printer_id.id
            if not printer_id:
                printers = self.env['l10n.ec.sri.printer.point'].search([], limit=1)
                if printers:
                    printer_id = printers[0].id
        return printer_id

    @api.model
    def _suggested_internal_number(self, printer_id, type):
        '''
        Numero de factura sugerida para facturas de venta y compra, depende del punto de impresion
        '''
        internal_number = False
        if type in ['out_invoice', 'out_refund']:
            internal_number = '001-001-'
            printer = self.env['l10n.ec.sri.printer.point'].browse(printer_id)
            if printer.l10n_ec_prefix:
                internal_number = printer.l10n_ec_prefix
            else:
                if not printer:
                    printer = self.env['l10n.ec.sri.printer.point'].browse(self._default_l10n_ec_printer_id())
                    internal_number = printer.l10n_ec_prefix
        if type in ['in_invoice', 'in_refund']:
            internal_number = '001-001-'
        return internal_number

    @api.depends('l10n_ec_invoice_payment_method_ids')
    def compute_payment_method(self):
        '''
        Este método devuelve el total de pagos agrupados por formas de pago
        '''
        for invoice in self:
            effective_method = 0.0
            electronic_method = 0.0
            card_method = 0.0
            other_method = 0.0
            for line in invoice.filtered(lambda x:x.l10n_latam_country_code == 'EC').l10n_ec_invoice_payment_method_ids:
                #Efectivo
                if line.l10n_ec_payment_method_id.l10n_ec_code == '01':
                    effective_method += line.l10n_ec_amount
                #Dinero Electrónico
                elif line.l10n_ec_payment_method_id.l10n_ec_code == '17':
                    electronic_method += line.l10n_ec_amount
                #Tarjetas Débito/Crédito
                elif line.l10n_ec_payment_method_id.l10n_ec_code in ('10','11','16','18','19'):
                    card_method += line.l10n_ec_amount
                #Otros
                else:
                    other_method += line.l10n_ec_amount
            invoice.l10n_ec_effective_method = effective_method
            invoice.l10n_ec_electronic_method = electronic_method
            invoice.l10n_ec_card_method = card_method
            invoice.l10n_ec_other_method = other_method

    def _get_name_invoice_report(self, report_xml_id):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.country_id.code == 'EC':
            custom_report = {
                'account.report_invoice_document_with_payments': 'l10n_ec_edi.report_invoice_document_with_payments',
                'account.report_invoice_document': 'l10n_ec_edi.report_invoice_document',
            }
            return custom_report.get(report_xml_id) or report_xml_id
        return super()._get_name_invoice_report(report_xml_id)
    
    def _compute_total_invoice_ec(self):
        '''
        '''
        for invoice in self:
            l10n_ec_total_discount = 0.0
            for line in invoice.invoice_line_ids:
                l10n_ec_total_discount += line.l10n_ec_total_discount
            invoice.l10n_ec_total_discount = l10n_ec_total_discount
    
    #Columns
    l10n_ec_printer_id = fields.Many2one(
        'l10n.ec.sri.printer.point',
        string='Punto de emisión', readonly = True,
        states = {'draft': [('readonly', False)]},
        default=_default_l10n_ec_printer_id,
        help='The printer point or cash of my company where receive or send documents'
        ) #TODO JOSÉ: Poner un ondelete = restrict y validar que si ya esta en una factura no se pueda borrar
    l10n_ec_authorization = fields.Char(
        string='Autorización', readonly = True,
        states = {'draft': [('readonly', False)]},
        help='It is for the authorization to issue the document, select a release from the list. '
             'Only existing authorizations are displayed according to the date of the document.'
        )
    l10n_ec_payment_method_id = fields.Many2one(
        'l10n.ec.payment.method',
        string='Forma de pago', readonly = True,
        states = {'draft': [('readonly', False)]},
        help='Forma de pago del SRI'
        ) #TODO JOSÉ: Poner un ondelete = restrict y validar que si ya esta en una factura no se pueda borrar
    l10n_ec_invoice_payment_method_ids = fields.One2many(
        'l10n.ec.invoice.payment.method',
        'l10n_ec_invoice_id',
        string='Payment Methods',
        help='Estos valores representan la forma estimada de pago de la factura, son '
             'utilizados con fines informativos en documentos impresos y documentos '
             'electrónicos. No tienen efecto contable.')
    l10n_ec_effective_method = fields.Float(
        compute='compute_payment_method',
        string='Effective', 
        digits=dp.get_precision('Account'),
        method=True,
        store=True,
        help='Es la sumatoria de las formas de pago con código 01.'
        )
    l10n_ec_electronic_method = fields.Float(
        compute='compute_payment_method',
        string='Electronic Money',
        digits=dp.get_precision('Account'),
        method=True,
        store=True,
        help='Es la sumatoria de las formas de pago con código 17.'
        )
    l10n_ec_card_method = fields.Float(
        compute='compute_payment_method',
        string='Card Credit / Debit', 
        digits=dp.get_precision('Account'),
        method=True,
        store=True,
        help='Es la sumatoria de las formas de pago con códigos 10, 11, 16, 18, 19.'
        )
    l10n_ec_other_method = fields.Float(
        compute='compute_payment_method',
        string='Others', 
        digits=dp.get_precision('Account'),
        method=True,
        store=True,
        help='Es la sumatoria de las formas de pago con códigos 02, 03, 04, 05, 06, 08, 09, 12, 13, 14, 15, 20, 21.'
        )
    l10n_ec_total_discount = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total Discount',
        method=True, 
        store=False,
        readonly=True,
        help='Total sum of the discount granted'
        )


class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    def _compute_total_invoice_line_ec(self):
        '''
        '''
        for line in self:
            if line.discount:
                if line.tax_ids:
                    taxes_res = line.tax_ids._origin.compute_all(self.l10n_latam_price_unit,
                        quantity=self.quantity, currency=self.currency_id, product=self.product_id, partner=self.partner_id, is_refund=self.move_id.type in ('out_refund', 'in_refund'))
                    total_discount = taxes_res['total_excluded'] - self.l10n_latam_price_subtotal    
                else:
                    total_discount = (self.quantity * self.l10n_latam_price_unit) - self.l10n_latam_price_subtotal
                #In case of multi currency, round before it's use for computing debit credit
                if self.currency_id:
                    total_discount = self.currency_id.round(total_discount)
            self.l10n_ec_total_discount = total_discount 

    #Columns
    l10n_ec_total_discount = fields.Monetary(
        string='Total Discount', 
        compute='_compute_total_invoice_line_ec', 
        method=True,
        store=False,
        readonly=True,                                     
        help='Indicates the monetary discount applied to the total invoice line.'
        )


class L10NECInvoicePaymentMethod(models.Model):
    _name = 'l10n.ec.invoice.payment.method'
     
    #Columns
    l10n_ec_payment_method_id = fields.Many2one(
        'l10n.ec.payment.method',
        string='Way to Pay', 
        help='Way of payment of the SRI'
        )
    l10n_ec_days_payment_term = fields.Integer(
        string='Days Payment Term', 
        help='Payment term in days'
        )
    l10n_ec_percentage = fields.Float(
        string='Percentage',
        digits=(3,3),
        help='Percentage of the amount of the payment'
        )
    l10n_ec_amount = fields.Float(
        string='Amount',
        digits=(16,2), 
        help='Is the pay value for this payment method'
        )
    l10n_ec_invoice_id = fields.Many2one(
        'account.move',
        required=True,
        string='Invoice', 
        help='This field help to relate to account invoice object'
        )
   
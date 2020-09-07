# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp


class AccountMove(models.Model):
    _inherit='account.move'
    
    @api.onchange('l10n_ec_printer_id', 'l10n_latam_document_type_id')
    def onchange_l10n_ec_printer_id(self):
        '''
        Este metodo setea el numero del documento en False cada vez que se cambia de Punto de Impresion y Tipo Documento
        '''
        if self.l10n_latam_country_code == 'EC':
            self.l10n_latam_document_number = False

    @api.onchange('l10n_latam_document_number')
    def onchange_l10n_latam_document_number(self):
        '''
        Este método agrega relleno del numero de factura en caso que lo requiera
        '''
        number = self.l10n_latam_document_number
        if self.l10n_latam_country_code == 'EC' and self.l10n_latam_document_number and self.l10n_ec_printer_id:
            number_split = number.split('-')
            number = number_split[len(number_split)-1]
            number = self.l10n_ec_printer_id.prefix + number.zfill(9)
        self.l10n_latam_document_number = number

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
            new_payment_method_lines = self.env['l10n_ec.invoice.payment.method']
            existing_payment_method_lines = self.l10n_ec_invoice_payment_method_ids
            for line in existing_move_lines:
                #Como es para reportar al SRI se computa en base al date_invoice y no en base al date_start_payment_term
                percentage = 0.0
                if self.amount_total > 0.0:
                    percentage = round((float(line.debit) * 100.0 / float(self.amount_total)), 3)
                days_payment_term = 0
                if line.date_maturity:
                    invoice_date = self.invoice_date or fields.Date.context_today(self)
                    days_payment_term = (line.date_maturity - invoice_date).total_seconds() / (3600 * 24)
                if existing_lines_index < len(existing_payment_method_lines):
                    candidate = existing_payment_method_lines[existing_lines_index]
                    existing_lines_index += 1
                    candidate.update({
                        'payment_method_id': self.l10n_ec_payment_method_id.id,
                        'days_payment_term': days_payment_term,
                        'percentage': percentage,
                        'amount': line.debit
                    })
                else:
                    create_method = in_draft_mode and self.env['l10n_ec.invoice.payment.method'].new or self.env['l10n.ec.invoice.payment.method'].create
                    candidate = create_method({
                        'payment_method_id': self.l10n_ec_payment_method_id.id,
                        'days_payment_term': days_payment_term,
                        'percentage': percentage,
                        'amount': line.debit,
                        'move_id': self.id
                    })
                new_payment_method_lines += candidate
            self.l10n_ec_invoice_payment_method_ids -= existing_payment_method_lines - new_payment_method_lines
    
    def post(self):
        '''
        Invocamos el metodo post para setear el numero de factura en base a la secuencia del punto de impresion
        cuando se usan documentos(opcion del diario) las secuencias del diario no se ocupan
        '''
        for invoice in self:
            if not invoice.company_id.vat:
                raise ValidationError(u'Please setup your VAT number in the company form')
        res = super(AccountMove, self).post() #TODO JOSE: Al llamar a super ya nos comemos las secuencias nativas, deberíamos comernoslas una sola vez
        for invoice in self:
            if invoice.l10n_latam_country_code == 'EC':
                #Facturas de ventas electronicas
                if invoice.type in ('out_invoice') and invoice.l10n_ec_printer_id.allow_electronic_document:
                    for document in invoice.edi_document_ids:
                        if document.state in ('to_send'):
                            #needed to print offline RIDE and populate request after validations
                            document._l10n_ec_set_access_key()
                            self.l10n_ec_authorization = document.l10n_ec_access_key #for auditing manual changes
                            document._l10n_ec_generate_request_xml_file()
        return res
    
    def view_credit_note(self):
        '''
        '''
        [action] = self.env.ref('account.action_move_out_refund_type').read()
        action['domain'] = [('id', 'in', self.reversal_move_id.ids)]
        return action
 
    @api.model
    def _default_l10n_ec_printer_id(self):
        '''
        Este metodo obtiene el punto de emisión configurado en las preferencias del usuario, en caso
        que no tenga, se obtiene el primer punto de impresion que exista generalmente es el 001-001
        '''
        if self._context.get('default_l10n_ec_printer_id'):
            printer_id = self.env['l10n_ec.printer.id'].browse(self._context['default_l10n_ec_printer_id'])
            return printer_id
        printer_id = False
        if self.env.company.country_id.code == 'EC': #self.l10n_latam_country_code is still empty
            printer_id = self.env.user.l10n_ec_printer_id.id
            if not printer_id: #search first printer point
                printer_id = self.env['l10n_ec.sri.printer.point'].search([('company_id', '=', company_id)], order="sequence asc", limit=1)
        return printer_id

    @api.model
    def _default_l10n_ec_payment_method_id(self):
        '''
        Este metodo obtiene el punto de emisión configurado en las preferencias del usuario, en caso
        que no tenga, se obtiene el primer punto de impresion que exista generalmente es el 001-001
        '''
        payment_method_id = False
        if self.l10n_latam_country_code == 'EC':
            if self.type in ['out_invoice', 'in_invoice']:
                payment_method_id = self.env['l10n_ec.payment.method'].search([], order="sequence asc", limit=1)
        return payment_method_id
        
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
                if line.l10n_ec_payment_method_id.code == '01':
                    effective_method += line.amount
                #Dinero Electrónico
                elif line.l10n_ec_payment_method_id.code == '17':
                    electronic_method += line.amount
                #Tarjetas Débito/Crédito
                elif line.l10n_ec_payment_method_id.code in ('10','11','16','18','19'):
                    card_method += line.amount
                #Otros
                else:
                    other_method += line.amount
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
            l10n_ec_base_doce_iva = 0.0
            l10n_ec_vat_doce_subtotal = 0.0
            l10n_ec_base_cero_iva = 0.0
            l10n_ec_base_tax_free = 0.0
            l10n_ec_base_not_subject_to_vat = 0.0
            for invoice_line in invoice.invoice_line_ids:
                l10n_ec_total_discount += invoice_line.l10n_ec_total_discount
            for move_line in invoice.line_ids:
                if move_line.tax_group_id:
                    if move_line.tax_group_id.l10n_ec_type in ['vat12', 'vat14']:
                        l10n_ec_base_doce_iva += move_line.tax_base_amount
                        l10n_ec_vat_doce_subtotal += move_line.price_subtotal
                    if move_line.tax_group_id.l10n_ec_type in ['zero_vat']:
                        l10n_ec_base_cero_iva += move_line.tax_base_amount
                    if move_line.tax_group_id.l10n_ec_type in ['exempt_vat']:
                        l10n_ec_base_tax_free += move_line.tax_base_amount
                    if move_line.tax_group_id.l10n_ec_type in ['not_charged_vat']:
                        l10n_ec_base_not_subject_to_vat += move_line.tax_base_amount
            invoice.l10n_ec_total_discount = l10n_ec_total_discount
            invoice.l10n_ec_base_doce_iva = l10n_ec_base_doce_iva
            invoice.l10n_ec_vat_doce_subtotal = l10n_ec_vat_doce_subtotal
            invoice.l10n_ec_base_cero_iva = l10n_ec_base_cero_iva
            invoice.l10n_ec_base_tax_free = l10n_ec_base_tax_free
            invoice.l10n_ec_base_not_subject_to_vat = l10n_ec_base_not_subject_to_vat

    def _get_document_type_sequence(self):
        """ Return the match sequences for the given journal and invoice """
        self.ensure_one()
        if self.l10n_latam_country_code == 'EC':
            res = self.l10n_ec_printer_id.l10n_ec_sequence_ids.filtered(
                lambda x: x.l10n_latam_document_type_id == self.l10n_latam_document_type_id)
            return res
        return super()._get_document_type_sequence()

    @api.depends('l10n_latam_document_type_id', 'l10n_ec_printer_id')
    def _compute_l10n_latam_sequence(self):
        recs_with_l10n_ec_printer_id = self.filtered('l10n_ec_printer_id')
        for rec in recs_with_l10n_ec_printer_id:
            rec.l10n_latam_sequence_id = rec._get_document_type_sequence()
        remaining = self - recs_with_l10n_ec_printer_id
        remaining.l10n_latam_sequence_id = False
    
    
    def button_draft(self):
        if self.l10n_latam_country_code == 'EC':
            for move in self:
                if move.edi_document_ids:
                    raise UserError(_(
                        "You can't set to draft the journal entry %s because an electronic document has already been requested. "
                        "Please leave this document in cancel state and create a new one instead"
                    ) % move.display_name)
        res = super().button_draft()
        return res
    
    l10n_ec_printer_id = fields.Many2one(
        'l10n_ec.sri.printer.point',
        string='Punto de emisión', readonly = True,
        states = {'draft': [('readonly', False)]},
        default=_default_l10n_ec_printer_id,
        ondelete='restrict',
        help='The tax authority authorized printer point from where to send or receive invoices'
        )
    l10n_ec_authorization = fields.Char(
        string='Autorización', readonly = True,
        states = {'draft': [('readonly', False)]},
        help='Authorization number for issuing the tributary document, assigned by SRI, can be 10 numbers long, 41, or 49.'
        )
    l10n_ec_payment_method_id = fields.Many2one(
        'l10n_ec.payment.method',
        string='Forma de pago', readonly = True,
        states = {'draft': [('readonly', False)]},
        ondelete='restrict',
        help='Payment method to report to tax authority, if unknown select the most likely option'
        )
    l10n_ec_invoice_payment_method_ids = fields.One2many(
        'l10n_ec.invoice.payment.method',
        'move_id',
        string='Payment Methods',
        copy=True,
        help='Estos valores representan la forma estimada de pago de la factura, son '
             'utilizados con fines informativos en documentos impresos y documentos '
             'electrónicos. No tienen efecto contable.'
        )
    l10n_ec_effective_method = fields.Float(
        compute='compute_payment_method',
        string='Effective', 
        digits=dp.get_precision('Account'),
        method=True,
        help='Es la sumatoria de las formas de pago con código 01.'
        )
    l10n_ec_electronic_method = fields.Float(
        compute='compute_payment_method',
        string='Electronic Money',
        digits=dp.get_precision('Account'),
        method=True,
        help='Es la sumatoria de las formas de pago con código 17.'
        )
    l10n_ec_card_method = fields.Float(
        compute='compute_payment_method',
        string='Card Credit / Debit', 
        digits=dp.get_precision('Account'),
        method=True,
        help='Es la sumatoria de las formas de pago con códigos 10, 11, 16, 18, 19.'
        )
    l10n_ec_other_method = fields.Float(
        compute='compute_payment_method',
        string='Others', 
        digits=dp.get_precision('Account'),
        method=True,
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
    l10n_ec_base_doce_iva = fields.Monetary(
        string='VAT 12 Base',
        compute='_compute_total_invoice_ec',
        method=True,
        store=False, 
        readonly=True, 
        help='Summation of total prices included discount of products that tax VAT 12%'
        )
    l10n_ec_vat_doce_subtotal = fields.Monetary(
        string='VAT Value 12', 
        compute='_compute_total_invoice_ec', 
        method=True, 
        store=False,
        readonly=True, 
        help='Generated VAT'
        )
    l10n_ec_base_cero_iva = fields.Monetary(
        string='VAT 0 Base', 
        compute='_compute_total_invoice_ec', 
        method=True,
        store=False,
        readonly=True,
        help='Sum of total prices included discount of products that tax VAT 0%'
        )
    l10n_ec_base_tax_free = fields.Monetary(
        string='Base Exempt VAT',
        compute='_compute_total_invoice_ec',
        method=True,
        store=False,
        readonly=True,
        help='Sum of total prices included discount of products exempt from VAT'
        )    
    l10n_ec_base_not_subject_to_vat = fields.Monetary(
        string='Base Not Object VAT',
        compute='_compute_total_invoice_ec',
        method=True,
        store=False,
        readonly=True, 
        help='Sum of total prices included discount of products not subject to VAT'
        )


class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    def _compute_total_invoice_line_ec(self):
        '''
        '''
        for line in self:
            total_discount = 0.0
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
    _name = 'l10n_ec.invoice.payment.method'
    
    payment_method_id = fields.Many2one(
        'l10n_ec.payment.method',
        string='Way to Pay', 
        help='Way of payment of the SRI'
        )
    days_payment_term = fields.Integer(
        string='Days Payment Term', 
        help='Payment term in days'
        )
    percentage = fields.Float(
        string='Percentage',
        digits=(3,3),
        help='Percentage of the amount of the payment'
        )
    amount = fields.Float(
        string='Amount',
        digits=(16,2), 
        help='Is the pay value for this payment method'
        )
    move_id = fields.Many2one(
        'account.move',
        required=True,
        string='Invoice', 
        help='This field help to relate to account invoice object'
        )

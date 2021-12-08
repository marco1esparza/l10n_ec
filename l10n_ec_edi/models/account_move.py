# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_compare
import re


class AccountMove(models.Model):
    _inherit='account.move'
    
    @api.onchange('l10n_ec_printer_id')
    def onchange_l10n_ec_printer_id(self):
        #Resets the document number when the printer point is changed
        if self.country_code == 'EC':
            self.l10n_latam_document_number = False

    @api.onchange('l10n_latam_document_number')
    def onchange_l10n_latam_document_number(self):
        #Autofills document number when needed
        if self.country_code == 'EC' and self.journal_id.l10n_latam_use_documents and self.l10n_latam_document_number:
            regex = '(\d{3})+\-(\d{3})+\-(\d{9})'
            if re.match(regex, self.l10n_latam_document_number):
                return #if matches ###-###-######### do nothing
            prefix = False
            number = self.l10n_latam_document_number
            prefix_regex = '(\d{3})+\-(\d{3})+\-'
            if re.match(prefix_regex, number[0:8]):
                prefix = number[0:8]
                number = number[8:]
            number = number.zfill(9)
            if not prefix:
                #Add the prefix, from the printer point when my company issues the document
                prefix = '999-999-'
                if self.l10n_latam_document_type_id.l10n_ec_authorization == 'third':
                    prefix = '001-001-'
                if self.l10n_latam_document_type_id.l10n_ec_authorization == 'own':
                    prefix = self.l10n_ec_printer_id.name + '-'
            self.l10n_latam_document_number = prefix + number
        else:
            # Se manda a computar l10n_latam_document_number de forma manual para documentos no tributarios
            # al igual que asientos manuales debido a que el onchange desactiva el compute
            self._compute_l10n_latam_document_number()
    
    def _l10n_ec_validate_number(self):
        #Check invoice number is like ###-###-#########, and prefix corresponds to printer point
        regex = '(\d{3})+\-(\d{3})+\-(\d{9})'
        if not re.match(regex, self.l10n_latam_document_number):
            raise ValidationError(u'The document number should be like ###-###-#########')
        prefix_to_validate = False
        if self.l10n_latam_document_type_id.l10n_ec_authorization == 'none':
            prefix_to_validate = '999-999-' #No tan seguro que sea necesario pero veamos que dicen los usuarios
        if self.l10n_latam_document_type_id.l10n_ec_authorization == 'own': #only when printer point is used
            prefix_to_validate = self.l10n_ec_printer_id.name + '-'
        if prefix_to_validate:
            if self.l10n_latam_document_number[0:8] != prefix_to_validate:
                raise ValidationError("Acorde a la configuración del tipo de documento, el prefijo del número de documento debería empezar con %s" % prefix_to_validate)
    
    @api.onchange('invoice_date', 'invoice_payment_term_id', 'l10n_ec_payment_method_id', 'invoice_line_ids', 'invoice_date_due')
    def onchange_set_l10n_ec_invoice_payment_method_ids(self):
        '''
        Con el cambio de los plazos al partner computamos las formas de pago a reportar al SRI
        Computamos las formas de pago en base a los plazos de pago
        '''
        self.ensure_one() #se ha probado el programa para una sola factura a la vez
        if self.move_type in 'out_invoice' and self.country_code == 'EC':
            in_draft_mode = self != self._origin
            existing_move_lines = self.line_ids.filtered(lambda line: (line.account_id.user_type_id.type or '') in ('receivable'))
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
                    create_method = in_draft_mode and self.env['l10n_ec.invoice.payment.method'].new or self.env['l10n_ec.invoice.payment.method'].create
                    candidate = create_method({
                        'payment_method_id': self.l10n_ec_payment_method_id.id,
                        'days_payment_term': days_payment_term,
                        'percentage': percentage,
                        'amount': line.debit,
                        'move_id': self.id
                    })
                new_payment_method_lines += candidate
            self.l10n_ec_invoice_payment_method_ids -= existing_payment_method_lines - new_payment_method_lines

    def is_invoice(self, include_receipts=False):
        # WARNING: For Ecuador we consider is_invoice for all edis (invoices, wihtholds, waybills, etc)
        if self.country_code == 'EC':
            if self.move_type in self.get_invoice_types(include_receipts):
                return True
            elif self.is_withholding():
                return True
            elif self.is_waybill():
                return True
            return False
        return super(AccountMove, self).is_invoice(include_receipts)
        #Hack, permite enviar por mail documentos distintos de facturas
        # is_invoice = super(AccountMove, self).is_invoice(include_receipts)
        # if self._context.get('l10n_ec_send_email_others_docs', False):
        #     if self.is_withholding():
        #         is_invoice = True
        # return is_invoice
        #  
        # def _compute_access_url(self):
        #     #para que el boton ver documento permita abrir el coprobante de retención
        #     super(AccountMove, self)._compute_access_url()
        #     for move in self.filtered(lambda move: move.is_withholding()):
        #         #TODO V15 agregar un controlador que reemplace invoices con withholds
        #         move.access_url = '/my/invoices/%s' % (move.id)
        #  
        # def _get_report_base_filename(self):
        #     #bypass core restriction to also print withholds and waybills
        #     #TODO V15: Call super
        #     if any(not move.is_invoice() and not move.is_withholding() and not move.is_waybill() for move in self):
        #         raise UserError(_("Only invoices, withholds and waybills could be printed."))
        #     return self._get_move_display_name()
        
    def is_withholding(self):
        return False
    
    def is_waybill(self):
        return False

    def _creation_message(self):
        # OVERRIDE, waybill and withholds have different types than an invoice
        if self.is_withholding():
            return _('Withhold Created')
        elif self.is_waybill():
            return _('Waybill Created')
        else:
            return super()._creation_message()
        
    def action_invoice_sent(self):
        #Reemplazamos la plantilla de account_edi por la nuestra, con tipo de documento, portal, y mejoras
        res = super(AccountMove, self).action_invoice_sent()
        if self.country_code == 'EC' and self.journal_id.l10n_latam_use_documents:
            template = self.env.ref('l10n_ec_edi.l10n_ec_email_template_edi_document')
            res['context']['default_template_id'] = template.id
        return res

    @api.onchange('partner_id', 'l10n_latam_document_type_id', 'l10n_ec_available_sri_tax_support_ids')
    def _onchange_l10n_ec_available_sri_tax_support_ids(self):
        '''
        '''
        if self.country_code == 'EC':
            #Solamente las compras tienen sustento tributario...
            if self.move_type in ['in_invoice', 'in_refund']:
                l10n_ec_sri_tax_support_id = False
                if self.l10n_latam_document_type_id:
                    if self.l10n_ec_available_sri_tax_support_ids:
                        #Usamos _origin para obtener el id del registro y evitar algo como lo sig: NewId: <NewId origin=2>
                        l10n_ec_sri_tax_support_id = self.l10n_ec_available_sri_tax_support_ids[0]._origin.id
                self.l10n_ec_sri_tax_support_id = l10n_ec_sri_tax_support_id

    def button_cancel(self):
        # validate number format of void documents when voiding draft documents
        for invoice in self.filtered(lambda x: x.country_code == 'EC' and x.l10n_latam_use_documents and x.state == 'draft'):
            if not invoice._context.get('procesing_edi_job',False): #bypass pues Odoo se da doble vuelta en la aprobación
                is_edi_needed = False
                for edi_format in invoice.journal_id.edi_format_ids.filtered(lambda e: e.code == 'l10n_ec_tax_authority'):
                    is_edi_needed = edi_format._is_required_for_invoice(invoice)
                if is_edi_needed:
                    raise ValidationError(_('%s: El punto de emisión está configurado para documentos electrónicos, debió primero aprobarlo en el SRI y luego aplastar el botón de ANULACIÓN EDI') % invoice.name)
            invoice._l10n_ec_validate_number()
        res = super().button_cancel()
        return res
    
    def _post(self, soft=True):
        '''
        Invocamos el metodo post para setear el numero de factura en base a la secuencia del punto de impresion
        cuando se usan documentos(opcion del diario) las secuencias del diario no se ocupan
        '''
        res = super(AccountMove, self)._post(soft)
        #Comentado pues ahora la opción is_invoice() retorna True para retenciones y guías
        #self.generate_other_documents_edi() #antes de ejecutar nuestras validaciones, por eso no puede estar en l10n_ec_withhold
        for invoice in self.filtered(lambda x: x.country_code == 'EC' and x.l10n_latam_use_documents):
            if not invoice.is_invoice():
                # ideally we should call a line like
                # if not invoice.is_invoice() and not invoice.is_withholding()
                # but for v14 we consider is_invoice to include all edis
                raise ValidationError(u'Para Ecuador por favor desactivar la opcion Usa Documentos del Diario %s.' % invoice.journal_id.name)
            if invoice.l10n_latam_document_type_id.l10n_ec_require_vat:
                if not invoice.partner_id.l10n_latam_identification_type_id:
                    raise ValidationError(_('Indicate a type of identification for the provider "%s".') % invoice.partner_id.name)
                if not invoice.partner_id.vat:
                    raise ValidationError(_('Enter an identification number for the provider "%s".') % invoice.partner_id.name)
            invoice._l10n_ec_validate_number()
            if not invoice.l10n_ec_invoice_payment_method_ids:
                #autofill, usefull as onchange is not called when invoicing from other modules (ie subscriptions) 
                invoice.onchange_set_l10n_ec_invoice_payment_method_ids()
            # in v14 we also have edi document "factur-x" for interchanging docs among differente odoo instances
            edi_ec = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'l10n_ec_tax_authority')
            if edi_ec.state or 'no_edi' in ('to_send'): #if an electronic document is on the way
                if not invoice.company_id.vat:
                    raise ValidationError(_('Please setup your VAT number in the company form'))
                if not invoice.company_id.street:
                    raise ValidationError(_('Please setup the your company address in the company form'))
                if not invoice.l10n_ec_printer_id.printer_point_address:
                    raise ValidationError(_('Please setup the printer point address, in Accounting / Settings / Printer Points'))
                #needed to print offline RIDE and populate XML request
                edi_ec._l10n_ec_set_access_key()
                self.l10n_ec_authorization = edi_ec.l10n_ec_access_key #for auditing manual changes
                edi_ec._l10n_ec_generate_request_xml_file() #useful for troubleshooting
        return res
    
    #comentado pues ahora el is_invoice() incluye retenciones y guías
    # def generate_other_documents_edi(self):
    #     #como la opcion is_invoice es False para las retenciones, repetimos el codigo que genera los EDIs, extraido de account_edi
    #     edi_document_vals_list = []
    #     for move in self:
    #         for edi_format in move.journal_id.edi_format_ids:
    #             is_edi_needed = (move.is_withholding() or move.is_waybill()) and edi_format._is_required_for_invoice(move)
    #             if is_edi_needed:
    #                 existing_edi_document = move.edi_document_ids.filtered(lambda x: x.edi_format_id == edi_format)
    #                 if existing_edi_document:
    #                     existing_edi_document.write({
    #                         'state': 'to_send',
    #                         'attachment_id': False,
    #                     })
    #                 else:
    #                     edi_document_vals_list.append({
    #                         'edi_format_id': edi_format.id,
    #                         'move_id': move.id,
    #                         'state': 'to_send',
    #                     })
    #     self.env['account.edi.document'].create(edi_document_vals_list)
    #     self.edi_document_ids._process_documents_no_web_services()

    def _is_manual_document_number(self):
        #overriden in l10n_ec_account_extended
        if self.l10n_latam_use_documents and self.country_code == 'EC':
            doc_code = self.l10n_latam_document_type_id.code or ''
            l10n_ec_type = self.l10n_latam_document_type_id.l10n_ec_type or ''
            if self.journal_id.type == 'purchase' and doc_code not in ['03', '41']:
                return True
            elif self.journal_id.type == 'purchase' and doc_code in ['41'] and self.l10n_latam_document_type_id.l10n_ec_authorization == 'third':
                return True
            elif self.journal_id.type == 'general' and doc_code in ['07'] and l10n_ec_type in ['out_withhold']:
                return True
            else:
                return False
        else:
            super()._is_manual_document_number()
    
    def view_credit_note(self):
        [action] = self.env.ref('account.action_move_out_refund_type').sudo().read()
        action['domain'] = [('id', 'in', self.reversal_move_id.ids)]
        return action
 
    @api.model
    def _default_l10n_ec_printer_id(self):
        #Gets the first printer point by its sequence as default value, usually 001-001
        #Overriden with extended features in l10n_ec_account_extended
        printer_id = False
        company_id = self.env.company #self.country_code is still empty
        if company_id.country_code == 'EC':
            move_type = self._context.get('default_move_type',False) or self._context.get('default_withhold_type',False) or self._context.get('default_waybill_type', False) #self.type is not yet populated
            if move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_withhold', 'out_waybill']:
                #regular account.move doesn't need a printer point
                printer_id = self.env['l10n_ec.sri.printer.point'].search([('company_id', '=', company_id.id)], order="sequence asc", limit=1)
        return printer_id

    @api.model
    def _default_l10n_ec_payment_method_id(self):
        '''
        Este metodo obtiene el punto de emisión configurado en las preferencias del usuario, en caso
        que no tenga, se obtiene el primer punto de impresion que exista generalmente es el 001-001
        '''
        
        if self._context.get('default_l10n_ec_payment_method_id'):
            payment_method_id = self.env['l10n_ec.payment.method'].browse(self._context['default_l10n_ec_payment_method_id'])
            return payment_method_id
        payment_method_id = False
        company_id = self.env.company #self.country_code is still empty
        if company_id.country_code == 'EC':
            move_type = self._context.get('default_move_type',False) #self.type is not yet populated
            if move_type in ['out_invoice', 'in_invoice']:
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
            for line in invoice.filtered(lambda x:x.country_code == 'EC').l10n_ec_invoice_payment_method_ids:
                if line.payment_method_id.code == '01': #Efectivo
                    effective_method += line.amount
                elif line.payment_method_id.code == '17': #Dinero Electrónico
                    electronic_method += line.amount
                elif line.payment_method_id.code in ('10','11','16','18','19'): #Tarjetas Débito/Crédito
                    card_method += line.amount
                else: #Otros
                    other_method += line.amount
            invoice.l10n_ec_effective_method = effective_method
            invoice.l10n_ec_electronic_method = electronic_method
            invoice.l10n_ec_card_method = card_method
            invoice.l10n_ec_other_method = other_method
    
    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.country_code == 'EC' \
                and self.move_type in ('out_invoice', 'out_refund') and self.l10n_latam_document_type_id.code in ['04', '18', '05', '41']:
            return 'l10n_ec_edi.report_invoice_document'
        elif self.l10n_latam_use_documents and self.country_code == 'EC' \
                and self.move_type in ('in_invoice') and self.l10n_latam_document_type_id.code in ['03', '41'] \
                and self.l10n_latam_document_type_id.l10n_ec_authorization == 'own':
            return 'l10n_ec_edi.report_invoice_document'
        return super(AccountMove, self)._get_name_invoice_report()
    
    def _compute_total_invoice_ec(self):
        '''
        '''
        for invoice in self:
            l10n_ec_total_discount = 0.0
            l10n_ec_base_doce_iva = 0.0
            l10n_ec_vat_doce_subtotal = 0.0
            l10n_ec_base_cero_iva = 0.0
            l10n_ec_vat_cero_subtotal = 0.0
            l10n_ec_base_tax_free = 0.0
            l10n_ec_base_not_subject_to_vat = 0.0
            l10n_ec_total_irbpnr = 0.0
            l10n_ec_total_to_withhold = 0.0
            for invoice_line in invoice.invoice_line_ids:
                l10n_ec_total_discount += invoice_line.l10n_ec_total_discount
            for move_line in invoice.line_ids:
                if move_line.tax_group_id:
                    if move_line.tax_group_id.l10n_ec_type in ['vat12', 'vat14']:
                        l10n_ec_base_doce_iva += move_line.tax_base_amount
                        l10n_ec_vat_doce_subtotal += move_line.price_subtotal
                    if move_line.tax_group_id.l10n_ec_type in ['zero_vat']:
                        l10n_ec_base_cero_iva += move_line.tax_base_amount
                        l10n_ec_vat_cero_subtotal += move_line.price_subtotal
                    if move_line.tax_group_id.l10n_ec_type in ['exempt_vat']:
                        l10n_ec_base_tax_free += move_line.tax_base_amount
                    if move_line.tax_group_id.l10n_ec_type in ['not_charged_vat']:
                        l10n_ec_base_not_subject_to_vat += move_line.tax_base_amount
                    if move_line.tax_group_id.l10n_ec_type in ['irbpnr']:
                        l10n_ec_total_irbpnr += move_line.price_subtotal
                    elif move_line.tax_group_id.l10n_ec_type in ['withhold_vat', 'withhold_income_tax']:
                        l10n_ec_total_to_withhold += move_line.price_subtotal
            invoice.l10n_ec_total_discount = l10n_ec_total_discount
            invoice.l10n_ec_base_doce_iva = l10n_ec_base_doce_iva
            invoice.l10n_ec_vat_doce_subtotal = l10n_ec_vat_doce_subtotal
            invoice.l10n_ec_base_cero_iva = l10n_ec_base_cero_iva
            invoice.l10n_ec_vat_cero_subtotal =  l10n_ec_vat_cero_subtotal
            invoice.l10n_ec_base_tax_free = l10n_ec_base_tax_free
            invoice.l10n_ec_base_not_subject_to_vat = l10n_ec_base_not_subject_to_vat            
            invoice.l10n_ec_total_irbpnr = l10n_ec_total_irbpnr
            invoice.l10n_ec_total_with_tax = invoice.amount_untaxed + invoice.l10n_ec_vat_cero_subtotal + invoice.l10n_ec_vat_doce_subtotal + invoice.l10n_ec_total_irbpnr
            invoice.l10n_ec_total_to_withhold = l10n_ec_total_to_withhold

    @api.depends('l10n_latam_document_type_id', 'l10n_ec_printer_id')
    def _compute_name(self):
        # Se computa tomando en cuenta tambien cambios en el Punto de Emision.
        super(AccountMove, self)._compute_name()
            
    def _get_formatted_sequence(self, number=0):
        return "%s-%09d" % (self.l10n_ec_printer_id.name, number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.journal_id.l10n_latam_use_documents and self.env.company.country_id == self.env.ref('base.ec'):
            if self.l10n_ec_printer_id:
                return self._get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        if self.company_id.country_code == 'EC' and self.l10n_latam_use_documents:
            where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
            if self.l10n_latam_document_type_id and self.l10n_ec_printer_id:
                l10n_latam_document_type_id = self.l10n_latam_document_type_id
                # Se obtiene el sequence para el l10n_latam_document_type_id correspondiente con
                # 18 - Factura de Venta
                if self.l10n_latam_document_type_id == self.env.ref('l10n_ec.ec_59'):
                    l10n_latam_document_type_id += self.env.ref('l10n_ec.ec_04')
                # Verificamos si el documento es 18 - Factura de Venta
                # a traves de su reference id
                elif self.l10n_latam_document_type_id == self.env.ref('l10n_ec.ec_04'):   #Factura de Venta
                    l10n_latam_document_type_id += self.env.ref('l10n_ec.ec_59')
                # Verificamos si el documento es 41 - Liquidación de Compras Emitida por Reembolso de Gastos
                # a traves de su reference id
                elif self.l10n_latam_document_type_id == self.env.ref('l10n_ec.ec_57'):
                    l10n_latam_document_type_id += self.env.ref('l10n_ec.ec_08')
                # Verificamos si el documento es 03 - Liquidación de Compras
                # a traves de su reference id
                elif self.l10n_latam_document_type_id == self.env.ref('l10n_ec.ec_08'): #Liquidación de Compras
                    l10n_latam_document_type_id += self.env.ref('l10n_ec.ec_57')
                where_string += "AND l10n_ec_printer_id = %(l10n_ec_printer_id)s "
                # Creamos un IN para poder buscar por mas de un tipo de documento,
                # para poder saber cual es el ultimo Nro de documento asignado para tipos de documentos compartidos.
                where_string += "AND l10n_latam_document_type_id IN ("
                doctype_id = ','.join(str(x.id) for x in l10n_latam_document_type_id)
                if not doctype_id:
                    doctype_id = 0
                where_string += doctype_id
                where_string += ") "
                param.update({'l10n_ec_printer_id': self.l10n_ec_printer_id.id or 0})
        else:
            where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        return where_string, param

    @api.depends('reversal_move_id')
    def _get_refund_count(self):
        # Return the refund count
        for invoice in self:
            invoice.refund_count = len(invoice.reversal_move_id)

    def _get_additional_info(self):
        self.ensure_one()
        document = self.mapped('edi_document_ids')
        additional_info = []
        if document:
            additional_info = document[0]._get_additional_info()
        return additional_info
    
    @api.depends('l10n_latam_document_type_id')
    def _compute_l10n_ec_available_sri_tax_supports(self):
        '''
        '''
        for invoice in self:
            l10n_ec_available_sri_tax_support_ids = False
            if invoice.l10n_latam_document_type_id:
                l10n_ec_available_sri_tax_support_ids = invoice.l10n_latam_document_type_id.l10n_ec_sri_tax_support_ids
            invoice.l10n_ec_available_sri_tax_support_ids = l10n_ec_available_sri_tax_support_ids

    def _compute_l10n_ec_transaction_type(self):
        ''' 
        Este campo agrega un código de tipo de transación en base al partner y el tipo de operacion(compras, ventas)
        '''
        partner_obj = self.env['res.partner']
        for invoice in self:
            #TODO jm: evaluar con andres la logica del sig metodo "_get_type_vat_by_vat", en caso que se requiere implementarlo
            #y descomentar las siguientes 5 lineas de codigo, temporalmente voy a poner a la variable code_error en vacia para
            #que que no explote.
            code_error = ''
#             type_vat, code_error = partner_obj._get_type_vat_by_vat(
#                 invoice.invoice_country_id,
#                 invoice.invoice_vat,
#                 invoice.fiscal_position_id.transaction_type,
#             )
            invoice_type = invoice.move_type
            code = invoice.partner_id.l10n_ec_code
            # Determinamos el pais, para segun el código del país
            # hacer uno o otro procedimiento
            if not invoice.country_code:
                invoice.l10n_ec_transaction_type = 'Debe definir el país de la factura.'
                invoice.l10n_ec_transaction_type += ' Documento ' + str(invoice.l10n_latam_document_number or '')
                invoice.l10n_ec_transaction_type += ' Empresa ' + (invoice.partner_id.name or '')
            elif invoice_type in ['in_invoice', 'in_refund']: #COMPRAS
                # RUC
                if code == 'R':
                    invoice.l10n_ec_transaction_type = '01'
                # CEDULA
                elif code == 'C':
                    invoice.l10n_ec_transaction_type = '02'
                # PERS. JURÍDICA EXTRANJERA, PERS. NATURAL EXTRANJERA
                elif code == 'P':
                    invoice.l10n_ec_transaction_type = '03'
                # Este caso es especial, es un proveedor con tipo de compania detectada 
                # como nacional por la posicion fiscal pero el pais es extranjero
                elif code_error == 'ERROR_POSICION_FISCAL_Y_PAIS':
                    invoice.l10n_ec_transaction_type = 'Debe revisar la posicion fiscal del proveedor y el pais seleccionado para que guarden coherencia entre si.'                    
                    invoice.l10n_ec_transaction_type += ' Documento de Compra ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Proveedor ' + (invoice.partner_id.name or '')
                else:
                    #cubre el caso de code == 'O': #OTROS
                    #cubre otros casos no determinados
                    #no se usa tildes por problema de unicode al ats
                    invoice.l10n_ec_transaction_type = 'Proveedor no tiene asignado una identificacion (CEDULA/RUC/PASAPORTE) correcta.'
                    invoice.l10n_ec_transaction_type += ' Documento de Compra ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Proveedor ' + (invoice.partner_id.name or '')
            elif invoice_type in ['out_invoice', 'out_refund']: #VENTAS
                # RUC
                if code == 'R':
                    invoice.l10n_ec_transaction_type = '04'
                # CEDULA
                elif code == 'C':
                    invoice.l10n_ec_transaction_type = '05'
                # PERS. JURÍDICA EXTRANJERA, PERS. NATURAL EXTRANJERA
                elif code == 'P':
                    invoice.l10n_ec_transaction_type = '06'
                # CONSUMIDOR FINAL
                elif code == 'F':
                    invoice.l10n_ec_transaction_type = '07'
                # Este caso es especial, es un cliente con tipo de compania detectada 
                # como nacional por la posicion fiscal pero el pais es extranjero
                elif code_error == 'ERROR_POSICION_FISCAL_Y_PAIS':
                    invoice.l10n_ec_transaction_type = 'Debe revisar la posicion fiscal del cliente y el pais seleccionado para que guarden coherencia entre si.'
                    invoice.l10n_ec_transaction_type += ' Documento de Venta ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Cliente ' + (invoice.partner_id.name or '')
                else:
                    #cubre el caso de code == 'O': #OTROS
                    #cubre otros casos no determinados
                    #no se usa tildes por problema de unicode al ats
                    invoice.l10n_ec_transaction_type = 'Cliente no tiene asignado una identificacion (CEDULA/RUC/PASAPORTE) correcta.'
                    invoice.l10n_ec_transaction_type += ' Documento de Venta ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Cliente ' + (invoice.partner_id.name or '')
            elif not invoice.is_withholding() and not invoice.is_waybill():
                invoice.l10n_ec_transaction_type = 'La factura no tiene tipo... contacte a soporte tecnico.'
                invoice.l10n_ec_transaction_type += ' Documento ' + str(invoice.l10n_latam_document_number or '')
                invoice.l10n_ec_transaction_type += ' Empresa ' + (invoice.partner_id.name or '')
            else:
                invoice.l10n_ec_transaction_type = ''


    @api.depends('l10n_latam_document_type_id','l10n_ec_printer_id','state')
    def _show_edit_l10n_ec_authorization(self):
        for res in self:
            show_l10n_ec_authorization = False
            edit_l10n_ec_authorization = False
            if res.country_code == 'EC':
                # ideally we should call a line like
                # if res.is_invoice(): or res.is_withholding()
                # but for v14 we consider is_invoice to include all edis
                if res.is_invoice():
                    if res.l10n_ec_authorization_type == 'third':
                        show_l10n_ec_authorization = True
                        edit_l10n_ec_authorization = True
                    elif res.l10n_ec_authorization_type == 'own':
                        if res.l10n_ec_printer_id.allow_electronic_document:
                            if res.state in ['posted','cancel']:
                                #las autorizaciones emitidas por nosotros no se muestran en
                                #el estado borrador pues se generará en el flujo del documento electronico
                                show_l10n_ec_authorization = True
                        else:
                            #en documentos preimrpresos si mostramos el numero de autorización
                            #en todos los estadoss
                            show_l10n_ec_authorization = True
                            edit_l10n_ec_authorization = True
            res.show_l10n_ec_authorization = show_l10n_ec_authorization
            res.edit_l10n_ec_authorization = edit_l10n_ec_authorization

    l10n_ec_printer_id = fields.Many2one(
        'l10n_ec.sri.printer.point',
        string='Punto de emisión', readonly = True,
        states = {'draft': [('readonly', False)]},
        default = _default_l10n_ec_printer_id,
        ondelete='restrict',
        index=True,
        check_company=True,
        tracking=True,
        help='The tax authority authorized printer point from where to send or receive invoices'
        )
    l10n_ec_authorization = fields.Char(
        string='Autorización', readonly = True,
        copy = False,
        help='Authorization number for issuing the tributary document, assigned by SRI, can be 10 numbers long, 41, or 49.'
        )
    l10n_ec_payment_method_id = fields.Many2one(
        'l10n_ec.payment.method',
        string='Forma de pago', readonly = True,
        states = {'draft': [('readonly', False)]},
        default = _default_l10n_ec_payment_method_id,
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
    #functional fields
    l10n_ec_effective_method = fields.Monetary(
        compute='compute_payment_method',
        string='Effective', 
        tracking=True,
        help='Es la sumatoria de las formas de pago con código 01.'
        )
    l10n_ec_electronic_method = fields.Monetary(
        compute='compute_payment_method',
        string='Electronic Money',
        tracking=True,
        help='Es la sumatoria de las formas de pago con código 17.'
        )
    l10n_ec_card_method = fields.Monetary(
        compute='compute_payment_method',
        string='Card Credit / Debit',
        tracking=True,
        help='Es la sumatoria de las formas de pago con códigos 10, 11, 16, 18, 19.'
        )
    l10n_ec_other_method = fields.Monetary(
        compute='compute_payment_method',
        string='Others', 
        tracking=True,
        help='Es la sumatoria de las formas de pago con códigos 02, 03, 04, 05, 06, 08, 09, 12, 13, 14, 15, 20, 21.'
        )
    l10n_ec_total_discount = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total Discount',
        tracking=True,
        readonly=True,
        help='Total sum of the discount granted'
        )
    l10n_ec_base_doce_iva = fields.Monetary(
        string='VAT 12 Base',
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True, 
        help='Summation of total prices included discount of products that tax VAT 12%'
        )
    l10n_ec_vat_doce_subtotal = fields.Monetary(
        string='VAT Value 12', 
        compute='_compute_total_invoice_ec', 
        tracking=True,
        readonly=True, 
        help='Generated VAT'
        )
    l10n_ec_base_cero_iva = fields.Monetary(
        string='VAT 0 Base', 
        compute='_compute_total_invoice_ec', 
        tracking=True,
        readonly=True,
        help='Sum of total prices included discount of products that tax VAT 0%'
        )
    l10n_ec_vat_cero_subtotal = fields.Monetary(
        string='VAT Value 0',
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True,
        help=''
        )
    l10n_ec_base_tax_free = fields.Monetary(
        string='Base Exempt VAT',
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True,
        help='Sum of total prices included discount of products exempt from VAT'
        )    
    l10n_ec_base_not_subject_to_vat = fields.Monetary(
        string='Base Not Object VAT',
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True, 
        help='Sum of total prices included discount of products not subject to VAT'
        )
    l10n_ec_total_irbpnr = fields.Monetary(
        string='IRBPNR',
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True,
        help='Impuesto redimible a las botellas plásticas no retornables PET',
        )
    l10n_ec_total_with_tax = fields.Monetary(
        string='Total With Taxes', 
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True,
        help='Result of the sum of taxable amount plus the Value of VAT'
        )
    l10n_ec_total_to_withhold = fields.Monetary(
        string='Total to Withhold', 
        compute='_compute_total_invoice_ec',
        tracking=True,
        readonly=True,
        help='Sum of values to be retained'
        )
    l10n_ec_authorization_type = fields.Selection(related='l10n_latam_document_type_id.l10n_ec_authorization')
    refund_count = fields.Integer(string='Refund Count', compute='_get_refund_count', readonly=True)
    l10n_ec_available_sri_tax_support_ids = fields.Many2many(
        'l10n_ec.sri.tax.support', 
        compute='_compute_l10n_ec_available_sri_tax_supports'
        )
    l10n_ec_sri_tax_support_id = fields.Many2one(
        'l10n_ec.sri.tax.support',
        string='Tax Support',
        default=lambda self: self.env['l10n_ec.sri.tax.support'].search([], order='priority asc', limit=1),
        ondelete='restrict',
        help='Indicates the tax support for this document'
        )
    l10n_ec_transaction_type = fields.Char(
        compute='_compute_l10n_ec_transaction_type',
        string='Transaction Type EC',
        tracking=True,
        store=False,
        help='Indicate the transaction type that performer the partner. Supplier Invoice '
             '[01-RUC,02-CEDULA,03-PASAPORTE],Customer Invoice [04-RUC,05-CEDULA,06-PASAPORTE, '
             '07-CONSUMIDOR FINAL, 0-OTROS].'
        )
    show_l10n_ec_authorization = fields.Boolean(
        string='Mostrar Autorizacion',
        compute='_show_edit_l10n_ec_authorization',
    )
    edit_l10n_ec_authorization = fields.Boolean(
        string='Editar Autorizacion',
        compute='_show_edit_l10n_ec_authorization',
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
                    taxes_res = line.tax_ids._origin.compute_all(
                        line.price_unit, #se usa price unit para el escenario de impuestos incluidos en el precio
                        quantity=line.quantity, currency=line.currency_id, product=line.product_id, partner=line.partner_id,
                        is_refund=line.move_id.move_type in ('out_refund', 'in_refund'))
                    total_discount = taxes_res['total_excluded'] - line.l10n_latam_price_subtotal
                else:
                    total_discount = (line.quantity * line.l10n_latam_price_unit) - line.l10n_latam_price_subtotal
                #In case of multi currency, round before it's use for computing debit credit
                if line.currency_id:
                    total_discount = line.currency_id.round(total_discount)
            line.l10n_ec_total_discount = total_discount

    @api.depends('price_unit', 'price_subtotal', 'move_id.l10n_latam_document_type_id')
    def compute_l10n_latam_prices_and_taxes(self):
        for line in self:
            invoice = line.move_id
            included_taxes = False
            # For the unit price, we need the number rounded based on the product price precision.
            # The method compute_all uses the accuracy of the currency so, we multiply and divide for 10^(decimal accuracy of product price) to get the price correctly rounded.
            price_digits = 10 ** self.env['decimal.precision'].precision_get('Product Price')
            price_unit = line.tax_ids.with_context(round=False,
                                                   force_sign=invoice._get_tax_force_sign()).compute_all(
                line.price_unit * price_digits, invoice.currency_id, 1.0, line.product_id, invoice.partner_id)
            l10n_latam_price_unit = price_unit['total_excluded'] / price_digits
            l10n_latam_price_subtotal = line.price_subtotal
            not_included_taxes = line.tax_ids
            l10n_latam_price_net = l10n_latam_price_unit * (1 - (line.discount or 0.0) / 100.0)

            line.l10n_latam_price_subtotal = l10n_latam_price_subtotal
            line.l10n_latam_price_unit = l10n_latam_price_unit
            line.l10n_latam_price_net = l10n_latam_price_net
            line.l10n_latam_tax_ids = not_included_taxes

    #Columns
    l10n_ec_total_discount = fields.Monetary(
        string='Total Discount', 
        compute='_compute_total_invoice_line_ec', 
        tracking=True,
        store=False,
        readonly=True,                                     
        help='Indicates the monetary discount applied to the total invoice line.'
        )
    l10n_latam_price_unit = fields.Float(compute='compute_l10n_latam_prices_and_taxes', digits='Product Price')
    l10n_latam_price_subtotal = fields.Monetary(compute='compute_l10n_latam_prices_and_taxes')
    l10n_latam_price_net = fields.Float(compute='compute_l10n_latam_prices_and_taxes', digits='Product Price')
    l10n_latam_tax_ids = fields.One2many(compute="compute_l10n_latam_prices_and_taxes", comodel_name='account.tax')


class L10NECInvoicePaymentMethod(models.Model):
    _name = 'l10n_ec.invoice.payment.method' #TODO V15 cambiarle el nombre con el sufijo "lines"
    _description = "Ecuadorian Invoice Payment Method Detail"
    
    payment_method_id = fields.Many2one(
        'l10n_ec.payment.method',
        string='Way to Pay',
        ondelete='restrict',
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
        ondelete='cascade',
        string='Invoice', 
        help='This field help to relate to account invoice object'
        )

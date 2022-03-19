# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round
from odoo.exceptions import UserError, ValidationError

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        #Invocamos el name_search para restringir la seleccion de facturas en las lineas de retenciones
        if self.env.context.get('origin') == 'receive_withhold':
            return super(AccountMove, self)._name_search(name, args=[('id', 'in', self.env.context.get('l10n_ec_withhold_origin_ids'))], operator=operator, limit=limit, name_get_uid=name_get_uid)
        return super(AccountMove, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        
    def copy_data(self, default=None):
        #avoid duplicating withholds, it has not been tested
        res = super(AccountMove, self).copy_data(default=default)
        if self.is_withholding():
            raise ValidationError(u'No se permite duplicar las retenciones, si necesita crear una debe hacerlo desde la factura correspondiente.')
        return res

    def action_create_journal_items(self):
        if not self.is_withholding():
            raise ValidationError(u'This functionality is only available for withholdings.')
        return self.l10n_ec_make_withhold_entry()

    def _post(self, soft=True):
        '''
        Invocamos el metodo post para generar los asientos de retenciones de forma manual y conciliar
        los asientos de retenciones en ventas con la factura
        '''
        self.l10n_ec_make_withhold_entry()
        posted = super()._post(soft=soft)
        for withhold in self:
            if withhold.country_code == 'EC':
                if withhold.move_type in ('entry') and withhold.l10n_ec_withhold_type in ['out_withhold'] and withhold.l10n_latam_document_type_id.code in ['07']:
                    (withhold + withhold.l10n_ec_withhold_origin_ids).line_ids.filtered(lambda line: not line.reconciled and line.account_id == withhold.partner_id.property_account_receivable_id).reconcile()
        return posted 

    def button_cancel_posted_moves(self):
        # Verificamos si es una retencion y se puede ejecutar REQUEST EDI CANCELLATION
        res = super().button_cancel_posted_moves()
        to_cancel_documents = self.env['account.edi.document']
        for move in self:
            is_move_marked = False
            for doc in move.edi_document_ids:
                if doc.edi_format_id._needs_web_services() \
                        and doc.attachment_id \
                        and doc.state == 'sent' \
                        and move.is_withholding():
                    to_cancel_documents |= doc
                    is_move_marked = True
            if is_move_marked:
                move.message_post(body=_("A cancellation of the EDI has been requested."))

        to_cancel_documents.write({'state': 'to_cancel', 'error': False})
        return res

    @api.depends(
        'state',
        'edi_document_ids.state',
        'edi_document_ids.attachment_id')
    def _compute_edi_show_cancel_button(self):
        # Validacion de mostrar el REQUEST EDI CANCELATION a las retenciones
        for move in self:
            super(AccountMove, move)._compute_edi_show_cancel_button()
            if move.is_withholding():
                move.edi_show_cancel_button = any([doc.edi_format_id._needs_web_services()
                                                   and doc.attachment_id
                                                   and doc.state == 'sent'
                                                   and move.is_withholding()
                                                   for doc in move.edi_document_ids])

    def button_draft(self):
        '''
        '''
        res = super(AccountMove, self).button_draft()
        for withhold in self:
            if withhold.country_code == 'EC':
                if withhold.move_type in ('entry') and withhold.l10n_ec_withhold_type in ['in_withhold', 'out_withhold'] and withhold.l10n_latam_document_type_id.code in ['07']:
                    #delete account.move.lines for re-posting scenario in sale withholds and purchase withholds
                    withhold.line_ids.unlink()
        return res
    
    def l10n_ec_make_withhold_entry(self):
        '''
        Metodo para hacer asientos de retenciones
        '''
        account_move_line_obj =  self.env['account.move.line'] 
        for withhold in self:
            if withhold.country_code == 'EC':
                if withhold.move_type in ('entry') and withhold.l10n_ec_withhold_type in ['in_withhold', 'out_withhold'] and withhold.l10n_latam_document_type_id.code in ['07']:
                    electronic = False
                    if withhold.l10n_ec_printer_id and withhold.l10n_ec_printer_id.allow_electronic_document:
                        electronic = True
                    if not withhold.l10n_ec_withhold_origin_ids:
                        raise ValidationError(u'La retención debe tener al menos una factura asociada.')
                    if not withhold.l10n_ec_withhold_line_ids:
                        raise ValidationError(u'Debe ingresar al menos un impuesto para aprobar la retención.')
                    if withhold.l10n_ec_withhold_type in ['out_withhold'] and withhold.l10n_ec_total == 0.0:
                        raise ValidationError(u'La cantidad de la retención debe ser mayor a cero.')
                    if any(invoice.state not in ['posted'] for invoice in withhold.l10n_ec_withhold_origin_ids):
                        raise ValidationError(u'Solo se puede registrar retenciones sobre facturas abiertas o pagadas.')
                    withhold.l10n_ec_validate_accounting_parameters() #validaciones generales
                    withhold.l10n_ec_validate_related_invoices(withhold.l10n_ec_withhold_origin_ids) # Checks on invoice records
                    #delete account.move.lines for re-posting scenario in sale withholds and purchase withholds
                    withhold.line_ids.unlink()
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
                                account_move_line_obj.with_context(check_move_validity=False).create(vals)
                    #Retenciones en compras
                    if withhold.l10n_ec_withhold_type == 'in_withhold':
                        if withhold.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.filtered(lambda x: x.state == 'posted'):
                            raise ValidationError(u'Solamente se puede tener una retención aprobada por factura de proveedor.')
                        for line in withhold.l10n_ec_withhold_line_ids:
                            vals = {
                                'name': withhold.name,
                                'move_id': withhold.id,
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
                            account_move_line_obj.with_context(check_move_validity=False).create(vals)
                        if withhold.l10n_ec_withhold_line_ids:
                            vals = {
                                'name': withhold.name,
                                'move_id': withhold.id,
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
                            account_move_line_obj.with_context(check_move_validity=False).create(vals)

    def l10n_ec_validate_accounting_parameters(self):
        '''
        Validacion de configuraciones de diarios y cuentas contables
        '''
        error = ''
        list = []
        for invoice in self.l10n_ec_withhold_origin_ids:
            if self.invoice_date < invoice.invoice_date:
                list.append(invoice.name)
        if list:
            joined_vals = '\n'.join('* ' + l for l in list)
            error += u'Las siguientes facturas tienen una fecha posterior a la retención:\n%s\n' % joined_vals
        amount_total = 0.0
        for invoice in self.l10n_ec_withhold_origin_ids:
            amount_total += invoice.amount_total
        if self.l10n_ec_total > amount_total:
                error += u'La cantidad a retener es mayor que el valor residual de las facturas.\n'
        if error:
            raise ValidationError(error)

    def l10n_ec_validate_related_invoices(self, invoices, partner_id=False):
        '''
        Validaciones generales cuando hay facturas asociadas a la retención
        util en ventas y compras
        '''
        partner_id = partner_id or self.partner_id
        if any(invoice.state not in ['posted'] for invoice in invoices):
            raise ValidationError(u'Solo se pueden hacer retenciones sobre facturas aprobadas.')
        if invoices and any(inv.commercial_partner_id != invoices[0].commercial_partner_id for inv in invoices): #and not self.env.context.get('massive_withhold'):
            raise ValidationError(u'A fin de emitir retenciones sobre múltiples facturas, aquellas deben pertenecer a la misma empresa.')
        if invoices and partner_id.commercial_partner_id != invoices[0].commercial_partner_id:
            raise ValidationError(u'La empresa indicada en la retención no corresponde a la de las facturas.')
        if invoices and any(MAP_INVOICE_TYPE_PARTNER_TYPE[inv.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type] for inv in invoices):
            raise ValidationError(u'No puede mezclar facturas de clientes y de proveedores en la misma retención.')
        if invoices and any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            raise ValidationError(u'A fin de emitir retenciones sobre múltiples facturas, aquellas deben tener la misma moneda.')
        if self.move_type == 'in_invoice' and invoices and any(inv.l10n_ec_total_to_withhold == 0.0 for inv in invoices):
            raise ValidationError(u'El valor a retener en la factura de compra asociada debe ser mayor a cero.')
        #Validamos que para cada factura exista maximo una retención de IVA y una de renta
        #en todas las lineas de retención de todas las retenciónes asociadas a todas las facturas
        categories = self.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.l10n_ec_withhold_line_ids.tax_id.tax_group_id.mapped('l10n_ec_type')
        categories = list(set(categories)) #remueve duplicados
        for withhold_line in self.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.l10n_ec_withhold_line_ids:
            if withhold_line.move_id.state in ('posted') and withhold_line.move_id != self:
                if withhold_line.tax_id.tax_group_id.l10n_ec_type in categories:
                    if withhold_line.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
                        withhold_category = u'Retención IVA'
                    elif withhold_line.tax_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
                        withhold_category = u'Retención Renta'
                    error_msg = u'Una factura no puede tener dos retenciones por el mismo concepto.\n' + \
                                u'La retención previamente existente ' + withhold_line.move_id.name + \
                                u' tiene tambien una retención por ' + withhold_category + u'.'  
                    raise ValidationError(error_msg)

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        '''
        It allows generating zero entries when the tax amount is zero
        '''
        return super(AccountMove, self.with_context(generate_zero_entry=True))._recompute_tax_lines(recompute_tax_base_amount)

    def l10n_ec_add_withhold(self):
        #Creates a withhold linked to selected invoices
        for invoice in self:
            if not invoice.country_code == 'EC':
                raise ValidationError(u'Withhold documents are only aplicable for Ecuador')
            if invoice.state != 'posted':
                raise ValidationError(u'No se puede registrar la retención, el documento %s no está aprobado' %invoice.name)
            if not invoice.l10n_ec_allow_withhold:
                raise ValidationError(u'The selected document type does not support withholds')
            if len(self) > 1 and invoice.move_type != 'out_invoice':
                raise ValidationError(u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')
        if len(list(set(self.mapped('commercial_partner_id')))) > 1:
            raise ValidationError(u'Las facturas seleccionadas no pertenecen al mismo cliente.')
        self = self.with_context(include_business_fields=False) #don't copy sale/purchase links
        
        default_values = self._l10n_ec_prepare_withold_default_values()
        new_move = self.env['account.move'] #this is the new withhold
        new_move = self[0].copy(default=default_values)
        
        return self.l10n_ec_action_view_withholds()

    @api.depends('move_type')
    def _compute_invoice_filter_type_domain(self):
        '''
        Metodo para obtener solo diarios generales en Retenciones.
        '''
        for move in self:
            super(AccountMove, move)._compute_invoice_filter_type_domain()
            if move.l10n_ec_withhold_type and move.l10n_ec_withhold_type in ('in_withhold'):
                move.invoice_filter_type_domain = 'general'

    def _get_l10n_latam_documents_domain(self):
        #Filter document types according to ecuadorian type
        domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
        if self.l10n_ec_withhold_type:
            domain.extend([('l10n_ec_type', '=', self.l10n_ec_withhold_type)])
        return domain
    
    def _l10n_ec_prepare_withold_default_values(self):
        #Compras
        if self[0].move_type == 'in_invoice':
            move_type = 'entry' #'out_refund' #'out_withhold'
            #TODO ANDRES: Evaluar el metodo de l10n_latam que define el tipo de documento
            l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
                [('country_id.code', '=', 'EC'),
                 ('code', '=', '07'),
                 ('l10n_ec_type', '=', 'in_withhold'),
                 ], order="sequence asc", limit=1)
            journal_id = False
            journals = self.env['account.journal'].search([('code', '=', 'RCMPR')])
            if journals:
                journal_id = journals[0].id
            default_values = {
                    #'ref': '%s, %s' % (move.name, self.reason) if self.reason else move.name,
                    'invoice_date': False,
                    'journal_id': journal_id,
                    'invoice_payment_term_id': None,
                    'move_type': move_type,
                    'line_ids': [(5, 0, 0)],
                    'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
                    'l10n_ec_invoice_payment_method_ids':  [(5, 0, 0)],
                    'l10n_ec_authorization': False,
                    'l10n_ec_withhold_origin_ids': [(6, 0, self.ids)],
                    'l10n_ec_withhold_type': 'in_withhold',
                }
            l10n_ec_withhold_line_ids = []
            group_taxes = {}
            prec = self.env['decimal.precision'].precision_get('Account')
            for invoice in self:
                for line in invoice.line_ids:
                    for tax in line.withhold_tax_ids:
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
                            group_taxes[tax.id][2] +=  abs((line.price_total - line.price_subtotal) * tax.amount / 100)
            for tax_id, detail in group_taxes.items():
                l10n_ec_withhold_line_ids.append((0, 0, {
                    'tax_id': tax_id,
                    'account_id': detail[0].get('account_id'),
                    'invoice_id': detail[0].get('invoice_id'),
                    'base': float_round(detail[1], precision_digits=prec),
                    'amount': float_round(detail[2], precision_digits=prec)
                }))
            default_values.update({
                'l10n_ec_withhold_line_ids': l10n_ec_withhold_line_ids
            })
        #Ventas
        if self[0].move_type == 'out_invoice':
            move_type = 'entry' #'out_refund' #'out_withhold'
            #TODO ANDRES: Evaluar el metodo de l10n_latam que define el tipo de documento
            l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
                [('country_id.code', '=', 'EC'),
                 ('code', '=', '07'),
                 ('l10n_ec_type', '=', 'out_withhold'),
                 ], order="sequence asc", limit=1)
            journal_id = False
            journals = self.env['account.journal'].search([('code', '=', 'RVNTA')])
            if journals:
                journal_id = journals[0].id
            default_values = {
                    #'ref': '%s, %s' % (move.name, self.reason) if self.reason else move.name,
                    'invoice_date': False,
                    'journal_id': journal_id,
                    'invoice_payment_term_id': None,
                    'move_type': move_type,
                    'line_ids': [(5, 0, 0)],
                    'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
                    'l10n_ec_invoice_payment_method_ids':  [(5, 0, 0)],
                    'l10n_ec_authorization': False,
                    'l10n_ec_withhold_origin_ids': [(6, 0, self.ids)],
                    'l10n_ec_withhold_type': 'out_withhold',
                }
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
            
        return default_values
        
    def l10n_ec_action_view_withholds(self):
        '''
        '''
        action = 'account.action_move_journal_line'
        view = 'l10n_ec_withhold.view_move_form_withhold'
        action = self.env.ref(action)
        result = action.sudo().read()[0]
        result['name'] = _('Withholds')
        l10n_ec_withhold_ids = self.l10n_ec_withhold_ids.ids
        if len(l10n_ec_withhold_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(l10n_ec_withhold_ids) + ")]"
        else:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = l10n_ec_withhold_ids and l10n_ec_withhold_ids[0] or False
        return result

    def _compute_total_invoice_ec(self):
        '''
        '''
        res = super(AccountMove, self)._compute_total_invoice_ec()
        for invoice in self:
            l10n_ec_vat_withhold = 0.0
            l10n_ec_profit_withhold = 0.0
            l10n_ec_total_base_vat = 0.0
            l10n_ec_total_base_profit = 0.0
            for line in invoice.l10n_ec_withhold_line_ids:
                if line.tax_id.tax_group_id:
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat']:
                        l10n_ec_vat_withhold += line.amount
                        l10n_ec_total_base_vat += line.base
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                        l10n_ec_profit_withhold += line.amount
                        l10n_ec_total_base_profit += line.base
            invoice.l10n_ec_vat_withhold = l10n_ec_vat_withhold
            invoice.l10n_ec_profit_withhold = l10n_ec_profit_withhold
            invoice.l10n_ec_total_base_vat = l10n_ec_total_base_vat
            invoice.l10n_ec_total_base_profit = l10n_ec_total_base_profit
            invoice.l10n_ec_total = l10n_ec_vat_withhold + l10n_ec_profit_withhold
        return res
    
    def _l10n_ec_allow_withhold(self):
        #shows/hide "ADD WITHHOLD" button on invoices
        for invoice in self:
            result = False
            if invoice.country_code == 'EC' and invoice.state == 'posted':
                if invoice.l10n_latam_document_type_id.code in ['01','02','03','18']: #TODO ANDRES añadir codigos, revisar proyecto X
                    result = True
            invoice.l10n_ec_allow_withhold = result
    
    @api.depends('l10n_ec_withhold_ids')
    def _compute_l10n_ec_withhold_count(self):
        for invoice in self:
            count = len(self.l10n_ec_withhold_ids)
            invoice.l10n_ec_withhold_count = count
    
    @api.depends('l10n_ec_withhold_origin_ids.l10n_ec_base_doce_iva', 'l10n_ec_withhold_origin_ids.amount_untaxed')
    def _l10n_ec_compute_total_invoices(self):
        '''
        Computa subtotales que dependen de la factura, estos subtotales son 
        utilizados para sugerir valores al momento de crear la retención
        '''
        for invoice in self:
            #valor de arranque
            l10n_ec_invoice_vat_doce_subtotal = l10n_ec_invoice_amount_untaxed = 0.0
            #computamos
            invoice.l10n_ec_invoice_vat_doce_subtotal = sum(inv.l10n_ec_vat_doce_subtotal for inv in invoice.l10n_ec_withhold_origin_ids)
            invoice.l10n_ec_invoice_amount_untaxed = sum(inv.amount_untaxed for inv in invoice.l10n_ec_withhold_origin_ids)

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.company_id.country_id.code == 'EC' \
                and self.move_type in ('entry') and self.l10n_latam_document_type_id.code in ['07']:
            return 'l10n_ec_withhold.report_invoice_document'
        return super()._get_name_invoice_report()

    def is_withholding(self):
        is_withholding = False
        if self.country_code == 'EC' and self.move_type in ('entry') \
           and self.l10n_ec_withhold_type and self.l10n_ec_withhold_type in ('in_withhold', 'out_withhold') \
           and self.l10n_latam_document_type_id.code in ['07']:
            is_withholding = True
        return is_withholding

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        '''
        Se computa para retenciones de ventas, para poder obtener el total registrado en lal vista lista.
        '''
        super()._compute_amount()
        for move in self.filtered(lambda x: x.is_withholding() and x.l10n_ec_withhold_type == 'out_withhold'):
            total = 0.0

            for line in move.line_ids:
                if line.debit:
                    total += line.balance

            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        '''
        Invocamos el _check_unique_sequence_number para hacer by pass a restriccion del core relacionada con duplicidad
        en retenciones recibidas en ventas.
        '''
        moves = self.filtered(lambda move: move.state == 'posted')
        if not moves:
            return
        self.flush()
        #Si son retenciones en ventas analizamos el partner
        out_withhold = self.filtered(lambda move: move.l10n_ec_withhold_type == 'out_withhold')
        if out_withhold:
            # /!\ Computed stored fields are not yet inside the database.
            self._cr.execute('''
                SELECT move2.id
                FROM account_move move
                INNER JOIN account_move move2 ON
                    move2.name = move.name
                    AND move2.journal_id = move.journal_id
                    AND move2.move_type = move.move_type
                    AND move2.id != move.id
                WHERE move.id IN %s AND move2.partner_id IN %s AND move2.state = 'posted'
            ''', [tuple(moves.ids), tuple(moves.mapped('partner_id').ids)])
            res = self._cr.fetchone()
            if res:
                raise ValidationError(_('Posted journal entry must have an unique sequence number per company.'))
            return
        return super(AccountMove, self)._check_unique_sequence_number()

    _EC_WITHHOLD_TYPE = [
        ('out_withhold', 'Customer Withhold'),
        ('in_withhold', 'Supplier Withhold')
    ]

    #Columns
    l10n_ec_withhold_type = fields.Selection(
        _EC_WITHHOLD_TYPE,
        string='Withhold Type'
        )
    l10n_ec_allow_withhold = fields.Boolean(
        compute='_l10n_ec_allow_withhold',
        string='Allow Withhold', 
        tracking=True,
        help='Technical field to show/hide "ADD WITHHOLD" button'
        )
    l10n_ec_withhold_count = fields.Integer(
        compute='_compute_l10n_ec_withhold_count',
        string='Number of Withhold',
        )
    l10n_ec_withhold_line_ids = fields.One2many(
        'l10n_ec.account.withhold.line',
        'move_id',
        string='Withhold Lines',
        copy=False
        )
    l10n_ec_withhold_ids = fields.Many2many(
        'account.move',
        'account_move_invoice_withhold_rel',
        'invoice_id',
        'withhold_id',
        string='Withholds',
        copy=False,
        help='Link to withholds related to this invoice'
        )
    l10n_ec_withhold_origin_ids = fields.Many2many(
        'account.move',
        'account_move_invoice_withhold_rel',
        'withhold_id',
        'invoice_id',
        string='Invoices',
        copy=False,
        help='Link to invoices related to this withhold'
        )
    #subtotals
    l10n_ec_vat_withhold = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total IVA',  
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total IVA value of withhold'
        )
    l10n_ec_profit_withhold = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total RENTA', 
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total renta value of withhold'
        )    
    l10n_ec_total_base_vat = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total Base IVA',  
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total base IVA of withhold'
        )
    l10n_ec_total_base_profit = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total Base RENTA', 
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total base renta of withhold'
        )
    l10n_ec_total = fields.Monetary(
        string='Total Withhold', 
        compute='_compute_total_invoice_ec', 
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total value of withhold'
        )
    l10n_ec_invoice_amount_untaxed = fields.Monetary(
        string='Base Sugerida Ret. Renta',
        compute='_l10n_ec_compute_total_invoices',
        tracking=True,
        store=False, 
        readonly=True, 
        help='Base imponible sugerida (no obligatoria) para retención del Impuesto a la Renta'
        )
    l10n_ec_invoice_vat_doce_subtotal = fields.Monetary(
        string='Base Sugerida Ret. IVA', 
        compute='_l10n_ec_compute_total_invoices',
        tracking=True,
        store=False, 
        readonly=True, 
        help='Base imponible sugerida (no obligatoria) para retención del IVA'
        )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
     
    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            line.withhold_tax_ids = line.product_id.withhold_tax_ids.mapped('id')
        return super(AccountMoveLine, self)._onchange_product_id()
    
    #Columns
    withhold_tax_ids = fields.Many2many(
        'account.tax',
        'move_line_withhold_taxes_rel',
        'line_id',
        'tax_id',
        string='Withholdings',
        domain=[('type_tax_use', '=', 'purchase')],
        help='Withholding taxes applied on the base amount'
        )

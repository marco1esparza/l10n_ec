# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': 1,
    'in_invoice': -1,
    'out_refund': -1,
}

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        #Invocamos el name_search para restringir la seleccion de facturas en las lineas de retenciones
        if self.env.context.get('origin') == 'receive_withhold':
            return super(AccountMove, self)._name_search(name, args=[('id', 'in', self.env.context.get('l10n_ec_withhold_origin_ids'))], operator=operator, limit=limit, name_get_uid=name_get_uid)
        return super(AccountMove, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
                
    def post(self):
        '''
        '''
        account_move_line_obj =  self.env['account.move.line']
        res = super(AccountMove, self).post() #TODO JOSE: Al llamar a super ya nos comemos las secuencias nativas, deberíamos comernoslas una sola vez
        for invoice in self:                           
            if invoice.l10n_latam_country_code == 'EC':
                #Retenciones en ventas
                if invoice.type in ('entry') and invoice.l10n_ec_withhold_type == 'out_withhold' and invoice.l10n_latam_document_type_id.code in ['07']:
                    if invoice.l10n_ec_withhold_line_ids:
                        #Credit
                        vals = {
                            'partner_id': invoice.partner_id.id,
                            'account_id': invoice.partner_id.property_account_receivable_id.id,
                            'quantity': 1.0,
                            'price_unit': invoice.l10n_ec_total,
                            'debit': 0.0,
                            'credit': invoice.l10n_ec_total,
                            'move_id': invoice.id
                        }
                        account_move_line_obj.with_context(check_move_validity=False).create(vals)
                        for line in invoice.l10n_ec_withhold_line_ids:
                            #TODO: terminar de implementar el asiento contable
                            #Debit
                            vals = {
                                'partner_id': invoice.partner_id.id,
                                'account_id': line.account_id.id,
                                'quantity': 1.0,
                                'price_unit': line.amount,
                                'debit': line.amount,
                                'credit': 0.0,
                                'tax_line_id': line.tax_id.id,
                                'tax_base_amount': line.base,
                                'move_id': invoice.id
                            }
                            account_move_line_obj.with_context(check_move_validity=False).create(vals)
                #Retenciones en compras
                if invoice.type in ('entry') and invoice.l10n_ec_withhold_type == 'in_withhold' and invoice.l10n_latam_document_type_id.code in ['07'] and invoice.l10n_ec_printer_id.allow_electronic_document:
                    for document in invoice.edi_document_ids:
                        if document.state in ('to_send'):
                            #needed to print offline RIDE and populate request after validations
                            document._l10n_ec_set_access_key()
                            self.l10n_ec_authorization = document.l10n_ec_access_key #for auditing manual changes
                            document._l10n_ec_generate_request_xml_file()
        return res

    def get_is_edi_needed(self, edi_format):
        '''
        '''
        res = super(AccountMove, self).get_is_edi_needed(edi_format)
        if self.l10n_latam_country_code == 'EC':
            if self.type == 'entry' and self.l10n_ec_withhold_type == 'in_withhold' and self.l10n_latam_document_type_id.code in ['07'] and self.l10n_ec_printer_id.allow_electronic_document:
                return True
        return res
    
    def add_withhold(self):
        #Creates a withhold linked to selected invoices
        for invoice in self:
            if not invoice.l10n_latam_country_code == 'EC':
                raise ValidationError(u'Withhold documents are only aplicable for Ecuador')
            if not invoice.l10n_ec_allow_withhold:
                raise ValidationError(u'The selected document type does not support withholds')
            if len(self) > 1 and invoice.type != 'out_invoice':
                raise ValidationError(u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')
            if not invoice.state in ['posted']: #TODO JOSE: Moverla al flujo de validación de la retención, esta es mejor allá
                raise ValidationError(u'Solo se puede registrar retenciones sobre facturas abiertas o pagadas.')
        if len(list(set(self.mapped('commercial_partner_id')))) > 1:
            raise ValidationError(u'Las facturas seleccionadas no pertenecen al mismo cliente.')
        self = self.with_context(include_business_fields=False) #don't copy sale/purchase links
        
        default_values = self._prepare_withold_default_values()
        new_move = self.env['account.move'] #this is the new withhold
        new_move = self[0].copy(default=default_values)
        #TODO: re-implementar las sig lineas aunque va existir un account.withhold.line andres quiere
        #mantener este vinculo para compras
#         if self.type == 'in_invoice':
#             withhold_lines = self.line_ids.filtered(lambda l: l.tax_group_id.l10n_ec_type in ['withhold_vat', 'withhold_income_tax'])
#             withhold_lines.l10n_ec_withhold_out_id = new_move.id
        
        return self.action_view_withholds()
    
    def _prepare_withold_default_values(self):
        #Compras
        if self[0].type == 'in_invoice':
            type = 'entry' #'out_refund' #'out_withhold'
            #TODO ANDRES: Evaluar el metodo de l10n_latam que define el tipo de documento
            l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
                [('country_id.code', '=', 'EC'),
                 ('code', '=', '07'),
                 ('l10n_ec_type', '=', 'in_withhold'),
                 ], order="sequence asc", limit=1)
            journal_id = self.env.ref('l10n_ec_withhold.withhold_purchase').id #TODO JOSE, hacerlo en base al códio de diario, RVNTA
            default_values = {
                    #'ref': '%s, %s' % (move.name, self.reason) if self.reason else move.name,
                    'invoice_date': False,
                    'journal_id': journal_id,
                    'invoice_payment_term_id': None,
                    'type': type,
                    'line_ids': [(5, 0, 0)],
                    'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
                    'l10n_ec_invoice_payment_method_ids':  [(5, 0, 0)],
                    'l10n_ec_authorization': False,
                    'l10n_ec_withhold_origin_ids': [(6, 0, self.ids)],
                    'l10n_ec_withhold_type': 'in_withhold',
                }
        #Ventas
        if self[0].type == 'out_invoice':
            type = 'entry' #'out_refund' #'out_withhold'
            #TODO ANDRES: Evaluar el metodo de l10n_latam que define el tipo de documento
            l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
                [('country_id.code', '=', 'EC'),
                 ('code', '=', '07'),
                 ('l10n_ec_type', '=', 'out_withhold'),
                 ], order="sequence asc", limit=1)
            journal_id = self.env.ref('l10n_ec_withhold.withhold_sale').id #TODO JOSE, hacerlo en base al códio de diario, RVNTA
            default_values = {
                    #'ref': '%s, %s' % (move.name, self.reason) if self.reason else move.name,
                    'invoice_date': False,
                    'journal_id': journal_id,
                    'invoice_payment_term_id': None,
                    'type': type,
                    'line_ids': [(5, 0, 0)],
                    'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
                    'l10n_ec_invoice_payment_method_ids':  [(5, 0, 0)],
                    'l10n_ec_authorization': False,
                    'l10n_ec_withhold_origin_ids': [(6, 0, self.ids)],
                    'l10n_ec_withhold_type': 'out_withhold',
                }
            origins = []
            for invoice in self:
                origin = invoice.name #Usamos name en lugar del l10n_latam_document_number para aprovechar el prefijo del tipo de doc
                if invoice.invoice_origin:
                    origin += ';' + invoice.invoice_origin
                origins.append(origin)
            origin = ','.join(origins)
            default_values.update({
                'l10n_ec_origin': origin
            })
        return default_values
        
    def action_view_withholds(self):
        '''
        '''
        action = 'account.action_move_journal_line'
        view = 'l10n_ec_withhold.view_move_form_withhold'
        action = self.env.ref(action)
        result = action.read()[0]
        result['name'] = _('Withholds')
        l10n_ec_withhold_ids = self.l10n_ec_withhold_ids.ids
        if len(l10n_ec_withhold_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(l10n_ec_withhold_ids) + ")]"
        else:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = l10n_ec_withhold_ids and l10n_ec_withhold_ids[0] or False
        return result
            
    def check_entry_line(self):
        '''
        Bypass para validar fact sin lineas(retenciones en compras)
        '''
        if self.type in ['entry'] and self.l10n_latam_document_type_id.code in ['07']:
            return True
        return super(AccountMove, self).check_entry_line()

    def _compute_total_invoice_ec(self):
        '''
        '''
        res = super(AccountMove, self)._compute_total_invoice_ec()
        for invoice in self:
            l10n_ec_total_iva = 0.0
            l10n_ec_total_renta = 0.0
            l10n_ec_total_base_iva = 0.0
            l10n_ec_total_base_renta = 0.0
            for line in invoice.l10n_ec_withhold_line_ids:
                if line.tax_id.tax_group_id:
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat']:
                        l10n_ec_total_iva += line.amount
                        l10n_ec_total_base_iva += line.base
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                        l10n_ec_total_renta += line.amount
                        l10n_ec_total_base_renta += line.base
            invoice.l10n_ec_total_iva = l10n_ec_total_iva
            invoice.l10n_ec_total_renta = l10n_ec_total_renta
            invoice.l10n_ec_total_base_iva = l10n_ec_total_base_iva
            invoice.l10n_ec_total_base_renta = l10n_ec_total_base_renta
            invoice.l10n_ec_total = l10n_ec_total_iva + l10n_ec_total_renta
        return res
    
    def _l10n_ec_allow_withhold(self):
        #shows/hide "ADD WITHHOLD" button on invoices
        for invoice in self:
            result = False
            if invoice.l10n_latam_country_code == 'EC' and invoice.state == 'posted':
                if invoice.l10n_latam_document_type_id.code in ['01','03','18']: #TODO añadir codigos, revisar proyecto X
                    result = True
            invoice.l10n_ec_allow_withhold = result
    
    @api.depends('l10n_ec_withhold_ids')
    def _compute_l10n_ec_withhold_count(self):
        for invoice in self:
            count = len(self.l10n_ec_withhold_ids)
            invoice.l10n_ec_withhold_count = count
    
    @api.depends('l10n_ec_withhold_origin_ids.l10n_ec_base_doce_iva', 'l10n_ec_withhold_origin_ids.amount_untaxed')
    def _compute_total_invoices(self):
        '''
        Computa subtotales que dependen de la factura, estos subtotales son 
        utilizados para sugerir valores al momento de crear la retención
        '''
        for invoice in self:
            #valor de arranque
            l10n_ec_invoice_vat_doce_subtotal = l10n_ec_invoice_amount_untaxed = 0.0
            #computamos
            invoice.l10n_ec_invoice_vat_doce_subtotal = sum(inv.l10n_ec_vat_doce_subtotal * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.type] for inv in invoice.l10n_ec_withhold_origin_ids)
            invoice.l10n_ec_invoice_amount_untaxed = sum(inv.amount_untaxed * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.type] for inv in invoice.l10n_ec_withhold_origin_ids)
    
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
        method=True,  
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
    l10n_ec_total_iva = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total IVA',  
        method=True, 
        store=False, 
        readonly=True, 
        help='Total IVA value of withhold'
        )
    l10n_ec_total_renta = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total RENTA', 
        method=True, 
        store=False, 
        readonly=True, 
        help='Total renta value of withhold'
        )    
    l10n_ec_total_base_iva = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total Base IVA',  
        method=True, 
        store=False, 
        readonly=True, 
        help='Total base IVA of withhold'
        )
    l10n_ec_total_base_renta = fields.Monetary(
        compute='_compute_total_invoice_ec',
        string='Total Base RENTA', 
        method=True, 
        store=False, 
        readonly=True, 
        help='Total base renta of withhold'
        )
    l10n_ec_total = fields.Monetary(
        string='Total Withhold', 
        compute='_compute_total_invoice_ec', 
        method=True, 
        store=False, 
        readonly=True, 
        help='Total value of withhold'
        )
    l10n_ec_origin = fields.Char(
        string='Source Document',
        readonly=True,
        help='Reference of the document that produced this withhold.'
        )
    l10n_ec_invoice_amount_untaxed = fields.Monetary(
        string='Base Sugerida Ret. Renta',
        compute='_compute_total_invoices',
        method=True, 
        store=False, 
        readonly=True, 
        help='Base imponible sugerida (no obligatoria) para retención del Impuesto a la Renta'
        )
    l10n_ec_invoice_vat_doce_subtotal = fields.Monetary(
        string='Base Sugerida Ret. IVA', 
        compute='_compute_total_invoices',
        method=True, 
        store=False, 
        readonly=True, 
        help='Base imponible sugerida (no obligatoria) para retención del IVA'
        )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    #Columns
    l10n_ec_withhold_out_id = fields.Many2one(
        'account.move',
        string='Withhold'
        )

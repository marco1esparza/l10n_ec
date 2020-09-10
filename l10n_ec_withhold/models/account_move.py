# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def post(self):
        '''
        '''
        for invoice in self:
            if not invoice.company_id.vat:
                raise ValidationError(u'Please setup your VAT number in the company form')
        res = super(AccountMove, self).post() #TODO JOSE: Al llamar a super ya nos comemos las secuencias nativas, deberíamos comernoslas una sola vez
        for invoice in self:
            if invoice.l10n_latam_country_code == 'EC':
                #Retenciones en compras
                if invoice.type in ('entry') and invoice.withhold_type == 'supplier' and invoice.l10n_latam_document_type_id.code in ['07'] and invoice.l10n_ec_printer_id.allow_electronic_document:
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
            if self.type == 'entry' and self.withhold_type == 'supplier' and self.l10n_latam_document_type_id.code in ['07'] and self.l10n_ec_printer_id.allow_electronic_document:
                return True
        return res
  
    def add_withhold(self): #TODO Andres implementar un add_single_withhold para automatizmos futuros ej. tipti
        '''
        Crea una retencion asociada a todas las facturas relacionadas
        '''
        if self.type in ['out_invoice', 'in_invoice']:
            #Compras
            #A las lineas de la factura original(relacionadas con retenciones) le seteamos el campo 
            #l10n_ec_withhold_out_id
            #TODO: ajustar la parte de compras
            if self.type == 'in_invoice':
                #Duplicamos solo la cabecera de la factura(va hacer funcion de cabecera de retencion), nada de lineas
                l10n_latam_document_type_id = self.env.ref('l10n_ec.ec_11').id
                journal_id = self.env.ref('l10n_ec_withhold.withhold_purchase').id
                withhold = self.copy(default={'l10n_latam_document_type_id': l10n_latam_document_type_id,
                                              'journal_id': journal_id,
                                              'invoice_line_ids': [], 
                                              'line_ids': [], 
                                              'l10n_ec_withhold_line_ids': [], 
                                              'type':'entry',
                                              'withhold_type': 'supplier'})
                withhold_lines = self.line_ids.filtered(lambda l: l.tax_group_id.l10n_ec_type in ['withhold_vat', 'withhold_income_tax'])
                withhold_lines.l10n_ec_withhold_out_id = withhold.id
            #Ventas
            elif self.type == 'out_invoice':
                #Duplicamos solo la cabecera de la factura(va hacer funcion de cabecera de retencion), nada de lineas
                l10n_latam_document_type_id = self.env.ref('l10n_ec.ec_03').id
                journal_id = self.env.ref('l10n_ec_withhold.withhold_sale').id
                withhold = self.copy(default={'l10n_latam_document_type_id': l10n_latam_document_type_id,
                                              'journal_id': journal_id,
                                              'invoice_line_ids': [], 
                                              'line_ids': [], 
                                              'l10n_ec_withhold_line_ids': [],
                                              'l10n_ec_invoice_payment_method_ids': [],
                                              'l10n_ec_authorization': False,
                                              'type':'entry',
                                              'withhold_type': 'customer'})
                withhold.l10n_ec_invoice_ids = [(6, 0, self.ids)]
            return self.view_withhold()
  
    def view_withhold(self):
        '''
        '''
        [action] = self.env.ref('account.action_move_journal_line').read()
        action['domain'] = [('id', 'in', self.get_withhold_ids())]            
        return action
 
    def _withhold_exist(self):
        '''
        Este método determina si la factura tiene al menos una retencion asociada
        '''
        for invoice in self:
            withhold_exist =  False
            if len(self.get_withhold_ids()) >= 1:
                withhold_exist = True
            invoice.l10n_ec_withhold_exist = withhold_exist
            
    def get_withhold_ids(self):
        '''
        '''
        withhold_ids = []
        self.env.cr.execute('''select withhold_id from account_move_invoice_withhold_rel where invoice_id=%s''', (self.id,))
        records = self.env.cr.dictfetchall()
        for record in records:
            withhold_ids.append(record.get('withhold_id'))
        return withhold_ids
            
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
            for move_line in invoice.line_ids:
                if move_line.tax_group_id:
                    if move_line.tax_group_id.l10n_ec_type in ['withhold_vat']:
                        l10n_ec_total_iva += move_line.credit
                        l10n_ec_total_base_iva += move_line.tax_base_amount
                    if move_line.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                        l10n_ec_total_renta += move_line.credit
                        l10n_ec_total_base_renta += move_line.tax_base_amount
            invoice.l10n_ec_total_iva = l10n_ec_total_iva
            invoice.l10n_ec_total_renta = l10n_ec_total_renta
            invoice.l10n_ec_total_base_iva = l10n_ec_total_base_iva
            invoice.l10n_ec_total_base_renta = l10n_ec_total_base_renta
        return res
    
    _WITHHOLD_TYPE = [
        ('customer', 'Customer'),
        ('supplier', 'Supplier')
    ]
    
    #Columns
    withhold_type = fields.Selection(
        _WITHHOLD_TYPE,
        string='Withhold type'
        )
    l10n_latam_document_type_code = fields.Char(
        string='Document Code (LATAM)',
        related='l10n_latam_document_type_id.code', 
        help='Technical field used to hide/show fields regarding the localization'
        )
    l10n_ec_withhold_line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Withhold lines',
        copy=False
        )
    l10n_ec_withhold_exist = fields.Boolean(
        compute='_withhold_exist',
        string='Withhold Exist',
        method=True, 
        store=False,
        help='Show internally if a withhold asociated exist'
        )
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
    l10n_ec_invoice_ids = fields.Many2many(
        'account.move',
        'account_move_invoice_withhold_rel',
        'withhold_id',
        'invoice_id',
        string='Withhold'
        )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    #Columns
    l10n_ec_withhold_out_id = fields.Many2one(
        'account.move',
        string='Withhold'
        )
    l10n_ec_withhold_invoice_id = fields.Many2one(
        'account.move',
        string='Invoice'
        )

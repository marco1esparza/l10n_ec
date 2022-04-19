# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        #only shows previously selected invoices in the withhold wizard lines
        if self.env.context.get('origin') == 'receive_withhold':
            return super(AccountMove, self)._name_search(name, args=[('id', 'in', self.env.context.get('l10n_ec_withhold_origin_ids'))], operator=operator, limit=limit, name_get_uid=name_get_uid)
        return super(AccountMove, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        
    def copy_data(self, default=None):
        #avoid duplicating withholds, it has not been tested
        res = super(AccountMove, self).copy_data(default=default)
        if self.is_withholding():
            raise ValidationError(u'You can not duplicate a withhold, instead create a new one from the invoice.')
        return res
    
    #TODO V15.2 Revisar si se incorpora en el l10n_ec_edi
    @api.depends('journal_id', 'partner_id', 'company_id', 'move_type')
    def _compute_l10n_latam_available_document_types(self):
        #Para EC el computo del tipo de documento no depende del partner, se rescribe en ese sentido
        #esto permite tener un tipo de documento por defecto al crear facturas, y facilita el ignreso
        #del numero de autorización
        self.l10n_latam_available_document_type_ids = False
        for rec in self.filtered(lambda x: x.journal_id and x.l10n_latam_use_documents): #en esta linea se borro el filtro de partner_id
            rec.l10n_latam_available_document_type_ids = self.env['l10n_latam.document.type'].search(rec._get_l10n_latam_documents_domain())
            #TODO V15, hacer que para el consumidor final se excluyan los documentos que no puede manejar

    #TODO V15.2 Revisar si se incorpora en el l10n_latam
    @api.depends('l10n_latam_available_document_type_ids')
    @api.depends_context('internal_type')
    def _compute_l10n_latam_document_type(self):
        #Reescribimos el metodo original de l10n_latam_document_type, pues reescribia el tipo de documento
        #cada vez q se cambiaba el partner, cuando debería reescribirlo solo si el tipo de documento
        #viejo no forma parte del nuevo l10n_latam_available_document_type_ids
        internal_type = self._context.get('internal_type', False)
        for rec in self.filtered(lambda x: x.state == 'draft'):
            document_types = rec.l10n_latam_available_document_type_ids._origin
            document_types = internal_type and document_types.filtered(lambda x: x.internal_type == internal_type) or document_types
            #linea agregada por trescloud:
            if rec.l10n_latam_document_type_id not in document_types:
                rec.l10n_latam_document_type_id = document_types and document_types[0].id
    
    #TODO Reimplement for v15.1
    # def _post(self, soft=True):
    #     '''
    #     Invocamos el metodo post para generar los asientos de retenciones de forma manual y conciliar
    #     los asientos de retenciones en ventas con la factura
    #     '''
    #     posted = super()._post(soft=soft)
    #     for withhold in self:
    #         if withhold.country_code == 'EC':
    #             if withhold.l10n_ec_withhold_type in ['out_withhold']:
    #                 (withhold + withhold.l10n_ec_withhold_origin_ids).line_ids.filtered(lambda line: not line.reconciled and line.account_id == withhold.partner_id.property_account_receivable_id).reconcile()
    #             elif withhold.l10n_ec_withhold_type in ['in_withhold']:
    #                 (withhold + withhold.l10n_ec_withhold_origin_ids).line_ids.filtered(lambda line: not line.reconciled and line.account_id == withhold.partner_id.property_account_payable_id).reconcile()
    #     return posted 

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
        #For now the wizard for withhold lines can be called only from the invoices... it is imposible to edit!
        res = super(AccountMove, self).button_draft()
        for move in self:
            if move.country_code == 'EC':
                if move.l10n_ec_withhold_type == 'in_withhold':
                    raise ValidationError(_("Can not send to draft an issued withhold, instead issue a new one"))
        return res
    
    def l10n_ec_validate_withhold_data_on_post(self):
        partner_id = partner_id or self.partner_id
        if invoices and partner_id.commercial_partner_id != invoices[0].commercial_partner_id:
           raise ValidationError(u'La empresa indicada en la retención no corresponde a la de las facturas.')
        #Validamos que para cada factura exista maximo una retención de IVA y una de renta
        #en todas las lineas de retención de todas las retenciónes asociadas a todas las facturas
        categories = self.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.l10n_ec_withhold_line_ids.tax_id.tax_group_id.mapped('l10n_ec_type')
        categories = list(set(categories)) #remueve duplicados
        for withhold_line in self.l10n_ec_withhold_origin_ids.l10n_ec_withhold_ids.l10n_ec_withhold_line_ids:
            if withhold_line.move_id.state in ('posted') and withhold_line.move_id != self:
                if withhold_line.tax_line_id.tax_group_id.l10n_ec_type in categories:
                    if withhold_line.tax_line_id.tax_group_id.l10n_ec_type == 'withhold_vat':
                        withhold_category = u'Retención IVA'
                    elif withhold_line.tax_line_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
                        withhold_category = u'Retención Renta'
                    error_msg = u'Una factura no puede tener dos retenciones por el mismo concepto.\n' + \
                                u'La retención previamente existente ' + withhold_line.move_id.name + \
                                u' tiene tambien una retención por ' + withhold_category + u'.'  
                    raise ValidationError(error_msg)
                
                
                
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
                error += u'La cantidad a retener es mayor que el valor de las facturas.\n'
        if error:
            raise ValidationError(error)



    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        # It allows generating zero entries when the tax amount is zero, needed to keep base amount in 0% withholdings
        #TODO V15.1 hacer el metodo solo para ecuador
        #TODO V15.2 luego de la fusión con Odoo evaluar moverlo al l10n_ec
        return super(AccountMove, self.with_context(generate_zero_entry=True))._recompute_tax_lines(recompute_tax_base_amount)
    
    def l10n_ec_add_withhold(self):
        #Launches the withholds wizard linked to selected invoices        
        view = self.env.ref('l10n_ec_withhold.wizard_account_withhold_form')
        return {
            'name': u'Withholding',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id or False,
            'res_model': 'l10n_ec.wizard.account.withhold',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new'
        }

    # #TODO V15.2 Posiblemente remover el metodo pues el wizard ya tiene algo parecido... pero talvez se necesite
    # @api.depends('move_type')
    # def _compute_invoice_filter_type_domain(self):
    #     '''
    #     Metodo para obtener solo diarios generales en Retenciones.
    #     '''
    #     for move in self:
    #         super(AccountMove, move)._compute_invoice_filter_type_domain()
    #         if move.l10n_ec_withhold_type and move.l10n_ec_withhold_type in ('in_withhold'):
    #             move.invoice_filter_type_domain = 'general'
    # 
    # #TODO V15.2 Posiblemente remover el metodo pues el wizard ya tiene algo parecido... pero talvez se necesite
    # def _get_l10n_latam_documents_domain(self):
    #     #Filter document types according to ecuadorian type
    #     
    #     domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
    #     if self.l10n_ec_withhold_type:
    #         domain.extend([('l10n_ec_type', '=', self.l10n_ec_withhold_type)])
    #     return domain
        
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

    @api.depends('l10n_ec_withhold_line_ids')
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
                if line.tax_line_id.tax_group_id:
                    if line.tax_line_id.tax_group_id.l10n_ec_type in ['withhold_vat']:
                        l10n_ec_vat_withhold += line.credit
                        l10n_ec_total_base_vat += line.base
                    if line.tax_line_id.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                        l10n_ec_profit_withhold += line.credit
                        l10n_ec_total_base_profit += line.tax_base_amount
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
                if invoice.l10n_latam_document_type_id.code in ['01','02','03','18']:
                    result = True
            invoice.l10n_ec_allow_withhold = result
    
    @api.depends('l10n_ec_withhold_ids')
    def _compute_l10n_ec_withhold_count(self):
        for invoice in self:
            count = len(self.l10n_ec_withhold_ids)
            invoice.l10n_ec_withhold_count = count
    
    #TODO: REIMPLEMENT FOR V15.1, llevandonos al valor por defecto para retenciones
    @api.depends()
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
        #TODO V15.2 Discuss with Odoo, the method can be simplified but in this way is more "secure"
        is_withholding = False
        if self.country_code == 'EC' and self.move_type in ('entry') \
           and self.l10n_ec_withhold_type and self.l10n_ec_withhold_type in ('in_withhold', 'out_withhold') \
           and self.l10n_latam_document_type_id.code in ['07']:
            is_withholding = True
        return is_withholding

    # @api.depends(
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
    #     'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
    #     'line_ids.debit',
    #     'line_ids.credit',
    #     'line_ids.currency_id',
    #     'line_ids.amount_currency',
    #     'line_ids.amount_residual',
    #     'line_ids.amount_residual_currency',
    #     'line_ids.payment_id.state',
    #     'line_ids.full_reconcile_id')
    # def _compute_amount(self):
    #     '''
    #     Se computa para retenciones de ventas, para poder obtener el total registrado en lal vista lista.
    #     '''
    #     super()._compute_amount()
    #     for move in self.filtered(lambda x: x.is_withholding() and x.l10n_ec_withhold_type == 'out_withhold'):
    #         total = 0.0
    #         for line in move.line_ids:
    #             if line.debit:
    #                 total += line.balance
    #         move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total

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
    
    @api.depends('l10n_latam_document_type_id')
    def _l10n_ec_compute_require_vat_tax(self):
        #Indicates if the invoice requires a vat tax or not
        for move in self:
            result = False
            if move.country_code == 'EC':
        #TODO agregar regiment especial en un AND al siguiente if
                if move.move_type in ['in_invoice', 'in_refund', 'out_invoice', 'out_refund']:
                    if move.l10n_latam_document_type_id.code in [
                                        '01', # factura compra
                                        '02', # nota de venta
                                        '03', # liquidacion compra
                                        '04', # Notas de credito en compras o ventas
                                        '05', # Notas de debito en compras o ventas
                                        '08', # Boletos espectaculos publicos
                                        '09', # Tiquetes
                                        '11', # Pasajes
                                        '12', # Inst FInancieras
                                        '16', # DAU, acordamos poner IVA en los rubros fodinfa, etc, para que sea fácil
                                        '18', # Factura de venta
                                        '20', # Estado
                                        '21', # Carta porte aereo
                                        '41', # Reembolsos de gastos compras y ventas, liquidaciones, facturas
                                        '47', # Nota de crédito de reembolso
                                        '48', # Nota de débito de reembolso
                                        ]:
                        result = True
            move.l10n_ec_require_vat_tax = result
            
    @api.depends('l10n_latam_document_type_id','l10n_ec_sri_tax_support_id')
    def _l10n_ec_compute_require_withhold_tax(self):
        #Indicates if the invoice requires a withhold or not
        for move in self:
            result = False
            if move.country_code == 'EC':
                #TODO agregar regiment especial en un AND al siguiente if
                if move.move_type == 'in_invoice' and move.company_id.l10n_ec_issue_withholds:
                    if move.l10n_latam_document_type_id.code in [
                                        '01', # factura compra
                                        '02', # Nota de venta
                                        '03', # liquidacion compra
                                        '08', # Entradas a espectaculos
                                        '09', # Tiquetes
                                        '11', # Pasajes
                                        '12', # Inst FInancieras
                                        '20', # Estado
                                        '21', # Carta porte aereo
                                        #'41', # Reembolso de gastos como cliente final, no requiere retención
                                        '47', # Nota de crédito de reembolso
                                        '48', # Nota de débito de reembolso
                                        ]:
                        #if move.l10n_ec_sri_tax_support_id.code not in ['08']: #compras por reembolso como intermediario
                        result = True
            move.l10n_ec_require_withhold_tax = result

    @api.depends('line_ids')
    def _compute_l10n_ec_withhold_line_ids(self):
        for withhold in self:
            withhold.l10n_ec_withhold_line_ids = withhold.line_ids.filtered(lambda l: l.credit > 0.0)

    _EC_WITHHOLD_TYPE = [
        ('out_withhold', 'Customer Withhold'),
        ('in_withhold', 'Supplier Withhold')
    ]
    
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
        'account.move.line',
        string='Withhold Lines',
        compute='_compute_l10n_ec_withhold_line_ids',
        readonly=True
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
        help='Technical field to limit elegible invoices related to this withhold'
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
    l10n_ec_require_withhold_tax = fields.Boolean(
        compute='_l10n_ec_compute_require_withhold_tax'
        )
    l10n_ec_require_vat_tax = fields.Boolean(
        compute='_l10n_ec_compute_require_vat_tax'
        )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
                 
    def _l10n_ec_get_computed_taxes(self):
        '''
        For purchases adds prevalence for tax mapping to ease withholds in Ecuador, in the following order:
        For profit withholding tax:
        - If payment type == credit card then withhold code 332G, if not then
        - partner_id.l10n_ec_force_profit_withhold, if not set then
        - product_id profit withhold, if not set then
        - company fallback profit withhold for goods or for services
        For vat withhold tax:
        - If product is consumable then l10n_ec_vat_withhold_goods
        - If product is services or not set then l10n_ec_vat_withhold_services
        If withholds doesn't apply to the document type then remove the withholds  
        '''
        super_tax_ids = self.env['account.tax']
        vat_withhold_tax = False
        profit_withhold_tax = False
        if self.move_id.country_code == 'EC':
            if self.move_id.is_purchase_document(include_receipts=True):
                if not self.exclude_from_invoice_tab: #just regular invoice lines
                    if self.move_id.l10n_ec_require_withhold_tax: #compute withholds
                        company_id = self.move_id.company_id
                        contributor_type = self.partner_id.contributor_type_id
                        tax_groups = super_tax_ids.mapped('tax_group_id').mapped('l10n_ec_type') 
                        #compute vat withhold
                        if 'vat12' in tax_groups or 'vat14' in tax_groups:
                            if not self.product_id or self.product_id.type in ['consu','product']:
                                vat_withhold_tax = contributor_type.l10n_ec_vat_withhold_goods
                            else: #services
                                vat_withhold_tax = contributor_type.l10n_ec_vat_withhold_services                         
                        #compute profit withhold
                        if self.move_id.l10n_ec_payment_method_id.code in ['16','18','19']:
                            #payment with debit card, credit card or gift card retains 0%
                            profit_withhold_tax = company_id.l10n_ec_profit_withhold_tax_credit_card
                        elif contributor_type.property_l10n_ec_profit_withhold_tax_id:
                            profit_withhold_tax = contributor_type.property_l10n_ec_profit_withhold_tax_id
                        elif self.product_id.withhold_tax_id:
                            profit_withhold_tax = self.product_id.withhold_tax_id
                        elif 'withhold_income_tax' in tax_groups:
                            pass #keep the taxes coming from product.product... for now
                        else: #if not any withhold tax then fallback
                            if self.product_id and self.product_id.type == 'service':
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_services
                            else:
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_goods
                    else: #remove withholds
                        super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat', 'withhold_income_tax'])
            if vat_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat'])
                super_tax_ids += vat_withhold_tax
            if profit_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_income_tax'])
                super_tax_ids += profit_withhold_tax
        return super_tax_ids

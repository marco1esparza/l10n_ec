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
        if self.env.context.get('l10n_ec_related_invoices_ctx'):
            return super(AccountMove, self)._name_search(name, args=[('id', 'in', self.env.context.get('l10n_ec_related_invoices_ctx'))], operator=operator, limit=limit, name_get_uid=name_get_uid)
        return super(AccountMove, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        
    def copy_data(self, default=None):
        #avoid duplicating withholds, duplication has not been tested
        res = super(AccountMove, self).copy_data(default=default)
        if self.is_withholding():
            raise ValidationError(u'You can not duplicate a withhold, instead create a new one from the invoice.')
        return res
    
    #TODO: V15.2 Revisar con el equipo de Odoo, si a la retenciones les hacemos el is_invoice = True ya no se necesitaria este codigo
    # def button_cancel_posted_moves(self):
    #     # Verificamos si es una retencion y se puede ejecutar REQUEST EDI CANCELLATION
    #     res = super().button_cancel_posted_moves()
    #     to_cancel_documents = self.env['account.edi.document']
    #     for move in self:
    #         is_move_marked = False
    #         for doc in move.edi_document_ids:
    #             if doc.edi_format_id._needs_web_services() \
    #                     and doc.attachment_id \
    #                     and doc.state == 'sent' \
    #                     and move.is_withholding():
    #                 to_cancel_documents |= doc
    #                 is_move_marked = True
    #         if is_move_marked:
    #             move.message_post(body=_("A cancellation of the EDI has been requested."))
    #     to_cancel_documents.write({'state': 'to_cancel', 'error': False})
    #     return res
    # 
    # @api.depends(
    #     'state',
    #     'edi_document_ids.state',
    #     'edi_document_ids.attachment_id')
    # def _compute_edi_show_cancel_button(self):
    #     # Validacion de mostrar el REQUEST EDI CANCELATION a las retenciones
    #     for move in self:
    #         super(AccountMove, move)._compute_edi_show_cancel_button()
    #         if move.is_withholding():
    #             move.edi_show_cancel_button = any([doc.edi_format_id._needs_web_services()
    #                                                and doc.attachment_id
    #                                                and doc.state == 'sent'
    #                                                and move.is_withholding()
    #                                                for doc in move.edi_document_ids])

    # TODO V15.2 ya no se requiere pues al tener un documento EDI el modulo account_edi impide que se cambie a borrador
    # def button_draft(self):
    #     #For now the wizard for withhold lines can be called only from the invoices... it is imposible to edit!
    #     res = super(AccountMove, self).button_draft()
    #     for move in self:
    #         if move.country_code == 'EC':
    #             if move.l10n_ec_withhold_type == 'in_withhold':
    #                 raise ValidationError(_("Can not send to draft an issued withhold, instead issue a new one"))
    #     return res
    
    @api.model
    def _l10n_ec_withhold_validate_related_invoices(self, invoices):
        # Let's test the source invoices for missuse
        MAP_INVOICE_TYPE_PARTNER_TYPE = {
            'out_invoice': 'customer',
            'out_refund': 'customer',
            'in_invoice': 'supplier',
            'in_refund': 'supplier',
        }
        for invoice in invoices:
            if not invoice.l10n_ec_allow_withhold:
                raise ValidationError(u'The selected document type does not support withholds, please check the document "%s".' % invoice.name) 
            if invoice.state not in ['posted']:
                raise ValidationError(u'Can not create a withhold, the document "%s" not yet posted.' % invoice.name)
            if invoice.commercial_partner_id != invoices[0].commercial_partner_id: #and not self.env.context.get('massive_withhold'):
                raise ValidationError(u'Some documents belong to different partners, please correct the document "%s".' % invoice.name)
            if MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type]:
                raise ValidationError(u'Can not mix documents supplier and customer documents in the same withhold, please correct the document "%s".' % invoice.name)
            if invoice.currency_id != invoice.company_id.currency_id:
                raise ValidationError(u'A fin de emitir retenciones sobre múltiples facturas, deben tener la misma moneda, revise la factura "%s".' % invoice.name)    
            if len(self) > 1 and invoice.move_type != 'out_invoice':
                raise ValidationError(u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')

    def l10n_ec_add_withhold(self):
        #Launches the withholds wizard linked to selected invoices
        self._l10n_ec_withhold_validate_related_invoices(invoices=self)
        view = self.env.ref('l10n_ec_withhold.wizard_account_withhold_form')
        return {
            'name': u'Withholding',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id or False,
            'res_model': 'l10n_ec.wizard.account.withhold',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': self.env.context
        }

    # #TODO V15.2 Posiblemente remover el metodo pues el wizard ya tiene algo parecido... pero talvez se necesite para edicion posterior de la retencion
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
    # #TODO V15.2 Posiblemente remover el metodo pues el wizard ya tiene algo parecido... pero talvez se necesite para edicion posterior de la retencion
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
        l10n_ec_withhold_ids = self.l10n_ec_withhold_ids.ids or self.env.context.get('withhold', [])
        if len(l10n_ec_withhold_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(l10n_ec_withhold_ids) + ")]"
        else:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = l10n_ec_withhold_ids and l10n_ec_withhold_ids[0] or False
        return result

    @api.depends('l10n_ec_withhold_line_ids')
    def _l10n_ec_compute_move_totals(self):
        '''
        '''
        res = super(AccountMove, self)._l10n_ec_compute_move_totals()
        for invoice in self:
            l10n_ec_vat_withhold = 0.0
            l10n_ec_profit_withhold = 0.0
            l10n_ec_total_base_vat = 0.0
            l10n_ec_total_base_profit = 0.0
            for line in invoice.l10n_ec_withhold_line_ids:
                if line.tax_line_id.tax_group_id:
                    if line.tax_line_id.tax_group_id.l10n_ec_type in ['withhold_vat']:
                        l10n_ec_vat_withhold += line.credit if invoice.l10n_ec_withhold_type == 'in_withhold' else line.debit 
                        l10n_ec_total_base_vat += line.tax_base_amount
                    if line.tax_line_id.tax_group_id.l10n_ec_type in ['withhold_income_tax']:
                        l10n_ec_profit_withhold += line.credit if invoice.l10n_ec_withhold_type == 'in_withhold' else line.debit
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

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.is_withholding():
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

    # TODO: V15.2 este calculo debiera de ser incluido... aunque podría funcionar si está marcado como is_invoice?
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
    
    #TODO 15.3 suggest Odoo to have something like this + bypass
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
    def _compute_l10n_ec_withhold_ids(self):
        for move in self:
            move.l10n_ec_withhold_line_ids = move.line_ids.filtered(lambda l: l.tax_line_id)
            move.l10n_ec_withhold_ids = self.env['account.move.line'].search([('l10n_ec_withhold_invoice_id', '=', move.id)]).mapped('move_id')
            move.l10n_ec_withhold_origin_ids = move.line_ids.mapped('l10n_ec_withhold_invoice_id')
            move.l10n_ec_withhold_count = len(move.l10n_ec_withhold_ids)

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
    l10n_ec_withhold_line_ids = fields.One2many(
        'account.move.line',
        string='Withhold Lines',
        compute='_compute_l10n_ec_withhold_ids',
        readonly=True
        )
    l10n_ec_withhold_ids = fields.Many2many(
        'account.move',
        compute='_compute_l10n_ec_withhold_ids',
        string='Withholds',
        help='Link to withholds related to this invoice'
        )
    l10n_ec_withhold_origin_ids = fields.Many2many(
        'account.move',
        compute='_compute_l10n_ec_withhold_ids',
        string='Invoices',
        copy=False,
        help='Technical field to limit elegible invoices related to this withhold'
        )
    l10n_ec_withhold_count = fields.Integer(
        compute='_compute_l10n_ec_withhold_ids',
        string='Number of Withhold',
        )
    #subtotals
    l10n_ec_vat_withhold = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total IVA',  
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total IVA value of withhold'
        )
    l10n_ec_profit_withhold = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total RENTA', 
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total renta value of withhold'
        )    
    l10n_ec_total_base_vat = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total Base IVA',  
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total base IVA of withhold'
        )
    l10n_ec_total_base_profit = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total Base RENTA', 
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total base renta of withhold'
        )
    l10n_ec_total = fields.Monetary(
        string='Total Withhold', 
        compute='_l10n_ec_compute_move_totals', 
        tracking=True,
        store=False, 
        readonly=True, 
        help='Total value of withhold'
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
        - If product is consumable then vat_goods_withhold_tax_id
        - If product is services or not set then vat_services_withhold_tax_id
        If withholds doesn't apply to the document type then remove the withholds  
        '''
        if self.move_id.country_code == 'EC':
            super_tax_ids = self.env['account.tax']
            vat_withhold_tax = False
            profit_withhold_tax = False
            if self.move_id.is_purchase_document(include_receipts=True):
                if not self.exclude_from_invoice_tab: #just regular invoice lines
                    if self.move_id.l10n_ec_require_withhold_tax: #compute withholds
                        company_id = self.move_id.company_id
                        contributor_type = self.partner_id.contributor_type_id
                        tax_groups = super_tax_ids.mapped('tax_group_id').mapped('l10n_ec_type') 
                        #compute vat withhold
                        if 'vat12' in tax_groups or 'vat14' in tax_groups:
                            if not self.product_id or self.product_id.type in ['consu','product']:
                                vat_withhold_tax = contributor_type.vat_goods_withhold_tax_id
                            else: #services
                                vat_withhold_tax = contributor_type.vat_services_withhold_tax_id                         
                        #compute profit withhold
                        if self.move_id.l10n_ec_payment_method_id.code in ['16','18','19']:
                            #payment with debit card, credit card or gift card retains 0%
                            profit_withhold_tax = company_id.l10n_ec_profit_withhold_tax_credit_card
                        elif contributor_type.profit_withhold_tax_id:
                            profit_withhold_tax = contributor_type.profit_withhold_tax_id
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
    
    l10n_ec_withhold_invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='restrict',
        help='Link the withholding entry lines to the invoice'
        )

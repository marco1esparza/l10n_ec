# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare


class AccountMove(models.Model):
    _inherit='account.move'


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        # OVERRIDE to also recompute withhold taxes
        res = super(AccountMove, self)._onchange_partner_id()
        self._l10n_ec_onchange_tax_dependecies()
        return res
    
    @api.onchange("fiscal_position_id","l10n_latam_document_type_id",
                  "l10n_ec_fiscal","l10n_ec_payment_method_id")
    def _l10n_ec_onchange_tax_dependecies(self):
        #triger recompute of profit withhold for purchase invoice
        #TODO v15: Recompute separately profit withhold and vat withhold
        self.ensure_one()
        res = {}
        if not self.country_code == 'EC':
            return res
        if not self.state == 'draft':
            return res
        if not self.move_type == 'in_invoice':
            return res
        for line in self.invoice_line_ids:
            taxes = line._get_computed_taxes()
            #line.tax_ids = [(6, 0, taxes.ids)]
            line.tax_ids = taxes
        return res
        
    def button_draft(self):
        #Execute ecuadorian validations with bypass option
        for document in self:
            if self.country_code == 'EC':
                bypass = document.l10n_ec_bypass_validations
                if not bypass:
                    document._l10n_ec_validations_to_draft()
                    document._l10n_ec_validations_to_draft_when_edi()
            #hack: send the context to later bypass account_edi restrictions
            res = super(AccountMove, document.with_context(l10n_ec_bypass_validations=bypass)).button_draft()
            document.l10n_ec_bypass_validations = False #Reset bypass to default value
        return res
    
    @api.depends('state','edi_document_ids.state','edi_document_ids.attachment_id')
    def _compute_edi_show_cancel_button(self):
        #hack to bypass account_edi restrictions and be able to cancel the document, only inside the cancellation flow
        bypass = self._context.get('l10n_ec_bypass_validations',False)
        if bypass:
            self.edi_show_cancel_button = False
        else:
            return super()._compute_edi_show_cancel_button()
        
    def _l10n_ec_validations_to_draft(self):
        #Validaciones para cuando se mueve un asiento a draft o a cancel
        self.ensure_one()
        #avoid setting state to draft to invoices with withholds
        if self.l10n_ec_withhold_ids.filtered(lambda x: x.state not in ('cancel')):
            raise ValidationError(u'No se debería anular un factura que ya tiene retención'
                                  u' asociada, primero debe eliminar la retención. '
                                  u'Alternativamente puede pedir a su contador que active la '
                                  u'opción "Bypass Validaciones" en la pestaña "Otra '
                                  u'información"')
    
    def _l10n_ec_validations_to_draft_when_edi(self):
        #FIX, because account_edi module of v13 allows to set to draft posted invoices not yet received by SRI
        #TODO V14: Validar si todavía hace falta
        if self.edi_document_ids:
            raise UserError(_(
                "You can't set to draft the journal entry %s because an electronic document has already been requested. "
                "Instead you can cancel this document (Request EDI Cancellation button) and then create a new one"
            ) % self.display_name)
    
    def _post(self, soft=True):
        #Execute ecuadorian validations with bypass option
        for document in self:
            if document.country_code == 'EC':
                bypass = document.l10n_ec_bypass_validations
                if not bypass:
                    document._l10n_ec_validations_to_posted()
        #hack: send the context to later bypass account_edi restrictions
        # Se modifica la ejecucion del post al final porque res se debe devolver con la ejecucion de todos los documentos
        res = super(AccountMove, self)._post(soft)
        self.l10n_ec_bypass_validations = False #Reset bypass to default value
        return res
    
    def _l10n_ec_validations_to_posted(self):
        #Execute extra validations for Ecuador when posting the move
        if self.l10n_latam_document_type_id.l10n_ec_require_vat:
            #Require partner's VAT type and ID
            if not self.partner_id.vat:
                raise UserError(_("Please set a VAT number in the partner for document %s") % self.display_name)
            #TODO V14 implemnetar validacion del tipo de documento, debe estar seteado con una opción válida        
        #validations per invoice line
        l10n_ec_require_withhold_tax = self.l10n_ec_require_withhold_tax
        l10n_ec_require_vat_tax = self.l10n_ec_require_vat_tax
        for line in self.invoice_line_ids:
            #TODO V16, medir performance, podria optimizarse para no iterar todas las lineas... SQL?
            vat_taxes = self.env['account.tax'] #empty recordset
            profit_withhold_taxes = self.env['account.tax'] #empty recordset
            vat_withhold_taxes = self.env['account.tax'] #empty recordset
            for tax in line.tax_ids:
                if tax.l10n_ec_type in ['vat12','vat14','zero_vat','not_charged_vat','exempt_vat']:
                    vat_taxes += tax
                elif tax.l10n_ec_type in ['withhold_income_tax']:
                    profit_withhold_taxes += tax
                elif tax.l10n_ec_type in ['withhold_vat']:
                    vat_withhold_taxes += tax #not yet implemented
                else:
                    pass #do nothin
            #check one tax type per line
            if l10n_ec_require_vat_tax:
                if len(vat_taxes) != 1:
                    raise UserError(_("Please select one and only one vat type (IVA 12, IVA 0, etc) for product:\n\n%s") % line.name)
            if l10n_ec_require_withhold_tax:
                if len(profit_withhold_taxes) != 1:
                    raise UserError(_("Please select one and only one profit withhold type (312, 332, 322, etc) for product:\n\n%s") % line.name)
    
    @api.depends('l10n_latam_document_type_id')
    def _l10n_ec_compute_require_vat_tax(self):
        #Indicates if the invoice requires a vat tax or not
        for move in self:
            result = False
            if move.country_code == 'EC':
                if move.move_type in ['in_invoice', 'in_refund', 'out_invoice', 'out_refund'] and move.company_id.l10n_ec_issue_withholds:
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
                                        '18', # Factura de venta
                                        '20', # Estado
                                        '21', # Carta porte aereo
                                        '41', # Reembolsos de gastos compras y ventas, liquidaciones, facturas
                                        '47', # Nota de crédito de reembolso
                                        '48', # Nota de débito de reembolso
                                        ]:
                        result = True
            move.l10n_ec_require_vat_tax = result
            
    @api.depends('l10n_latam_document_type_id')
    def _l10n_ec_compute_require_withhold_tax(self):
        #Indicates if the invoice requires a withhold or not
        for move in self:
            result = False
            if move.country_code == 'EC':
                if move.move_type == 'in_invoice' and move.company_id.l10n_ec_issue_withholds:
                    if move.l10n_latam_document_type_id.code in [
                                        '01', # factura compra
                                        '03', # liquidacion compra
                                        '08', # Entradas a espectaculos
                                        '09', # Tiquetes
                                        '11', # Pasajes
                                        '12', # Inst FInancieras
                                        '20', # Estado
                                        '21', # Carta porte aereo
                                        '41', # Reembolsos de gastos compras y ventas, liquidaciones, facturas
                                        '47', # Nota de crédito de reembolso
                                        '48', # Nota de débito de reembolso
                                        ]:
                        result = True
            move.l10n_ec_require_withhold_tax = result

    
    def _validate_require_withhold(self):
        '''
        Bypass las retenciones tarjetas de Credito
        '''
        validate = True
        credit_card = self.env.user.company_id.default_profit_withhold_tax_corporate_credit_card
        if self.tax_line_ids.mapped('tax_id').filtered(lambda x : x.type_ec in ['withhold_vat','withhold_income_tax'] and
                                                              x.id == credit_card.id):
            validate = False
        return self.document_invoice_type_id.to_require_withhold and validate
    
    @api.onchange('l10n_ec_bypass_validations')
    def _onchange_l10n_ec_bypass_validations(self):
        if self.l10n_ec_bypass_validations == True:
            return {
                'warning': {'title': _('Warning'), 'message': _('Only activate bypass if you know what you are doing, it can break system integrity'),},
                 }

    #TODO AP:
    def _l10n_ec_warn_missing_withhold(self):
        '''
        Rehacer por completo el método (el texto es de la v10), para que:
        - En el post de la factura que tenga retención (campo l10n_ec_require_withhold_tax = True) crear un msg
          de alerta en la barra superior, que indique que "está pendiente emitir la retención con el botón Añadir Retención"
        - En el post de la retención debe removerse la alerta, pero si se anula la retención debe volver a ponerse
        '''
        warning_msgs = ''
        missing_withhold_error = u'Acorde a los impuestos que usted ha seleccionado está pendiente aprobar la retención, de no ser así corrija los impuestos.'
        aproved_states = ['open','paid']
        if self.state not in aproved_states:
            return warning_msgs
        #determinamos si debemos emitir retenciones electronicas
        electronic = False
        if 'electronic_docs_start_date' in self.company_id._fields \
        and self.date >= self.company_id.electronic_docs_start_date: 
            #determina si el modulo docs electronicos esta instalado
            #y que sean documentos emitidos con fecha posterior  
            electronic = True
        if not electronic and not self.has_valid_withholds and self.total_to_withhold != 0.0:
            #caso de punto de emision preimpreso
            warning_msgs = missing_withhold_error
        elif electronic and not self.has_valid_withholds and self._validate_require_withhold():
            #caso de punto de emision electronico
            #en documentos electronicos SIEMPRE se emite retencion, asi sea de valor 0.0
            warning_msgs = missing_withhold_error
        else:
            pass
        return warning_msgs
    
    #columns
    l10n_ec_require_withhold_tax = fields.Boolean(compute='_l10n_ec_compute_require_withhold_tax')
    l10n_ec_require_vat_tax = fields.Boolean(compute='_l10n_ec_compute_require_vat_tax')
    l10n_ec_bypass_validations = fields.Boolean(
        string='Bypass Validaciones',
        readonly=True,
        copy=False,
        track_visibility='onchange',
        states={'posted': [('readonly', False)], 'draft': [('readonly', False)]},
        help='Bypass para ciertas validaciones ecuatorianas:\n'
        '- Permite anular facturas con retenciones ya emitidas\n'
        '- Permite aprobar facturas sin impuestos',
        )

class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    def _get_computed_taxes(self):
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
        super_tax_ids = super(AccountMoveLine, self)._get_computed_taxes()
                
        vat_withhold_tax = False
        profit_withhold_tax = False
        if self.move_id.country_code == 'EC':
            if self.move_id.is_purchase_document(include_receipts=True):
                if not self.exclude_from_invoice_tab: #just regular invoice lines
                    if self.move_id.l10n_ec_require_withhold_tax: #compute withholds
                        company_id = self.move_id.company_id
                        fiscal_postition_id = self.move_id.fiscal_position_id
                        tax_groups = super_tax_ids.mapped('tax_group_id').mapped('l10n_ec_type')

                        #compute vat withhold
                        if 'vat12' in tax_groups or 'vat14' in tax_groups:
                            if not self.product_id or self.product_id.type in ['consu']:
                                vat_withhold_tax = fiscal_postition_id.l10n_ec_vat_withhold_goods
                            else: #services
                                vat_withhold_tax = fiscal_postition_id.l10n_ec_vat_withhold_services
                        
                        #compute profit withhold
                        if self.move_id.l10n_ec_payment_method_id.code in ['16','18','19']:
                            #payment with debit card, credit card or gift card retains 0%
                            profit_withhold_tax = company_id.l10n_ec_profit_withhold_tax_credit_card
                        elif self.partner_id.property_l10n_ec_profit_withhold_tax_id:
                            profit_withhold_tax = self.partner_id.property_l10n_ec_profit_withhold_tax_id
                        elif 'withhold_income_tax' in tax_groups:
                            pass #keep the taxes coming from product.product... for now
                        else: #if not any withhold tax then fallback
                            if self.product_id and self.product_id.type == 'service':
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_services
                            else:
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_goods
                    else: #remove withholds
                        super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat','withhold_income_tax'])
            if vat_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat'])
                super_tax_ids += vat_withhold_tax
            if profit_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_income_tax'])
                super_tax_ids += profit_withhold_tax
        return super_tax_ids        
        

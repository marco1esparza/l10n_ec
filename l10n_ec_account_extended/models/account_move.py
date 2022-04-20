# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import format_date

from datetime import datetime


class AccountMove(models.Model):
    _inherit='account.move'

    def write(self, vals):
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['l10n_ec_authorization', 'l10n_ec_sri_tax_support_id']
        # Check the tax lock date.
        if any(self.env['account.move']._field_will_change(self, vals, field_name) for field_name in PROTECTED_FIELDS_TAX_LOCK_DATE):
            self._check_tax_lock_date()
        return super().write(vals)

    def _check_tax_lock_date(self):
        for move in self.filtered(lambda x: x.state == 'posted'):
            if move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date:
                raise UserError(_("The operation is refused as it would impact an already issued tax statement. "
                                  "Please change the journal entry date or the tax lock date set in the settings (%s) to proceed.")
                                % format_date(self.env, move.company_id.tax_lock_date))
        
    def button_draft(self):
        #Execute ecuadorian validations with bypass option
        for document in self:
            bypass = False
            if document.country_code == 'EC':
                bypass = document.l10n_ec_bypass_validations
                if not bypass:
                    document._l10n_ec_validations_to_draft()
                    document._l10n_ec_validations_to_draft_when_edi()
            #hack: send the context to later bypass account_edi restrictions
            super(AccountMove, document.with_context(l10n_ec_bypass_validations=bypass)).button_draft()
            document.l10n_ec_bypass_validations = False #Reset bypass to default value
            #there is no return res or any return for button_draft()
    
    @api.depends('state','edi_document_ids.state','edi_document_ids.attachment_id')
    def _compute_edi_show_cancel_button(self):
        #hack to bypass account_edi restrictions and be able to cancel the document, only inside the cancellation flow
        bypass = self._context.get('l10n_ec_bypass_validations',False)
        if bypass:
            self.edi_show_cancel_button = False
        else:
            return super()._compute_edi_show_cancel_button()
        
    @api.depends('l10n_latam_document_type_id', 'journal_id', 'l10n_ec_printer_id')
    def _compute_l10n_latam_manual_document_number(self):
        # trigger computation depending on l10n_ec_printer_id
        # return super()._compute_l10n_latam_manual_document_number()
        # until bug https://github.com/odoo/odoo/pull/65673 is merged we include fix here:
        recs_with_journal_id = self.filtered(lambda x: x.journal_id and x.journal_id.l10n_latam_use_documents)
        for rec in recs_with_journal_id:
            rec.l10n_latam_manual_document_number = rec._is_manual_document_number()
        remaining = self - recs_with_journal_id
        remaining.l10n_latam_manual_document_number = False
    
    #TODO V15.2 Revisar si se incorpora en el l10n_ec_edi para reprocesamientos o creación manual
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
        #if self.state in ['cancel']:
        ec_edi = self.edi_document_ids.filtered(lambda x: x.edi_format_id.code == 'l10n_ec_tax_authority')
        procesing_edi_job = self._context.get('procesing_edi_job',False)
        if ec_edi and not procesing_edi_job:
            #la anulación edi de account_edi obliga a pasar temporalmente por draft, mediante el
            #contexto procesing_edi_job bypaseamos la restricción cuando es una anulación del proceso edi
            raise UserError(_(
                "You can't set to draft the journal entry %s because an electronic document has already been requested. "
                "Instead you can cancel this document (Request EDI Cancellation button) and then create a new one"
                "|n|n"
                "DebugData:ID%s,S%s,C%s"
            ) % (self.display_name,str(self.id),self.state,str(procesing_edi_job)))
    
    def _post(self, soft=True):
        #Execute ecuadorian validations with bypass option
        for document in self:
            document._fix_partner_in_amls()
            if document.country_code == 'EC':
                
                # Corregimos bug de Odoo... para Ecuador removemos el Factur-X, cambios en el core de Odoo causan que se vuelva a incluir
                ecuador_edis = document.journal_id.edi_format_ids.filtered(lambda x: x.code == 'l10n_ec_tax_authority')
                unnecesary_edis = document.journal_id.edi_format_ids - ecuador_edis
                document.journal_id.sudo().edi_format_ids -= unnecesary_edis #se elimina el factur-x del diarios
                if document.journal_id.compatible_edi_ids.filtered(lambda e: e.code == 'facturx_1_0_05'):
                    raise UserError(_("Por favor, debe deshabilitar primero el Documento Electrónico Factur-X (FR) del Diario %s, Contabilidad/Configuración/Diarios Contables") % self.journal_id.name)
                #FIX ME: a veces, con puntos de emision nuevos, no se computa el perfijo de la factura en el numero
                document._inverse_l10n_latam_document_number()
                bypass = document.l10n_ec_bypass_validations
                if not bypass: #TODO V15 poner algo como if not bypass and require_document
                    document._l10n_ec_validations_to_posted()
                    # Se inicializa el amount_total_refunds con el monto de la nota de credito actual, pues al estar
                    # en estado borrador queda excluida en la verificacion que se realiza mas adelante y evitamos que se
                    # aprueben nc con montos superiores a la factura cuando no existe ninguna aprobada previamente
                    # Para las notas de credito exterior se setea amount_total_refunds con el valor de la NC
                    # ya que no cuenta con un invoice_rectification_id para obtener el total de la factura.
                    # Caso especial NC exterior
                    if document.move_type in ['in_refund', 'out_refund']:
                        if self.partner_id != self.reversed_entry_id.partner_id:
                            raise UserError(_("Por favor, no puede crear una Nota de Credito con Cliente/Proveedor distinto a %s") % self.reversed_entry_id.name)
                        if document.l10n_latam_document_type_id.code == '0500':
                            amount_total_refunds = 0.00
                        else:
                            amount_total_refunds = document.l10n_ec_total_with_tax
                        for refund in document.reversed_entry_id.reversal_move_id.\
                                filtered(lambda m: m.id != document.id and m.move_type in ['in_refund', 'out_refund']
                                                   and m.state in ['posted']):
                            amount_total_refunds += refund.l10n_ec_total_with_tax
                        refund_value_control = document.company_id.l10n_ec_refund_value_control
                        if float_compare(amount_total_refunds, document.reversed_entry_id.l10n_ec_total_with_tax, precision_digits=2) == 1 \
                                and refund_value_control == 'local_refund':
                            raise UserError(_(u'La nota de crédito %s no se puede aprobar debido a que el valor de las '
                                              u'notas de crédito emitidas más la actual suman USD %s, sobrepasando el '
                                              u'valor de USD %s de la factura %s.')
                                            % (document.name, amount_total_refunds,
                                               document.reversed_entry_id.l10n_ec_total_with_tax, document.reversed_entry_id.name))
                        # Validacion de notas de credito no se las realice a consumidor final
                        if document.company_id.l10n_ec_refund_value_control == 'local_refund' \
                                and document.partner_id.vat == '9999999999999':
                            raise UserError(_(u'La nota de crédito %s no se puede aprobar debido a que en REGLAMENTO DE '
                                              u'COMPROBANTES DE VENTA, RETENCIÓN Y DOCUMENTOS COMPLEMENTARIOS en su ART 15 '
                                              u'y ART 25 impiden la emision de Notas de crédito a "Consumidor Final".')
                                            % (document.name,))
        #hack: send the context to later bypass account_edi restrictions
        # Se modifica la ejecucion del post al final porque res se debe devolver con la ejecucion de todos los documentos
        res = super(AccountMove, self)._post(soft)
        self.l10n_ec_bypass_validations = False #Reset bypass to default value
        return res
    
    def _fix_partner_in_amls(self):
        # Ticket #18334, a veces los amls llevan un partner distinto que la cabecera
        # Ticket #19729, a veces los amls tienen partner vacío
        # posiblemente se hizo así al hacer la PO a un partner A pero cambiar el partner al momento de la factura
        self.ensure_one()
        if self.move_type in ['in_invoice','out_invoice','in_refund','out_refund']:
            # TODO podría ponerse un contexto para hacer bypass heredable en desarrollos especificos 
            # partners = self.line_ids.mapped('partner_id')
            # partners = partners | document.partner_id.commercial_partner_id
            # if len(partners) != 1:
            #     raise UserError(_("Algunas lineas del asiento contable tienen una empresa diferente a la de la cabecera de la factura, borre, guarde, y vuelva a colocar la empresa en la factura %s") % self.name)
            commercial_partner_id = self.partner_id.commercial_partner_id
            for line in self.line_ids.filtered(lambda x:x.display_type not in ['line_section','line_note']):
                if not line.partner_id == commercial_partner_id:
                    line.partner_id = commercial_partner_id
    
    def _l10n_ec_validations_to_posted(self):
        #Execute extra validations for Ecuador when posting the move
        if self.l10n_latam_document_type_id.l10n_ec_require_vat:
            #Require partner's VAT type and ID
            if not self.partner_id.vat:
                raise UserError(_("Please set a VAT number in the partner for document %s") % self.display_name)
            if self.partner_id.vat == '9999999999999':
                if self.move_type == 'out_invoice' and float_compare(self.amount_total, 200, precision_rounding=self.currency_id.rounding) > 0:
                    raise UserError(_("Para facturas de Consumidor Final no se puede superar los $200 USD."))
                if self.move_type in ('in_invoice', 'in_refund'):
                    raise UserError(_("No se pueden emitir Documentos de Compras como Consumidor Final"))
            #TODO V14 implemnetar validacion del tipo de documento, debe estar seteado con una opción válida
        is_electronic_document = self.move_type in ['in_invoice','in_refund','out_invoice','out_refund'] and self.l10n_ec_printer_id.allow_electronic_document
        if is_electronic_document:
            # no se puede emitir documentos electronicos con descripcion mayor a 300 caracteres
            if len(self.narration or '') > 300:
                raise UserError(_("Por favor, Corrija los términos y cóndiciones pues es muy extenso, se aceptan máximo 300 caracteres y usted ingresó %s caracteres") % narration)
        if self.l10n_ec_authorization_type == 'third' and self.l10n_ec_authorization:
            #validamos la clave de acceso contra los datos de la cabecera de la factura
            self._l10n_ec_validate_authorization()
        if self.move_type in ['in_refund']:
            #las notas de credito del exterior deben usar otro tipo de documento para que no vayan al ATS y para q no requieran impuestos
            if self.reversed_entry_id.l10n_latam_document_type_id.code == '15' and not self.l10n_latam_document_type_id.code == '110': 
                raise UserError(_("En el documento %s debe cambiar el tipo de documento a Nota de Crédito del Extranjero (código 110)") % self.display_name)
            elif self.reversed_entry_id.l10n_latam_document_type_id.code != '15' and self.l10n_latam_document_type_id.code == '110': 
                raise UserError(_("En el documento %s debe cambiar el tipo de documento a Nota de Crédito (código 04)") % self.display_name)
        #validations per invoice line
        l10n_ec_require_withhold_tax = self.l10n_ec_require_withhold_tax
        l10n_ec_require_vat_tax = self.l10n_ec_require_vat_tax
        #remove sections and comments
        move_lines = self.invoice_line_ids.filtered(lambda x:x.display_type not in ['line_section','line_note'])
        for line in move_lines:
            if self.move_type in ('in_refund', 'out_refund'):
                if line.tax_ids.filtered(lambda x:x.tax_group_id.l10n_ec_type in ['withhold_vat', 'withhold_income_tax']):
                    raise UserError('Las notas de crédito no deben tener impuesto de retención (IVA o RENTA), verifique la línea con producto "%s".' % line.name)
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
            if l10n_ec_require_vat_tax and len(vat_taxes) != 1:
                raise UserError(_("Please select one and only one vat type (IVA 12, IVA 0, etc) for product:\n\n%s") % line.name)
            elif not l10n_ec_require_vat_tax and vat_taxes:
                raise UserError(_("Por favor remueva el IVA del producto:\n\n%s") % line.name)
            #TODO v15.2 Volver a poner la validacion
            # if l10n_ec_require_withhold_tax:
            #     if len(profit_withhold_taxes) != 1:
            #         raise UserError(_("Please select one and only one profit withhold type (312, 332, 322, etc) for product:\n\n%s") % line.name)
            #     if len(vat_withhold_taxes) not in [0,1]:
            #         raise UserError(_("Please select no more than one vat withhold tax for product:\n\n%s") % line.name)
            # else:
            #     if len(profit_withhold_taxes) + len(vat_withhold_taxes):
            #         raise UserError(_("This document doesn't needs a withholding tax, please remove it for product:\n\n%s") % line.name)
    
    def _l10n_ec_validate_authorization(self):
        '''
        - Validate the authorization number lenght
        - Validate access_key integrity against invoice number, date, ruc, etc
        '''
        auth_len = len(self.l10n_ec_authorization)
        if auth_len in (10, 42):
            return True  # no podemos aplicar ninguna validacion
        if auth_len != 49:
            raise UserError(_("El número de Autorización es incorrecto, presenta %s dígitos") % auth_len)
        #la siguiente seccion es solo para el caso de 49 digitos, osea claves de acceso
        access_key_data = self._extract_data_from_access_key()
        if self.invoice_date != access_key_data['document_date']:
            invoice_date = self.invoice_date.strftime('%d%m%Y')
            access_key_date = access_key_data['document_date'].strftime('%d%m%Y')
            raise ValidationError(u'No existe correspondencia entre la clave de acceso "%s" y la fecha del documento "%s", para la autorización seleccionada se espera '\
                                  u'como fecha del documento"%s".' % (self.l10n_ec_authorization, invoice_date, access_key_date))
        # se comparan los codigos en lugar de los ids para soportar el caso de reembolso de gastos
        source_code = access_key_data['source_code']
        destination_code = self.l10n_latam_document_type_id.l10n_ec_map_document_type_code_to_electronic_code() 
        if source_code != destination_code:
            raise ValidationError(u'No existe correspondencia entre la clave de acceso "%s" pues su documento (digito 9 y 10) es "%s", para documento seleccionado se espera '\
                                  u'como codigo de documento "%s".' % (self.l10n_ec_authorization, source_code, destination_code))
        if self.partner_id.vat != access_key_data['partner_vat']:
            raise ValidationError(u'No existe correspondencia entre la clave de acceso "%s" y el RUC registrado "%s", para la autorización seleccionada se espera '\
                                  u'como RUC del documento"%s".' % (self.l10n_ec_authorization, self.partner_id.vat, access_key_data['partner_vat']))
        if self.l10n_latam_document_number != access_key_data['document_number']:
            raise ValidationError(u'No existe correspondencia entre la clave de acceso "%s" y el número de factura "%s", para la autorización seleccionada se espera '\
                                  u'como número de factura "%s".' % (self.l10n_ec_authorization, self.l10n_latam_document_number, access_key_data['document_number']))
        
    @api.onchange('l10n_ec_authorization')
    def onchange_l10n_ec_authorization(self):
        '''
        For invoices in draft:
        - Updates partner, invoice number, invoice date, etc
        For invoices in posted or cancel:
        - Validates integrity against already existing partner, invoice number, invoice date, etc
        '''
        if self.l10n_ec_authorization:
            if self.state in ['draft']:
                self._update_document_header_from_access_key()
            elif self.state in ['posted','cancel']:
                self._l10n_ec_validate_authorization()
            else:
                raise #nunca deberia caer aqui
    
    def _extract_data_from_access_key(self):
        '''
        Extrae los diferentes campos de la clave de acceso (la clave de acceso es guardada en el campo name
                Estructura de la clave de acceso:
                Nro Digitos    Campo
                8              fecha de emision
                2              tipo de comprobante
                13             numero de ruc 
                1              tipo de ambiente 
                3              tienda
                3              pto emision 
                9              nro comprobante 
                8              filler 
                1              tipo emision 
                1              digito verificador
        Retorna un diccionario con los datos
        '''
        access_key = self.l10n_ec_authorization
        document_date = datetime.strptime(access_key[0:8], "%d%m%Y").date()
        #l10n_latam_document_type_id
        if self.move_type in ['out_invoice','out_refund','in_invoice','in_refund']:
            l10n_ec_type_filter = self.move_type
        elif self.l10n_ec_withhold_type:
            l10n_ec_type_filter = self.l10n_ec_withhold_type
        else:
            raise #nunca deberia caer aquí, problema con tipos de documentos
        source_code = access_key[8:10]
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
            [('code','=',source_code),
             ('l10n_ec_type','=',l10n_ec_type_filter),],
            limit=1)
        if not l10n_latam_document_type_id:
            raise UserError(_("No se ha encontrado un tipo de documento con codigo %s") % access_key[8:10])
        #vat_emmiter
        partner_vat = access_key[10:23]
        partner_id = self.partner_id
        if not partner_id.vat == partner_vat:
            #cambiamos de partner solo si el seleccionado no cumple 
            partner_id = self.env['res.partner'].search(
                [('vat','=',partner_vat)
                 ],limit=1).commercial_partner_id        
        environment_type = access_key[23:24]
        if self.company_id.l10n_ec_environment_type == '2': #ambiente producción
            if environment_type != '2':
                raise UserError(_("No se debe digitar claves de acceso de un ambiente de pruebas en un ambiente de producción, los documentos de ambiente de pruebas no son validos"))
        document_number = "-".join([access_key[24:27],access_key[27:30],access_key[30:39]])
        #filler del 40 al 47, no se usa
        emission_type = access_key[47:48]
        if emission_type != '1':
            raise UserError(_("Actualmente, bajo el esquema offline, el tipo de emisión no puede ser 'contingencia'"))        
        #49 digito verificador, no se usa
        return {
            'document_date': document_date,
            'source_code': source_code,
            'l10n_latam_document_type_id': l10n_latam_document_type_id,
            'partner_vat': partner_vat,
            'partner_id': partner_id, #sometimes False
            'environment_type': environment_type,
            'document_number': document_number,
            'emission_type': emission_type,
            }
        
    def _update_document_header_from_access_key(self):
        auth_len = len(self.l10n_ec_authorization)
        if auth_len in (10,42):
            return True #no podemos aplicar ninguna validacion
        if auth_len != 49:
            raise UserError(_("El número de Autorización es incorrecto, presenta %s dígitos, debe ser de 10 o 42 digitos") % auth_len)
        access_key_data = self._extract_data_from_access_key()
        self.invoice_date = access_key_data['document_date']
        if access_key_data['partner_id'] and self.l10n_latam_document_type_id.l10n_ec_authorization != 'own':
            self.partner_id = access_key_data['partner_id']
        if access_key_data['l10n_latam_document_type_id']:
            self.l10n_latam_document_type_id = access_key_data['l10n_latam_document_type_id']
        else:
            #TODO V15, deberíamos poder popup el form del partner prellenada su RUC
            self.partner_id = False
        self.l10n_latam_document_number = access_key_data['document_number']
            
    def _validate_require_withhold(self):
        '''
        Bypass las retenciones tarjetas de Credito
        '''
        validate = True
        credit_card = self.company_id.default_profit_withhold_tax_corporate_credit_card
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
        aproved_states = ['posted','cancel']
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

#     def unlink(self):
#         """ When using documents, on vendor bills the document_number is set manually by the number given from the vendor,
#         the odoo sequence is not used. In this case We allow to delete vendor bills with document_number/move_name """
#         for move in self:
#             if move.country_code == 'EC' and move.state in ['draft'] and move.l10n_latam_use_documents:
#                 edi_ec = move.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'l10n_ec_tax_authority')
#                 if not edi_ec:
#                     #TODO: Llamar a super con contexto
#                     move.with_context(force_delete=True).unlink()
#                     move.write({'name': '/'})
#         return super().unlink()
    
    @api.model
    def _default_l10n_ec_printer_id(self):
        #Redefine por completo el metodo de l10n_ec_edi, para soportar punto de emision en formulario de usuario
        if self._context.get('default_l10n_ec_printer_id'):
            printer_id = self.env['l10n_ec.printer.id'].browse(self._context['default_l10n_ec_printer_id'])
            return printer_id
        printer_id = False
        company_id = self.env.company #self.country_code is still empty
        if company_id.country_code == 'EC':
            move_type = self._context.get('default_move_type',False) or \
                        self._context.get('default_withhold_type',False) or \
                        self._context.get('default_waybill_type', False) #self.type is not yet populated
            if move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_withhold', 'out_waybill']:
                #regular account.move doesn't need a printer point
                printer_id = self.env.user.property_l10n_ec_printer_id.id
                if not printer_id: #search first printer point
                    printer_id = self.env['l10n_ec.sri.printer.point'].search([('company_id', '=', company_id.id)], order="sequence asc", limit=1)
        return printer_id
    
    #columns
    l10n_ec_bypass_validations = fields.Boolean(
        string='Bypass Validaciones',
        readonly=True,
        copy=False,
        tracking=True,
        states={'posted': [('readonly', False)], 'draft': [('readonly', False)]},
        help='Bypass para ciertas validaciones ecuatorianas:\n'
        '- Permite anular facturas con retenciones ya emitidas\n'
        '- Permite aprobar facturas sin impuestos',
        )

#     @api.constrains('l10n_latam_document_type_id', 'name', 'move_type')
#     def _check_l10n_latam_document_number_doctype_41(self):
#         for move in self:
#             if move.l10n_latam_document_type_id and move.l10n_latam_document_type_id.code == '41' and move.name \
#                     and move.move_type:
#                 doc_code_prefix = move.l10n_latam_document_type_id.doc_code_prefix
#                 name = move.name
# #                 if doc_code_prefix and name:
#                     name = name.split(" ", 1)[-1]
#                 count = self.env['account.move'].search(
#                     [('l10n_latam_document_type_id', '=', move.l10n_latam_document_type_id.id),
#                      ('name', 'ilike', name), ('move_type', '=', 'in_invoice')])
#                 if len(count) > 1:
#                     raise ValidationError('No pueden existir varios documentos con el mismo numero de documento.')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        # Restrict reconciliation to SAME PARTNER
        partner = None
        for line in self:
            if partner is None:
                partner = line.partner_id
            elif line.partner_id != partner:
                if not self.env.context.get('allow_different_partner_entries'):
                    raise UserError(_("Las entradas no son de la misma empresa: %s != %s")
                                    % (partner.display_name, line.partner_id.display_name))
        res = super().reconcile()
        return res
    
    @api.depends('tax_repartition_line_id', 'tax_tag_ids')
    def _compute_l10n_ec_editable_base_tax(self):
        #TODO editar en todos los estados hasta el cierre de la fecha de impuestos
        imports_tax_codes = ['523', #Importación servicios
                             '524', #Importacion bienes
                             '525', #Importación activos
                             ]
        for line in self:
            line.l10n_ec_editable_base_tax = False
            if line.move_id.country_code == 'EC' \
               and line.move_id.l10n_latam_document_type_id \
               and line.tax_repartition_line_id \
               and line.move_id.l10n_latam_document_type_id.code == '16' \
               and line.move_id.move_type == 'in_invoice'  \
               and line.tax_repartition_line_id.tax_id.l10n_ec_code_applied in imports_tax_codes:
                line.l10n_ec_editable_base_tax = True

    l10n_ec_editable_base_tax = fields.Boolean(
        compute='_compute_l10n_ec_editable_base_tax',
        help='Campo técnico, permite editar la base imponible en el DAU'
        )
    tax_base_amount = fields.Monetary(readonly=False) #redefinimos para hacer la base editable en el DAU

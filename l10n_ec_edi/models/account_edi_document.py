# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from lxml import etree
import base64

from odoo.addons.l10n_ec_edi.models.common_methods import get_SRI_normalized_text, clean_xml, validate_xml_vs_xsd, XSD_SRI_110_FACTURA, XSD_SRI_110_NOTA_CREDITO, XSD_SRI_110_LIQ_COMPRA
from odoo.addons.l10n_ec_edi.models.amount_to_words import l10n_ec_amount_to_words

from bs4 import BeautifulSoup

from suds.client import Client #para los webservices, pip install suds-community
DEFAULT_ECUADORIAN_DATE_FORMAT = '%d-%m-%Y'
ELECTRONIC_SRI_WSDL_RECEPTION_OFFLINE = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
ELECTRONIC_SRI_WSDL_RECEPTION_TEST_OFFLINE = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
ELECTRONIC_SRI_WSDL_AUTORIZATION_OFFLINE = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
ELECTRONIC_SRI_WSDL_AUTORIZATION_TEST_OFFLINE = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'

_IVA_CODES = ('vat12', 'vat14', 'zero_vat', 'not_charged_vat', 'exempt_vat') 
_ICE_CODES = ('ice',) 
_IRBPNR_CODES = ('irbpnr',)
_MICROCOMPANY_REGIME_LABEL = 'CONTRIBUYENTE RÉGIMEN MICROEMPRESAS'
_RIMPE_REGIME_LABEL = u'CONTRIBUYENTE RÉGIMEN RIMPE'

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def send_email_success(self, invoices):
        for document in invoices.mapped('edi_document_ids'):
            if document.state == 'sent':
                action_invoice_wizard = document.move_id.action_invoice_sent()
                ctx = action_invoice_wizard["context"]
                ctx.update(
                    {
                        "active_id": document.move_id.id,
                        "active_ids": document.move_id.ids,
                        "active_model": "account.move",
                    }
                )
                invoice_wizard = (
                    self.env[action_invoice_wizard["res_model"]].with_context(ctx).create({})
                )
                invoice_wizard._compute_composition_mode()
                invoice_wizard.onchange_template_id()
                invoice_wizard.send_and_print_action()
    
    def _process_job(self, documents, doc_type):
        #sends an email
        #context to bypass _l10n_ec_validations_to_draft_when_edi validations when
        #voiding a document
        super(AccountEdiDocument,  self.with_context(procesing_edi_job=True))._process_job(documents, doc_type)
        self.send_email_success(documents.mapped('move_id').filtered(lambda x: x.country_code == 'EC'))

    def _l10n_ec_set_access_key(self):
        #writes de access key of the document
        self.ensure_one()
        if not self.move_id:
            raise ValidationError("Error, el documento electrónico no está vinculado a un asiento contable %s" % self.name)
        related_document = self.move_id
        # cargamos los datos generales
        data_model = related_document._name
        filler = 3 #puede ser cualquier numero, 3 de trescloud! :)
        # Dato para el portal web
        if data_model == 'account.move':
            date = related_document.invoice_date
            document_type = related_document.move_type
            code_document_type = str(
                related_document.l10n_latam_document_type_id.code
            )
            if document_type in ('out_invoice','out_refund'):
                if code_document_type in ('18', '41'):
                    # Factura de venta y reembolso se mapea con codigo '01'
                    code_document_type = '01'
            elif document_type in ('in_invoice',):
                if code_document_type in ('03', '41'):
                    # Liquidacion de compra y reembolso se mapea con codigo '03'
                    code_document_type = '03'
            serie = related_document.l10n_latam_document_number
        else:
            raise ValidationError(
                u'No se ha implementado documentos electronicos para '
                u'este modelo de datos'
            )

        access_key = self.l10n_ec_get_access_key(
            filler, date, code_document_type, serie,
            related_document.company_id.vat,
            self.move_id.company_id.l10n_ec_environment_type,
        )
        self.l10n_ec_access_key = access_key
    
    @api.model
    def l10n_ec_get_access_key(self, filler_number, date, code_document_type,
                       l10n_latam_document_number, company_vat, environment_type):
        '''
        Genera la clave de acceso del documento electronico
        '''
        def AuxGenerateModulus11(Numero):
            '''
            Input en la forma: 
            Numero=2334568734
            '''
            if str(Numero) != Numero:
               Numero = str(Numero)    
            x = 0
            factor = 2
            for c in reversed(Numero):    
                try:
                    int(c)
                except ValueError:
                    # not numeric
                    continue           
                else:
                    # numeric
                    x += int(c) * factor
                    factor += 1
                    if factor == 8:
                        factor = 2
            #Calcula el digito de control.
            Control = (11 - (x % 11)) % 11
            return Control

        # cargamos los datos generales
        cadena = ''
        fill = 8
        cod_number = '0' * (fill - len(str(filler_number))) + \
                     str(filler_number)
        type_emm = '1'
        #vat_emmiter = _get_clear_vat(company_vat)
        vat_emmiter = company_vat
        '''first value date'''
        date = date.strftime('%d%m%Y')
        cadena += date
        '''second value tipo de comprobante, tabla 4 de la ficha
         tecnica de docs electronicos'''
        cadena += code_document_type
        '''third value VAT number'''
        # Es el RUC de la empresa que emite el documento
        cadena = cadena + vat_emmiter
        '''fourth value tipo de ambiente'''
        cadena = cadena + environment_type
        '''fifth value serie and sixth value number'''
        try:
            # si no tiene guienes en la mitad en la
            # forma numero-numero-numero da error
            serie = l10n_latam_document_number.split('-')
            cadena = cadena + serie[0] + serie[1] + serie[2]
        except:
            # TODO: corregir el raise, esta deprecado
            raise ValidationError(
                _(u'El numero de documento %s presenta errores al generar la clave de acceso: %s') % (
                    serie, cadena
                )
            )
        '''seven value numeric code '''
        cadena += cod_number
        '''eigth value tipo emision siempre sera 1 '''
        cadena += type_emm
        number_c = int(cadena)
        digit_ver = AuxGenerateModulus11(number_c)
        # Cuando el resultado del dígito verificador obtenido
        # sea igual a once (11), el digito verificador será el cero (0) y
        # cuando el resultado del dígito verificador obtenido sea igual
        # a diez 10, el digito verificador será el uno (1).
        if digit_ver == 10:
            digit_ver = 1
        elif digit_ver == 11:
            digit_ver = 0
        cadena = cadena + str(digit_ver)
        return cadena
    
    def _l10n_ec_generate_request_xml_file(self):
        #generates and validates an xml request to later be sent to SRI
        self.ensure_one()
        if not self.move_id.is_invoice():
           return
        etree_content = self._l10n_ec_get_xml_request_for_sale_invoice()
        xml_content = clean_xml(etree_content)
        try: #validamos el XML contra el XSD
            if self.move_id.move_type in ('out_invoice') and self.move_id.l10n_latam_document_type_id.code in ['18','41']:
                validate_xml_vs_xsd(xml_content, XSD_SRI_110_FACTURA)
            elif self.move_id.move_type in ('out_refund') and self.move_id.l10n_latam_document_type_id.code in ['04']:
                validate_xml_vs_xsd(xml_content, XSD_SRI_110_NOTA_CREDITO)
            elif self.move_id.move_type in ('in_invoice') and self.move_id.l10n_latam_document_type_id.code in ['03', '41']:
                validate_xml_vs_xsd(xml_content, XSD_SRI_110_LIQ_COMPRA)
        except ValueError: 
            raise UserError(u'No se ha enviado al servidor: ¿quiza los datos estan mal llenados?:' + ValueError[1])        
        self.l10n_ec_request_xml_file_name = self.move_id.name + '_draft.xml'
        self.l10n_ec_request_xml_file = base64.encodebytes(xml_content)
        return True
    
    @api.model
    def _l10n_ec_get_xml_request_for_sale_invoice(self):
        # INICIO CREACION DE FACTURA
        type = self.move_id.move_type
        document_type = self.move_id.l10n_latam_document_type_id
        if type == 'out_invoice':
            if document_type.code in ('18', '41'):
                factura = etree.Element('factura', {'id': 'comprobante', 'version': '1.1.0'})
#             elif document_type.code == '05':
#                 return self._getNotaDebito()
        elif type == 'out_refund':
            factura = etree.Element('notaCredito', {'id': 'comprobante', 'version': '1.1.0'})
        elif type == 'in_invoice':
            if document_type.code in ('03','41'):
                factura = etree.Element('liquidacionCompra', {'id': 'comprobante', 'version': '1.1.0'})
        # CREACION INFO TRIBUTARIA
        infoTributaria = etree.SubElement(factura, 'infoTributaria')
        if not self.move_id.company_id.l10n_ec_legal_name:
            raise UserError('Defina el nombre legal para la compañía "%s".' % (self.move_id.company_id.name))
        infoTribElements = [
            ('ambiente', self.move_id.company_id._get_l10n_ec_environment_type()),
            ('tipoEmision', '1'),
            ('razonSocial', self.move_id.company_id.l10n_ec_legal_name)
        ]
        if self.move_id.company_id.partner_id.l10n_ec_commercial_name:
            infoTribElements.append(('nombreComercial', self.move_id.company_id.partner_id.l10n_ec_commercial_name))
        infoTribElements.extend([
            ('ruc', self.move_id.company_id.partner_id.vat),
            ('claveAcceso', self.l10n_ec_access_key)
        ])
        if type == 'out_invoice':
            infoTribElements.append(('codDoc', '01'))
        elif type == 'out_refund':
            infoTribElements.append(('codDoc',document_type.code))
        elif type == 'in_invoice':
            if document_type.code in ('03','41'):
                infoTribElements.append(('codDoc', '03'))
        infoTribElements.extend([
            ('estab', self.move_id.l10n_latam_document_number[0:3]),
            ('ptoEmi', self.move_id.l10n_latam_document_number[4:7]),
            ('secuencial', self.move_id.l10n_latam_document_number[8:]),
            ('dirMatriz', self.move_id.company_id.partner_id._get_complete_address())
            ])
        if self.move_id.company_id.l10n_ec_regime == 'micro':
            infoTribElements.extend([('regimenMicroempresas',_MICROCOMPANY_REGIME_LABEL)])
        if self.move_id.company_id.l10n_ec_withhold_agent == 'designated_withhold_agent':
            infoTribElements.extend([('agenteRetencion',self.move_id.company_id.l10n_ec_wihhold_agent_number)])
        if self.move_id.company_id.l10n_ec_regime == 'rimpe':
            infoTribElements.extend([('contribuyenteRimpe', _RIMPE_REGIME_LABEL)])
        self.create_TreeElements(infoTributaria, infoTribElements)
        # CREACION INFO FACTURA
        if type == 'out_invoice':
            infoFactura = etree.SubElement(factura, 'infoFactura')
        elif type == 'out_refund':
            infoFactura = etree.SubElement(factura, 'infoNotaCredito')
        elif type == 'in_invoice':
            if document_type.code in ('03', '41'):
                infoFactura = etree.SubElement(factura, 'infoLiquidacionCompra')
        infoFactElements = [
            ('fechaEmision', datetime.strftime(self.move_id.invoice_date,'%d/%m/%Y')),
            ('dirEstablecimiento', self.move_id.l10n_ec_printer_id.printer_point_address)
        ]
        get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
        if type == 'out_invoice':
            if self.move_id.company_id.l10n_ec_special_contributor_number:
                infoFactElements.append(('contribuyenteEspecial', self.move_id.company_id.l10n_ec_special_contributor_number))
            infoFactElements.extend([
                ('obligadoContabilidad', 'SI' if self.move_id.company_id.l10n_ec_forced_accounting else 'NO'),
                ('tipoIdentificacionComprador', self.move_id.partner_id.get_invoice_ident_type()),
                #TODO: cuando se arregle el metodo get_SRI_normalized_text borrar la sig linea y descomentar la otra
                ('razonSocialComprador', get_invoice_partner_data['invoice_name']),
                #('razonSocialComprador', get_SRI_normalized_text(get_invoice_partner_data['invoice_name'])),
                ('identificacionComprador', get_invoice_partner_data['invoice_vat']),
                ('totalSinImpuestos', '{0:.2f}'.format(self.move_id.amount_untaxed)),
                ('totalDescuento', '{0:.2f}'.format(self.move_id.l10n_ec_total_discount))
            ])
            if document_type.code == '41':
                amount_total, totalComprobantesReembolso, totalImpuestoReembolso = 0.0, 0.0, 0.0
                for refund_line in self.move_id.refund_ids:
                    amount_total += refund_line.total
                    totalComprobantesReembolso += refund_line.base_tax_free + refund_line.base_vat_0 + \
                        refund_line.no_vat_amount + refund_line.base_vat_no0
                    totalImpuestoReembolso += refund_line.vat_amount_no0
                infoFactElements.extend([
                    ('codDocReembolso', '41'),
                    ('totalComprobantesReembolso', '{0:.2f}'.format(amount_total)),
                    ('totalBaseImponibleReembolso', '{0:.2f}'.format(totalComprobantesReembolso)),
                    ('totalImpuestoReembolso', '{0:.2f}'.format(totalImpuestoReembolso)),
                ])
        elif type == 'out_refund':
            infoFactElements.extend([
                ('tipoIdentificacionComprador', self.move_id.partner_id.get_invoice_ident_type()),
                ('razonSocialComprador', get_invoice_partner_data['invoice_name']),
                ('identificacionComprador', get_invoice_partner_data['invoice_vat'])
            ])
            if self.move_id.company_id.l10n_ec_special_contributor_number:
                infoFactElements.append(('contribuyenteEspecial', self.move_id.company_id.l10n_ec_special_contributor_number)) 
            infoFactElements.extend([
                ('obligadoContabilidad', 'SI' if self.move_id.company_id.l10n_ec_forced_accounting else 'NO'),
                ('codDocModificado', '01'),
                ('numDocModificado', self.move_id.reversed_entry_id.l10n_latam_document_number),
                ('fechaEmisionDocSustento', datetime.strftime(self.move_id.reversed_entry_id.invoice_date,'%d/%m/%Y')),
                ('totalSinImpuestos', '{0:.2f}'.format(self.move_id.amount_untaxed)),
                ('valorModificacion', '{0:.2f}'.format(self.move_id.amount_total)),
                ('moneda', 'DOLAR')
            ])
        elif type == 'in_invoice':
            if document_type.code in ('03','41'):
                if self.move_id.company_id.l10n_ec_special_contributor_number:
                    infoFactElements.append(('contribuyenteEspecial', self.move_id.company_id.l10n_ec_special_contributor_number))
                infoFactElements.extend([
                    ('obligadoContabilidad', 'SI' if self.move_id.company_id.l10n_ec_forced_accounting else 'NO'),
                    ('tipoIdentificacionProveedor', self.move_id.partner_id.get_invoice_ident_type()),
                    ('razonSocialProveedor', get_invoice_partner_data['invoice_name']),
                    ('identificacionProveedor', get_invoice_partner_data['invoice_vat']),
                    ('totalSinImpuestos', '{0:.2f}'.format(self.move_id.amount_untaxed)),
                    ('totalDescuento', '{0:.2f}'.format(self.move_id.l10n_ec_total_discount)),
                ])
                if document_type.code == '41':
                    amount_total, totalComprobantesReembolso, totalImpuestoReembolso = 0, 0, 0
                    for refund_line in self.move_id.refund_ids:
                        amount_total += refund_line.total
                        totalComprobantesReembolso += refund_line.base_tax_free + refund_line.base_vat_0 + \
                            refund_line.no_vat_amount + refund_line.base_vat_no0
                        totalImpuestoReembolso += refund_line.vat_amount_no0
                    infoFactElements.extend([
                        ('codDocReembolso', '41'),
                        ('totalComprobantesReembolso', '{0:.2f}'.format(amount_total)),
                        ('totalBaseImponibleReembolso', '{0:.2f}'.format(totalComprobantesReembolso)),
                        ('totalImpuestoReembolso', '{0:.2f}'.format(totalImpuestoReembolso)),
                    ])
        infoFactElements.append(('totalConImpuestos', None))
        if type == 'out_invoice':
            infoFactElements.extend([
                ('propina', '0.00'),
                ('importeTotal', '{0:.2f}'.format(self.move_id.amount_total)),
                ('pagos', None),
            ])
        elif type == 'out_refund':
            infoFactElements.append(('motivo', self.move_id.ref))
        if type == 'in_invoice':
            if document_type.code in ('03','41'):
                infoFactElements.extend([
                    ('importeTotal', '{0:.2f}'.format(self.move_id.l10n_ec_total_with_tax)),
                ])
        self.create_TreeElements(infoFactura, infoFactElements)
        # CREACION DE TOTAL CON IMPUESTOS
        # Para la creacion de la seccion de impuestos para facturas en 0, debemos revisar si ya ha 
        # sido creado un impuesto, de otro modo la factura debe tener algun valor
        totalConImpuestos = infoFactura.find('totalConImpuestos')
        taxes_zero = True
        # Esta parte analiza el 12% y 14%
        if self.move_id.l10n_ec_base_doce_iva != 0:
            totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
            totalconImpuesto = [] 
            totalconImpuesto.append(('codigo', '2')) #tabla 16
            #el sri permite facturas simultaneas con base 12% y base14%
            #pero nuestro sistema solo permite el uno o el otro, por eso el if
            #TODO v11 hacer un campo funcional que abstraiga esta logica en el pie de la factura 
            vat_percentages = []
            for move_line in self.move_id.line_ids:
                if move_line.tax_group_id:
                    if move_line.tax_group_id.l10n_ec_type in ['vat12', 'vat14']:
                        vat_percentages.append(move_line.tax_line_id.amount)
            vat_percentages = list(set(vat_percentages)) #removemos duplicados
            if len(vat_percentages) != 1:
                raise UserError('No se puede determinar si es IVA 12% o IVA 14%')
            if vat_percentages[0] == 12.0:
                vcodigoPorcentaje = '2'
            elif vat_percentages[0] == 14.0:
                vcodigoPorcentaje = '3'
            totalconImpuesto.append(('codigoPorcentaje', vcodigoPorcentaje))
            totalconImpuesto.append(('baseImponible', '{0:.2f}'.format(self.move_id.l10n_ec_base_doce_iva)))
            totalconImpuesto.append(('valor', '{0:.2f}'.format(self.move_id.l10n_ec_vat_doce_subtotal)))
            self.create_TreeElements(totalImpuesto, totalconImpuesto)
            taxes_zero = False
        # Esta parte analiza el IVA 0%
        if self.move_id.l10n_ec_base_cero_iva != 0:
            totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
            totalconImpuesto = [] 
            totalconImpuesto.append(('codigo', '2'))
            totalconImpuesto.append(('codigoPorcentaje', '0'))
            totalconImpuesto.append(('baseImponible', '{0:.2f}'.format(self.move_id.l10n_ec_base_cero_iva)))
            totalconImpuesto.append(('valor', '0'))
            self.create_TreeElements(totalImpuesto, totalconImpuesto)
            taxes_zero = False
        # Esta parte analiza el iva exento 
        if self.move_id.l10n_ec_base_tax_free != 0:
            totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
            totalconImpuesto = [] 
            totalconImpuesto.append(('codigo', '2'))
            totalconImpuesto.append(('codigoPorcentaje', '7'))
            totalconImpuesto.append(('baseImponible', '{0:.2f}'.format(self.move_id.l10n_ec_base_tax_free)))
            totalconImpuesto.append(('valor', '0'))
            self.create_TreeElements(totalImpuesto, totalconImpuesto)
            taxes_zero = False
        # Esta parte analiza el no objeto de iva%
        if self.move_id.l10n_ec_base_not_subject_to_vat != 0:
            totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
            totalconImpuesto = [] 
            totalconImpuesto.append(('codigo', '2'))
            totalconImpuesto.append(('codigoPorcentaje', '6'))
            totalconImpuesto.append(('baseImponible', '{0:.2f}'.format(self.move_id.l10n_ec_base_not_subject_to_vat)))
            totalconImpuesto.append(('valor', '0'))
            self.create_TreeElements(totalImpuesto, totalconImpuesto)
            taxes_zero = False
        # Para emitir facturas con subtotal 0.0, como no hay impuestos entonces creamos un impuesto de 12% iva con 0.0 en el valor del IVA
        if taxes_zero:
            totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
            totalconImpuesto = []
            totalconImpuesto.append(('codigo', '2'))
            totalconImpuesto.append(('codigoPorcentaje', '2'))
            totalconImpuesto.append(('baseImponible', '0'))
            totalconImpuesto.append(('valor', '0'))
            self.create_TreeElements(totalImpuesto, totalconImpuesto)
        if type == 'out_invoice':
            pagos = infoFactura.find('pagos')
            # CREACION DE PAGOS
            for payment in self.move_id.l10n_ec_invoice_payment_method_ids:
                pago = self.create_SubElement(pagos, 'pago')
                pago_data = [
                    ('formaPago', payment.payment_method_id.code),
                    ('total', '{0:.2f}'.format(payment.amount)),
                    ('plazo', payment.days_payment_term),
                    ('unidadTiempo','dias')
                ]
                self.create_TreeElements(pago, pago_data)
        # DETALLES DE LA FACTURA
        detalles = etree.SubElement(factura, 'detalles')
        #remove sections and comments
        move_lines = self.l10n_ec_get_invoice_lines()
        for each in move_lines:
            detalle = self.create_SubElement(detalles, 'detalle')
            detalle_data = []
            main_code, secondary_code = self.l10n_ec_get_product_code(each)
            if main_code:
                if type == 'out_invoice':
                    detalle_data.append(('codigoPrincipal', main_code))
                elif type == 'out_refund':
                    detalle_data.append(('codigoInterno', main_code))
                elif type == 'in_invoice': #Liq de compras
                    detalle_data.append(('codigoPrincipal', main_code))
            detalle_data.append(('descripcion', get_SRI_normalized_text(each.name[:300])))
            detalle_data.append(('cantidad', '{0:.6f}'.format(each.quantity)))
            #TODO: usar algo similar al price_unit-final que deberia ser este l10n_latam_price_net o algo parecido
            detalle_data.append(('precioUnitario','{0:.6f}'.format(each.l10n_latam_price_unit))) #price_unit
            #TODO: agregar un campo funional total_discunt para tener el valor en dolares no %
            detalle_data.append(('descuento', '{0:.2f}'.format(each.l10n_ec_total_discount)))
            detalle_data.append(('precioTotalSinImpuesto', '{0:.2f}'.format(each.l10n_latam_price_subtotal)))
            if type == 'out_invoice':
                detalle_data.append(('detallesAdicionales', None))
            detalle_data.append(('impuestos', None))
            self.create_TreeElements(detalle, detalle_data)
            if type == 'out_invoice':
                detallesAdicionales = detalle.find('detallesAdicionales')
                self.create_SubElement(detallesAdicionales, 'detAdicional', attrib={'valor': each.product_id and each.product_uom_id.name or 'Unidad', 'nombre': 'uom'})
            impuestos = detalle.find('impuestos')
            for linetax in each.tax_ids:
                if linetax.tax_group_id.l10n_ec_type in ('ice', 'irbpnr'):
                    raise ValidationError(u'No se puede procesar el documento debido a que para ventas no se ha implementado los casos ICE o IRBPNR.')
                elif linetax.tax_group_id.l10n_ec_type in ('vat12', 'vat14', 'zero_vat', 'not_charged_vat', 'exempt_vat'):
                    impuesto = self.create_SubElement(impuestos, 'impuesto')
                    tax_data, valor, tarifa, codigoPorc = [], 0.0, 0, 0
                    valor, tarifa, codigoPorc = self._get_tax_value_amount(linetax, 12, each.move_id.l10n_ec_base_doce_iva, each.price_subtotal)
                    tax_data.append(('codigo', self._l10n_ec_map_tax_groups(linetax)))
                    tax_data.append(('codigoPorcentaje', codigoPorc)) 
                    tax_data.append(('tarifa', tarifa))
                    tax_data.append(('baseImponible', '{0:.2f}'.format(each.price_subtotal)))
                    tax_data.append(('valor', '{0:.2f}'.format(valor)))
                    self.create_TreeElements(impuesto, tax_data)
                else:
                    #ignoramos otros impuestos fuera del grupo contable de ecuador
                    pass
        if document_type.code == '41':
            reembolsos = self.create_SubElement(factura, 'reembolsos')
            for each in self.move_id.refund_ids:
                reembolsoDetalle = self.create_SubElement(reembolsos, 'reembolsoDetalle')
                detalle_data = []
                tipoProveedor, estabDocReembolso, ptoEmiDocReembolso = False, False, False
                secuencialDocReembolso = False
                #TODO: AL unir a las ramas ecommerce reestructurar el computo del tipoProveedor
                if each.partner_id.property_account_position_id and 'PERSONA NATURAL' in each.partner_id.property_account_position_id.name.upper():
                    tipoProveedor = '01'
                else:
                    tipoProveedor = '02'
                #se asume que el formulario obliga a que se cumpla el formato ###-###-##########
                number_refund = each.number.split('-')
                estabDocReembolso = number_refund[0]
                ptoEmiDocReembolso = number_refund[1]
                secuencialDocReembolso = number_refund[2]
                #TODO: AL unir a las ramas ecommerce reestructurar el computo del get_ident_type
                #TODO: se esta usando el metodo get_invoice_ident_type de la clase account.refund
                # debido a que el de auxiliar_function solo funciona con facturas, hay que unir estos metodos.
                detalle_data.append(('tipoIdentificacionProveedorReembolso', each.partner_id.get_invoice_ident_type()))
                detalle_data.append(('identificacionProveedorReembolso', each.partner_id.vat))
                detalle_data.append(('tipoProveedorReembolso', tipoProveedor))
                detalle_data.append(('codDocReembolso', '01'))
                detalle_data.append(('estabDocReembolso', estabDocReembolso))
                detalle_data.append(('ptoEmiDocReembolso', ptoEmiDocReembolso))
                detalle_data.append(('secuencialDocReembolso', secuencialDocReembolso))
                detalle_data.append(('fechaEmisionDocReembolso', each.creation_date.strftime('%d/%m/%Y')))
                detalle_data.append(('numeroautorizacionDocReemb', each.authorization))
                self.create_TreeElements(reembolsoDetalle, detalle_data)
                detalleImpuestos = self.create_SubElement(reembolsoDetalle, 'detalleImpuestos')
                detalleImpuesto_data = []
                if each.base_vat_no0:
                    detalleImpuesto = self.create_SubElement(detalleImpuestos, 'detalleImpuesto')
                    detalleImpuesto_data.append(('codigo', '2'))
                    detalleImpuesto_data.append(('codigoPorcentaje', '2'))
                    detalleImpuesto_data.append(('tarifa', '12'))
                    detalleImpuesto_data.append(('baseImponibleReembolso', '{0:.2f}'.format(each.base_vat_no0)))
                    detalleImpuesto_data.append(('impuestoReembolso', '{0:.2f}'.format(each.vat_amount_no0)))
                    self.create_TreeElements(detalleImpuesto, detalleImpuesto_data)
                    detalleImpuesto_data = []
                if each.base_vat_0:
                    detalleImpuesto = self.create_SubElement(detalleImpuestos, 'detalleImpuesto')
                    detalleImpuesto_data.append(('codigo', '2'))
                    detalleImpuesto_data.append(('codigoPorcentaje', '0'))
                    detalleImpuesto_data.append(('tarifa', '0'))
                    base = each.base_tax_free + each.base_vat_0 + each.no_vat_amount
                    detalleImpuesto_data.append(('baseImponibleReembolso', '{0:.2f}'.format(base)))
                    detalleImpuesto_data.append(('impuestoReembolso', '0.00'))
                    self.create_TreeElements(detalleImpuesto, detalleImpuesto_data)
                    detalleImpuesto_data = []
        infoAdicional = self.create_SubElement(factura, 'infoAdicional')
        if get_invoice_partner_data['invoice_email']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'email'}, text=get_invoice_partner_data['invoice_email'])
        if self.move_id.user_id.name: 
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'vendedor'}, text=self.move_id.user_id.name)
        if self.move_id.narration:
            narration = BeautifulSoup(self.move_id.narration, 'lxml').get_text()
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'novedades'}, text=narration.replace('\n', ' '))
        if self.move_id.invoice_origin:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'pedido'}, text=self.move_id.invoice_origin)
        if get_invoice_partner_data['invoice_address']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'direccion'}, text=get_invoice_partner_data['invoice_address'])
        if get_invoice_partner_data['invoice_phone']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'telefono'}, text=get_invoice_partner_data['invoice_phone'])
        if self.move_id.invoice_payment_term_id.name:
           self. create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'formaPago'}, text=self.move_id.invoice_payment_term_id.name)
        if type != 'in_invoice':
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'totalLetras'}, text=l10n_ec_amount_to_words(self.move_id.amount_total))
        else:
            if document_type.code in ('03','41'):
                self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'totalLetras'}, text=l10n_ec_amount_to_words(self.move_id.l10n_ec_total_with_tax))
        return factura
    
    def l10n_ec_get_invoice_lines(self):
        return self.move_id.invoice_line_ids.filtered(lambda x:x.display_type not in ['line_section','line_note'])
    
    def l10n_ec_get_product_code(self, line):
        return line.product_id.l10n_ec_get_product_codes()
    
    def create_TreeElements(self, _parent,_tags_text):
        for tag, text in _tags_text:
            self.create_SubElement(_parent, tag, text=text)
        return True
    
    def create_SubElement(self, _parent, _tag, attrib={}, text=None, nsmap=None, **_extra):
        result = etree.SubElement(_parent, _tag, attrib,nsmap, **_extra)
        result.text = (text if not text is None and isinstance(text, str) else not text is None and str(text)) or None
        return result

    def _get_additional_info(self):
        self.ensure_one()
        additional_info = []
        get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
        if get_invoice_partner_data['invoice_email']:
            additional_info.append('Email: %s' % get_invoice_partner_data['invoice_email'])
        if self.move_id.l10n_ec_printer_id.name[:3]:
            additional_info.append('Vendedor: %s' % self.move_id.user_id.name)
        if self.move_id.narration:
            narration = BeautifulSoup(self.move_id.narration, 'lxml').get_text()
            additional_info.append('Novedades: %s' % narration.replace('\n', ' '))
        if self.move_id.company_id.l10n_ec_regime == 'rimpe':
            additional_info.append('Régimen: Contribuyente Régimen RIMPE')
        if self.move_id.invoice_origin:
            additional_info.append('Pedido: %s' % self.move_id.invoice_origin)
        if get_invoice_partner_data['invoice_address']:
            additional_info.append('Direccion: %s' % get_invoice_partner_data['invoice_address'])
        if get_invoice_partner_data['invoice_phone']:
            additional_info.append('Telefono: %s' % get_invoice_partner_data['invoice_phone'])
        if self.move_id.invoice_payment_term_id.name:
            additional_info.append('Forma de Pago: %s' % self.move_id.invoice_payment_term_id.name)
        if self.move_id.move_type != 'in_invoice':
            additional_info.append('Monto Letras: %s' % l10n_ec_amount_to_words(self.move_id.amount_total))
        else:
            if self.move_id.l10n_latam_document_type_id.code in ('03','41'):
                additional_info.append('Monto Letras: %s' % l10n_ec_amount_to_words(self.move_id.l10n_ec_total_with_tax))
        return additional_info

    def _l10n_ec_map_tax_groups(self, tax_id):
        #Maps different tax types (aka groups) to codes for electronic invoicing
        if tax_id.tax_group_id.l10n_ec_type in _IVA_CODES:
            return 2
        elif tax_id.tax_group_id.l10n_ec_type in _ICE_CODES:
            return 3
        elif tax_id.tax_group_id.l10n_ec_type in _IRBPNR_CODES:
            return 5
        else: 
            raise ValidationError(u'No se ha implementado ningún código en los documentos '
                                  u'electrónicos para este tipo de impuestos.')
    
    def _get_tax_value_amount(self, tax_id, tax_amount, amount_graba, price_subtotal):
        #Gets the VAT tax code and monetary value for electronic invoicing
        code = self._l10n_ec_map_vat_subtaxes(tax_id, tax_amount, amount_graba)
        value = 0 #TODO V15, use the functional fields in account.move.line
        value_tax = 0
        if code == 3:
            value = price_subtotal * 0.14
            value_tax = 14
        elif code == 2:
            value = price_subtotal * 0.12
            value_tax = 12
        elif code in (0, 6, 7):
            # Estos codigos con iva 0, exento, y no objeto de iva por eso el valos es 0
            value = price_subtotal * 0.0
            value_tax = 0
        return value, value_tax, code
    
    def _l10n_ec_map_vat_subtaxes(self, tax_id, tax_amount, amount_graba):
        #Maps speceficit vat types to codes for electronic invoicing
        if tax_id.tax_group_id.l10n_ec_type == 'vat12':
            code = 2
        elif tax_id.tax_group_id.l10n_ec_type == 'vat14':
            code = 3
        elif tax_id.tax_group_id.l10n_ec_type == 'zero_vat':
            code = 0
        elif tax_id.tax_group_id.l10n_ec_type == 'not_charged_vat':
            code = 6
        elif tax_id.tax_group_id.l10n_ec_type == 'exempt_vat':
            code = 7
        else:
            raise # TODO v15: Implementar todos los otros casos que no son para el IVA ej. ICE, IRBPNR
        return code
    
    def _l10n_ec_sign_digital_xml(self, access_key, cert_encripted, password_p12, draft_electronic_document_in_xml, path_temp='/tmp/'):
        #To be redefined in module l10n_ec_digital_signature
        raise ValidationError("Please install module l10n_ec_digital_signature by Trescloud to sign electronic documents in Ecuador") 

    def _l10n_ec_upload_electronic_document(self):
        # Se realiza la firma del documento
        signed_xml = self._l10n_ec_sign_digital_xml(self.l10n_ec_access_key,
                                           self.sudo().move_id.company_id.l10n_ec_digital_cert_id.cert_encripted,
                                           self.sudo().move_id.company_id.l10n_ec_digital_cert_id.password_p12,
                                           self.l10n_ec_request_xml_file)
        client = self._l10n_ec_open_connection_sri(mode='reception')
        reply = client.service.validarComprobante(signed_xml)
        if reply.comprobantes and reply.comprobantes.comprobante[0].mensajes:
            raise ValidationError(str(reply.comprobantes.comprobante[0].mensajes.mensaje))
        
    def _l10n_ec_download_electronic_document_reply(self):
        #Consulta el estado del doc electronico al servidor externo y procesa la respuesta
        client = self._l10n_ec_open_connection_sri()
        access_key = self.l10n_ec_access_key
        #access_key = "3108202001179236683600120010020000019670000000315" #sample authorized code
        #access_key = "0806202007179126948900120010110000428902912200518" #sample voided code
        state = 'not_yet_ready'
        response = client.service.autorizacionComprobante(access_key)
        if response.autorizaciones:
            if response.autorizaciones.autorizacion[0].estado == 'AUTORIZADO':
                state = 'sent'
            elif response.autorizaciones.autorizacion[0].estado == 'NO AUTORIZADO':
                state = 'rejected'
        elif response.numeroComprobantes == '0':
            state = 'non-existent'
        elif int(response.numeroComprobantes) > 0:
            #Cuando el documento ya existe en el SRI, aunque con errores
            raise ValidationError(str(response.autorizaciones.autorizacion[0].mensajes))
        return state, response
    
    def _l10n_ec_open_connection_sri(self, mode='autorization'):
        '''
        Nos conectamos al sistema del S.R.I. de documentos electronicos
        Este paso depende de que se requiere hacer ya que el SRI expone 2 servicios
        uno para enviar los documentos y otro para verificar su estado.
        mode: permite indicar en que modo se realizara la conexion, 
              autorization -> conecta al WS que permite consultar el estado de los documentos
              reception -> conecta al WS que permite enviar documentos    
        '''
        environment_type = self.move_id.company_id.l10n_ec_environment_type
        if environment_type == '0': #SRI Test Environment
            raise ValidationError('Error de programación, se iba a intentar una conexión al SRI en modo demo, no permitido')
        elif environment_type == '1': #SRI Test Environment
            if mode == 'autorization':
                WSDL_URL = ELECTRONIC_SRI_WSDL_AUTORIZATION_TEST_OFFLINE
            elif mode == 'reception':
                WSDL_URL = ELECTRONIC_SRI_WSDL_RECEPTION_TEST_OFFLINE
        elif environment_type == '2': #SRI Production Environment
            if mode == 'autorization':
                WSDL_URL = ELECTRONIC_SRI_WSDL_AUTORIZATION_OFFLINE
            elif mode == 'reception':
                WSDL_URL = ELECTRONIC_SRI_WSDL_RECEPTION_OFFLINE
        client = Client(WSDL_URL)
        #client = Client(WSDL_URL,retxml=True,prettyxml=True)
        return client
    
    l10n_ec_access_key = fields.Char(
        string='Access Key', 
        readonly=True,
        help='Unique code to identify this document, is generated based on date, vat code, serial number, and other related fields',
        ) 
    l10n_ec_request_xml_file = fields.Binary(
        string='Peticion XML',
        attachment = True, #por default los attachment se guardan en el filestore
        help='El archivo XML enviado al proveedor de documentos electronicos, guardado para depuracion',
        )
    l10n_ec_request_xml_file_name = fields.Char(
        string='Request File Name',
        size=64,
        help='El nombre del archivo XML enviado al proveedor de documentos electronicos, guardado para depuracion',
        ) #TODO V15: Removerlo? desde Odoo 13 el usuario no accede a la tabla de docs electronicos
    

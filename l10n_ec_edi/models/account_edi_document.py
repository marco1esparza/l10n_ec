# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from lxml import etree
import base64

from odoo.addons.l10n_ec_edi.models.common_methods import get_SRI_normalized_text, clean_xml, validate_xml_vs_xsd, XSD_SRI_110_FACTURA
from odoo.addons.l10n_ec_edi.models.amount_to_words import amount_to_words_es


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'
    
    def get_access_key(self):
        '''
        Genera la clave de acceso del documento electronico
        Para esta revision en account.invoice se envia el mismo
        tipo de documento para evitar errores.
        '''
        self.ensure_one()
        if not self.document_id:
            return False
        related_document = self.document_id
        # cargamos los datos generales
        data_model = related_document._name
        filler = self.filler_number
        # Dato para el portal web
        if data_model == 'account.invoice':
            date = related_document.invoice_date
            document_type = related_document.type
            code_document_type = str(
                related_document.document_invoice_type_id.code
            )
            if document_type in ('out_invoice','out_refund'):
                if code_document_type in ('18', '41'):
                    # Factura de venta y reembolso se mapea con codigo '01'
                    code_document_type = '01'
            elif document_type in ('in_invoice',):
                if code_document_type in ('03', '41'):
                    # Factura de venta y reembolso se mapea con codigo '01'
                    code_document_type = '03'
            document_type_id = related_document.document_invoice_type_id.id
            serie = related_document.l10n_latam_document_number
        else:
            raise ValidationError(
                u'No se ha implementado documentos electronicos para '
                u'este modelo de datos'
            )
        # Datos para el portal web
        vat_emmiter = _get_clear_vat(
            str(related_document.company_id.partner_id.vat)
        )

        cadena = self.gen_access_key(
            filler, date, code_document_type, serie,
            related_document.company_id.partner_id.vat,
            self.environment_type,
        )
        # agregado campos que se obtienen desde el access
        # key ademas de la clave
        self.write({
            'access_key': cadena,
            'name': cadena,
            'document_date': date,
            'l10n_latam_document_number': serie,
            'document_type_id': document_type_id,
            'commercial_partner_id': self.document_id.partner_id.commercial_partner_id.id,
            'vat_emmiter': vat_emmiter
        })
        return cadena
    
    @api.model
    def gen_access_key(self, filler_number, date, code_document_type,
                       l10n_latam_document_number, company_vat, environment_type):
        '''
        Genera la clave de acceso del documento electronico
        '''

        # cargamos los datos generales
        cadena = ''
        fill = 8
        cod_number = '0' * (fill - len(str(filler_number))) + \
                     str(filler_number)
        type_emm = '1'
        vat_emmiter = _get_clear_vat(company_vat)
        '''first value date'''
        fdate = date.find('-')
        fdateo = date.find('/')
        if fdate != -1:
            date = date.split('-')
            # si es un datetime se remueven las horas minutos y segundos
            cadena = '' + date[2][:2] + date[1] + date[0]
        elif fdateo != -1:
            date = date.split('/')
            # si es un datetime se remueven las horas minutos y segundos
            cadena = '' + date[2][:2] + date[1] + date[0]
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
                _(u'El numero de documento %s presenta errores: %s') % (
                    serie, detail
                )
            )
        '''seven value numeric code '''
        cadena += cod_number
        '''eigth value tipo emision siempre sera 1 '''
        cadena += type_emm
        number_c = int(cadena)
        digit_ver = self.GenerateModulus11(number_c)
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
    
    def GenerateModulus11(self, Numero):
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

    def attempt_electronic_document(self):
        '''
        Intenta ejecutar el proceso completo de generar el documento electronico
        '''
        if self.state in ('sent'):
            raise ValidationError("No se puede enviar al SRI documentos previamente enviados: Documento %s" % str(self.l10n_ec_access_key or self.id))
        if self.state in ('canceled'):
            raise ValidationError("No se puede enviar al SRI documentos previamente anulados: Documento %s \n"
                                  "En su lugar debe crear un nuevo documento electrónico" % str(self.l10n_ec_access_key or self.id)) 
        if self.state in ('to_send'):
            self.generate_request_xml_file()
        #decidimos si nos conectamos al servidor o si lo procesamos localmente
        connect_to_server = self.env.context.get('connect_to_server', False) #contexto que fuerza conexion desde cron o boton
        type_document = self.document_id._name
        if not connect_to_server:
            #Sin enviar al SRI autorizaremos el documento de forma OFFLINE
            #Nota: El cron y el boton si se conectan al SRI pues tienen el contexto "connect_to_server"
            self.update_filler_number_and_access_key()
            self.state = 'sri_authorized_offline'
            self.validation_result_message = "Autorizado Offline"
            self.set_authorizations(self.l10n_ec_access_key)
            return
        if self.state in ELECTRONIC_STATES_DRAFT + ELECTRONIC_STATES_OFFLINE:
            self.update_filler_number_and_access_key()
            #el siguiente metodo debe invocarse al final pues puede ocurir erroes en la comunicación
            self.upload_electronic_document_request()
            #TODO: marco el momento en que fue enviado el documento (reutilizo la fecha de reintento)(Aqui se debe guardar el secuencial consumido en el documento, especialmente facturas)
            self.send_document_datetime = today
            #TODO podriamos revisar si hay aprobacion inmediata y escribir el estado aprobado
            #pero no forma parte del primer sprint, ademas con offline no es perceptible por el usuario  
        elif self.state in ELECTRONIC_STATES_SENT:
            #en estos casos estamos a la espera de la respuesta del SRI
            #consultamos y actualizamos el estado
            self.download_electronic_document_reply()
            
    def generate_request_xml_file(self):
        '''
        Escribe el archivo xml en el campo designado para ello
        '''
        for document in self:
            document.l10n_ec_request_xml_file_name = document.move_id.name + '_draft.xml'
            xml_string = document.generate_request_xml_string()
            document.l10n_ec_request_xml_file = base64.encodestring(xml_string)

    @api.model
    def generate_request_xml_string(self):
        '''        
        Retorna como string el contenido del reporte xml de documento electronico 
        '''
        context = self.env.context.copy()
        if not context.get('lang',False) or not context.get('tz', False) or not context.get('uid', False):  
            #TODO: Investigar el error, a veces el context llega incompleto y el reporte no se puede generar, parece ser cuando se viene desde el cron
            user = self.env.user
            if not context.get('lang', False):
                context.update({'lang': user.lang})
            if not context.get('tz', False):
                context.update({'tz': user.tz})
            if not context.get('uid', False):
                context.update({'uid': user.id})
        assert len(self) == 1, u'Esta opción sólo debe utilizarse para un solo identificador a la vez.'
        #generamos y validamos el documento
        etree_content = self.create_electronic_document()
        xml_content = clean_xml(etree_content, context=context)
        try: #validamos el XML contra el XSD
            if self.move_id.type in ('out_invoice') and self.move_id.l10n_latam_document_type_id.code in ['18','01','41']:
                validate_xml_vs_xsd(xml_content, XSD_SRI_110_FACTURA)
        except ValueError: 
            raise UserError(u'No se ha enviado al servidor: ¿quiza los datos estan mal llenados?:' + ValueError[1])        
        return xml_content
    
    @api.model
    def create_electronic_document(self):
        # INICIO CREACION DE FACTURA
        type = self.move_id.type
        document_type = self.move_id.l10n_latam_document_type_id
        if type == 'out_invoice':
            if document_type.code in ('18', '41'):
                factura = etree.Element('factura', {'id': 'comprobante', 'version': '1.1.0'})
#             elif document_type.code == '05':
#                 return self._getNotaDebito()
#         elif type == 'out_refund':
#             factura = etree.Element('notaCredito', {'id': 'comprobante', 'version': '1.1.0'})
#         elif type == 'in_invoice':
#             if document_type.code in ('03','41'):
#                 factura = etree.Element('liquidacionCompra', {'id': 'comprobante', 'version': '1.1.0'})
        # CREACION INFO TRIBUTARIA
        infoTributaria = etree.SubElement(factura, 'infoTributaria')
        infoTribElements = [
            ('ambiente', self.move_id.company_id.l10n_ec_environment_type),
            ('tipoEmision', '1'),
            ('razonSocial', self.move_id.company_id.l10n_ec_legal_name)
        ]
        if self.move_id.company_id.partner_id.l10n_commercial_name:
            infoTribElements.append(('nombreComercial', self.move_id.company_id.partner_id.l10n_commercial_name))
        infoTribElements.extend([
            ('ruc', self.move_id.company_id.partner_id.vat),
            ('claveAcceso', self.l10n_ec_access_key)
        ])
        if type == 'out_invoice':
            infoTribElements.append(('codDoc', '01'))
#         elif type == 'out_refund':
#             infoTribElements.append(('codDoc',document_type.code))
#         elif type == 'in_invoice':
#             if document_type.code in ('03','41'):
#                 infoTribElements.append(('codDoc', '03'))
        infoTribElements.extend([
            ('estab', self.move_id.l10n_latam_document_number[0:3]),
            ('ptoEmi', self.move_id.l10n_latam_document_number[4:7]),
            ('secuencial', self.move_id.l10n_latam_document_number[8:]),
            ('dirMatriz', self.move_id.company_id.street)
        ])
        self.create_TreeElements(infoTributaria, infoTribElements)
        # CREACION INFO FACTURA
        if type == 'out_invoice':
            infoFactura = etree.SubElement(factura, 'infoFactura')
#         elif type == 'out_refund':
#             infoFactura = etree.SubElement(factura, 'infoNotaCredito')
#         elif type == 'in_invoice':
#             if document_type.code in ('03', '41'):
#                 infoFactura = etree.SubElement(factura, 'infoLiquidacionCompra')
        infoFactElements = [
            ('fechaEmision', datetime.strftime(self.move_id.invoice_date,'%d/%m/%Y')),
            ('dirEstablecimiento', self.move_id.l10n_ec_printer_id.l10n_ec_printer_point_address)
        ]
        if type == 'out_invoice':
            if self.move_id.company_id.l10n_ec_special_contributor_number:
                infoFactElements.append(('contribuyenteEspecial', self.move_id.company_id.l10n_ec_special_contributor_number))
            get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
            infoFactElements.extend([
                ('obligadoContabilidad', 'SI' if self.move_id.company_id.l10n_ec_forced_accounting else 'NO'),
                ('tipoIdentificacionComprador', self.move_id.partner_id.get_invoice_ident_type()),
                #TODO: cuando se arregle el metodo get_SRI_normalized_text borrar la sig linea y descomentar la otra
                ('razonSocialComprador', get_invoice_partner_data['invoice_name']),
                #('razonSocialComprador', get_SRI_normalized_text(get_invoice_partner_data['invoice_name'])),
                ('identificacionComprador', get_invoice_partner_data['invoice_vat']),
                ('totalSinImpuestos', self.move_id.amount_untaxed),
                ('totalDescuento', self.move_id.l10n_ec_total_discount)#TODO: estan saliendo con muchos decimales
            ])
#             if document_type.code == '41':
#                 amount_total, totalComprobantesReembolso, totalImpuestoReembolso = 0, 0, 0
#                 for refund_line in self.account_refund_client_ids:
#                     amount_total += refund_line.total
#                     totalComprobantesReembolso += refund_line.base_tax_free + refund_line.base_vat_0 + \
#                         refund_line.no_vat_amount + refund_line.base_vat_no0
#                     totalImpuestoReembolso += refund_line.vat_amount_no0
#                 infoFactElements.extend([
#                     ('codDocReembolso', '41'),
#                     ('totalComprobantesReembolso', amount_total),
#                     ('totalBaseImponibleReembolso', totalComprobantesReembolso),
#                     ('totalImpuestoReembolso', totalImpuestoReembolso),
#                 ])
#         elif type == 'out_refund':
#             infoFactElements.extend([
#                 ('tipoIdentificacionComprador', get_invoice_ident_type(self)),
#                 ('razonSocialComprador', self.invoice_name),
#                 ('identificacionComprador', get_identification(self.invoice_vat))
#             ])
#             if self.company_id.special_tax_contributor_number:
#                 infoFactElements.append(('contribuyenteEspecial', self.company_id.special_tax_contributor_number))   
#             infoFactElements.extend([
#                 ('obligadoContabilidad', 'SI' if self.company_id.forced_accounting else 'NO'),
#                 ('codDocModificado', '01'),
#                 ('numDocModificado', self.invoice_rectification_id.l10n_latam_document_number),
#                 ('fechaEmisionDocSustento', datetime.strptime(self.invoice_rectification_id.invoice_date,'%Y-%m-%d').strftime('%d/%m/%Y')),
#                 ('totalSinImpuestos', self.amount_untaxed),
#                 ('valorModificacion', self.amount_total),
#                 ('moneda', 'DOLAR')
#             ])
#         elif type == 'in_invoice':
#             if document_type.code in ('03','41'):
#                 if self.company_id.special_tax_contributor_number:
#                     infoFactElements.append(('contribuyenteEspecial', self.company_id.special_tax_contributor_number))
#                 infoFactElements.extend([
#                     ('obligadoContabilidad', 'SI' if self.company_id.forced_accounting else 'NO'),
#                     ('tipoIdentificacionProveedor', get_invoice_ident_type(self)),
#                     ('razonSocialProveedor', self.invoice_name),
#                     ('identificacionProveedor', get_identification(self.invoice_vat)),
#                     ('totalSinImpuestos', self.amount_untaxed),
#                     ('totalDescuento', self.total_discount),
#                 ])
#                 if document_type.code == '41':
#                     amount_total, totalComprobantesReembolso, totalImpuestoReembolso = 0, 0, 0
#                     for refund_line in self.account_refund_client_ids:
#                         amount_total += refund_line.total
#                         totalComprobantesReembolso += refund_line.base_tax_free + refund_line.base_vat_0 + \
#                             refund_line.no_vat_amount + refund_line.base_vat_no0
#                         totalImpuestoReembolso += refund_line.vat_amount_no0
#                     infoFactElements.extend([
#                         ('codDocReembolso', '41'),
#                         ('totalComprobantesReembolso', amount_total),
#                         ('totalBaseImponibleReembolso', totalComprobantesReembolso),
#                         ('totalImpuestoReembolso', totalImpuestoReembolso),
#                     ])
        infoFactElements.append(('totalConImpuestos', None))
        if type == 'out_invoice':
            infoFactElements.extend([
                ('propina', '0.00'),
                ('importeTotal', '{0:.2f}'.format(self.move_id.amount_total)),
                ('pagos', None),
            ])
#         elif type == 'out_refund':
#             infoFactElements.append(('motivo', self.name))
#         if type == 'in_invoice':
#             if document_type.code in ('03','41'):
#                 infoFactElements.extend([
#                     ('importeTotal', '{0:.2f}'.format(self.total_with_tax)),
#                 ])
        self.create_TreeElements(infoFactura, infoFactElements)
        # CREACION DE TOTAL CON IMPUESTOS
        # Para la creacion de la seccion de impuestos para facturas en 0, debemos revisar si ya ha 
        # sido creado un impuesto, de otro modo la factura debe tener algun valor
        totalConImpuestos = infoFactura.find('totalConImpuestos')
        taxes_zero = True
        #TODO:implementar todo esto
#         # Esta parte analiza el 12% y 14%
#         if self.base_doce_iva != 0:
#             totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
#             totalconImpuesto = [] 
#             totalconImpuesto.append(('codigo', '2')) #tabla 16
#             #el sri permite facturas simultaneas con base 12% y base14%
#             #pero nuestro sistema solo permite el uno o el otro, por eso el if
#             #TODO v11 hacer un campo funcional que abstraiga esta logica en el pie de la factura 
#             vat_percentages = []
#             for tax_line in self.tax_line_ids:
#                 if tax_line.tax_id.type_ec != 'vat':
#                     continue #pasamos al siguiente impuesto, solo me interesan los de iva
#                 vat_percentages.append(tax_line.tax_id.amount)
#             vat_percentages = list(set(vat_percentages)) #removemos duplicados
#             if len(vat_percentages) != 1:
#                 raise UserError('No se puede determinar si es IVA 12% o IVA 14%')
#             if vat_percentages[0] == 12.0:
#                 vcodigoPorcentaje = '2'
#             elif vat_percentages[0] == 14.0:
#                 vcodigoPorcentaje = '3'
#             totalconImpuesto.append(('codigoPorcentaje', vcodigoPorcentaje))
#             totalconImpuesto.append(('baseImponible', self.base_doce_iva))
#             totalconImpuesto.append(('valor', self.vat_doce_subtotal))
#             self.create_TreeElements(totalImpuesto, totalconImpuesto)
#             taxes_zero = False
#         # Esta parte analiza el IVA 0%
#         if self.base_cero_iva != 0:
#             totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
#             totalconImpuesto = [] 
#             totalconImpuesto.append(('codigo', '2'))
#             totalconImpuesto.append(('codigoPorcentaje', '0'))
#             totalconImpuesto.append(('baseImponible', self.base_cero_iva))
#             totalconImpuesto.append(('valor', '0'))
#             self.create_TreeElements(totalImpuesto, totalconImpuesto)
#             taxes_zero = False
#         # Esta parte analiza el iva exento 
#         if self.base_tax_free != 0:
#             totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
#             totalconImpuesto = [] 
#             totalconImpuesto.append(('codigo', '2'))
#             totalconImpuesto.append(('codigoPorcentaje', '7'))
#             totalconImpuesto.append(('baseImponible', self.base_tax_free))
#             totalconImpuesto.append(('valor', '0'))
#             self.create_TreeElements(totalImpuesto, totalconImpuesto)
#             taxes_zero = False
#         # Esta parte analiza el no objeto de iva%
#         if self.base_not_subject_to_vat != 0:
#             totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
#             totalconImpuesto = [] 
#             totalconImpuesto.append(('codigo', '2'))
#             totalconImpuesto.append(('codigoPorcentaje', '6'))
#             totalconImpuesto.append(('baseImponible', self.base_not_subject_to_vat))
#             totalconImpuesto.append(('valor', '0'))
#             self.create_TreeElements(totalImpuesto, totalconImpuesto)
#             taxes_zero = False
#         # Para emitir facturas con subtotal 0.0, como no hay impuestos entonces creamos un impuesto de 12% iva con 0.0 en el valor del IVA
#         if taxes_zero:
#             totalImpuesto = self.create_SubElement(totalConImpuestos, 'totalImpuesto')
#             totalconImpuesto = []
#             totalconImpuesto.append(('codigo', '2'))
#             totalconImpuesto.append(('codigoPorcentaje', '2'))
#             totalconImpuesto.append(('baseImponible', '0'))
#             totalconImpuesto.append(('valor', '0'))
#             self.create_TreeElements(totalImpuesto, totalconImpuesto)
#         if type == 'out_invoice':
#             pagos = infoFactura.find('pagos')
#             # CREACION DE PAGOS
#             for payment in self.move_id.l10n_ec_invoice_payment_method_ids:
#                 pago = self.create_SubElement(pagos, 'pago')
#                 pago_data = [
#                     ('formaPago', payment.l10n_ec_payment_method_id.code),
#                     ('total', '{0:.2f}'.format(payment.l10n_ec_amount)),
#                     ('plazo', payment.l10n_ec_days_payment_term),
#                     ('unidadTiempo','dias')
#                 ]
#                 self.create_TreeElements(pago, pago_data)
        # DETALLES DE LA FACTURA
        detalles = etree.SubElement(factura, 'detalles')
        for each in self.move_id.invoice_line_ids:
            detalle = self.create_SubElement(detalles, 'detalle')
            detalle_data = []
            if each.product_id.get_product_code():
                if type == 'out_invoice':
                    detalle_data = self.getCodigoPrincipal(detalle_data, each)
#                 elif type == 'out_refund':
#                     detalle_data.append(('codigoInterno', each.product_id.get_product_code()[:25]))
            detalle_data.append(('descripcion', each.name[:300]))
            detalle_data.append(('cantidad', each.quantity))
            #TODO: usar algo similar al price_unit-final que deberia ser este l10n_latam_price_net o algo parecido
            detalle_data.append(('precioUnitario',each.l10n_latam_price_net)) #price_unit
            #TODO: agregar un campo funional total_discunt para tener el valor en dolares no %
            detalle_data.append(('descuento', each.l10n_ec_total_discount))
            detalle_data.append(('precioTotalSinImpuesto', each.l10n_latam_price_subtotal))
            if type == 'out_invoice':
                detalle_data.append(('detallesAdicionales', None))
            detalle_data.append(('impuestos', None))
            self.create_TreeElements(detalle, detalle_data)
            if type == 'out_invoice':
                detallesAdicionales = detalle.find('detallesAdicionales')
                self.create_SubElement(detallesAdicionales, 'detAdicional', attrib={'valor': each.product_uom_id.name, 'nombre': 'uom'})
            impuestos = detalle.find('impuestos')
#             #TODO: implememtar la siguiente seccion de impuesto
#             for linetax in each.invoice_line_tax_ids:
#                 if linetax.type_ec in ('vat', 'zero_vat', 'not_charged_vat', 'exempt_vat', 'ice', 'irbpnr'):
#                     impuesto = self.create_SubElement(impuestos, 'impuesto')
#                     tax_data, valor, tarifa, codigoPorc = [], 0.0, 0, 0
#                     try:
#                         valor, tarifa, codigoPorc = self._get_tax_value_amount(linetax, 12, each.invoice_id.base_doce_iva, each.price_subtotal)
#                     except:
#                         raise ValidationError(u'No se puede procesar el documento debido a que no se ha implementado los casos ICE o IRBPNR.')
#                     tax_data.append(('codigo', self._get_code(linetax)))
#                     tax_data.append(('codigoPorcentaje', codigoPorc)) 
#                     tax_data.append(('tarifa', tarifa))
#                     tax_data.append(('baseImponible', each.price_subtotal))
#                     tax_data.append(('valor', '{0:.2f}'.format(valor)))
#                     self.create_TreeElements(impuesto, tax_data)
#         if document_type.code == '41':
#             reembolsos = self.create_SubElement(factura, 'reembolsos')
#             for each in self.account_refund_client_ids:
#                 reembolsoDetalle = self.create_SubElement(reembolsos, 'reembolsoDetalle')
#                 detalle_data = []
#                 tipoProveedor, estabDocReembolso, ptoEmiDocReembolso = False, False, False
#                 secuencialDocReembolso = False
#                 #TODO: AL unir a las ramas ecommerce reestructurar el computo del tipoProveedor
#                 if each.partner_id.property_account_position_id and 'PERSONA NATURAL' in each.partner_id.property_account_position_id.name.upper():
#                     tipoProveedor = '01'
#                 else:
#                     tipoProveedor = '02'
#                 #se asume que el formulario obliga a que se cumpla el formato ###-###-##########
#                 number_refund = each.number.split('-')
#                 estabDocReembolso = number_refund[0]
#                 ptoEmiDocReembolso = number_refund[1]
#                 secuencialDocReembolso = number_refund[2]
#                 #TODO: AL unir a las ramas ecommerce reestructurar el computo del get_ident_type
#                 #TODO: se esta usando el metodo get_invoice_ident_type de la clase account.refund
#                 # debido a que el de auxiliar_function solo funciona con facturas, hay que unir estos metodos.
#                 detalle_data.append(('tipoIdentificacionProveedorReembolso', each.get_invoice_ident_type()))
#                 detalle_data.append(('identificacionProveedorReembolso', get_identification(each.partner_id.vat)))
#                 detalle_data.append(('tipoProveedorReembolso', tipoProveedor))
#                 detalle_data.append(('codDocReembolso', '01'))
#                 detalle_data.append(('estabDocReembolso', estabDocReembolso))
#                 detalle_data.append(('ptoEmiDocReembolso', ptoEmiDocReembolso))
#                 detalle_data.append(('secuencialDocReembolso', secuencialDocReembolso))
#                 detalle_data.append(('fechaEmisionDocReembolso', datetime.strptime(each.creation_date,'%Y-%m-%d').strftime('%d/%m/%Y')))
#                 detalle_data.append(('numeroautorizacionDocReemb', each.authorizations_id.name))
#                 self.create_TreeElements(reembolsoDetalle, detalle_data)
#                 detalleImpuestos = self.create_SubElement(reembolsoDetalle, 'detalleImpuestos')
#                 detalleImpuesto_data = []
#                 if each.base_vat_no0:
#                     detalleImpuesto = self.create_SubElement(detalleImpuestos, 'detalleImpuesto')
#                     detalleImpuesto_data.append(('codigo', '2'))
#                     detalleImpuesto_data.append(('codigoPorcentaje', '2'))
#                     detalleImpuesto_data.append(('tarifa', '12'))
#                     detalleImpuesto_data.append(('baseImponibleReembolso', each.base_vat_no0))
#                     detalleImpuesto_data.append(('impuestoReembolso', each.vat_amount_no0))
#                     self.create_TreeElements(detalleImpuesto, detalleImpuesto_data)
#                     detalleImpuesto_data = []
#                 if each.base_vat_0:
#                     detalleImpuesto = self.create_SubElement(detalleImpuestos, 'detalleImpuesto')
#                     detalleImpuesto_data.append(('codigo', '2'))
#                     detalleImpuesto_data.append(('codigoPorcentaje', '0'))
#                     detalleImpuesto_data.append(('tarifa', '0'))
#                     detalleImpuesto_data.append(('baseImponibleReembolso', each.base_tax_free + each.base_vat_0 + each.no_vat_amount))
#                     detalleImpuesto_data.append(('impuestoReembolso', '0.00'))
#                     self.create_TreeElements(detalleImpuesto, detalleImpuesto_data)
#                     detalleImpuesto_data = []
        infoAdicional = self.create_SubElement(factura, 'infoAdicional')
        if get_invoice_partner_data['invoice_email']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'email'}, text=get_invoice_partner_data['invoice_email'])
        if self.move_id.l10n_ec_printer_id.l10n_ec_name[:3]: 
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'tienda'}, text=self.move_id.l10n_ec_printer_id.l10n_ec_name[:3])
        if self.move_id.user_id.name: 
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'vendedor'}, text=self.move_id.user_id.name)
        if self.move_id.narration:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'novedades'}, text= self.move_id.narration.replace('\n', ' '))
        if self.move_id.invoice_origin:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'pedido'}, text=self.move_id.invoice_origin)
        if get_invoice_partner_data['invoice_address']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'direccion'}, text=get_invoice_partner_data['invoice_address'])
        if get_invoice_partner_data['invoice_phone']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'telefono'}, text=get_invoice_partner_data['invoice_phone'])
        if self.move_id.invoice_payment_term_id.name:
           self. create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'formaPago'}, text=self.move_id.invoice_payment_term_id.name)
        if type != 'in_invoice':
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'totalLetras'}, text=amount_to_words_es(self.move_id.amount_total))
#         else:
#             if document_type.code in ('03','41'):
#                 self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'totalLetras'}, text=amount_to_words_es(self.total_with_tax))
        return factura
        
    def create_TreeElements(self, _parent,_tags_text):
        for tag, text in _tags_text:
            self.create_SubElement(_parent, tag, text=text)
        return True
    
    def create_SubElement(self, _parent, _tag, attrib={}, text=None, nsmap=None, **_extra):
        result = etree.SubElement(_parent, _tag, attrib,nsmap, **_extra)
        result.text = (text if not text is None and isinstance(text, str) else not text is None and str(text)) or None
        return result
    
    def getCodigoPrincipal(self, detalle_data, each):
        '''
        Hook se utilizara para aumentar el codigoAuxiliar
        en un modulo especifico del cliente.
        El metodo "get_product_code" retorna al referencia interna o el codigo de barra
        #TODO: implementar codigoAuxiliar para todos los clientes.
        '''
        detalle_data.append(('codigoPrincipal', each.product_id.get_product_code()[:25]))
        return detalle_data
    
    #Columns
    l10n_ec_access_key = fields.Char(
        string='Access Key', 
        readonly=True,
        track_visibility='onchange',
        help='Unique code to identify this document, is generated based on date, vat code, serial number, and other related fields',
        ) 
    l10n_ec_request_xml_file = fields.Binary(
        string='Peticion XML',
        attachment = True, #por default los attachment se guardan en el filestore
        help='El archivo XML enviado al proveedor de documentos electronicos, guardado para depuracion',
        )
    l10n_ec_request_xml_file_name = fields.Char(
        string='Name',
        size=64,
        help='El nombre del archivo XML enviado al proveedor de documentos electronicos, guardado para depuracion',
        )
    l10n_ec_response_xml_file = fields.Binary(
        string='Respuesta XML',
        attachment = True, #por default los attachment se guardan en el filestore
        help='El archivo XML retornado por el proveedor de documentos electronicos',
        )
    l10n_ec_response_xml_file_name = fields.Char(
        string='Name', 
        size=64,
        help='El nombre del archivo XML retornado por el proveedor de documentos electronicos',
        )

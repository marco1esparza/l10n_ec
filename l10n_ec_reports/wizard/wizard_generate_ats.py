# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from xml.dom.minidom import Document
from lxml import etree
from datetime import date, datetime
from time import time as tm
import time
import calendar
import base64
import os
import logging
 
_logger = logging.getLogger(__name__)

from odoo.addons.l10n_ec_reports.models.auxiliar_functions import get_name_only_characters
 
ATS_FILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'ats_29_08_2016.xsd')
#TODO jm: descomentar la sig linea y hacer que funcione
#ATS_CONTENT = open(ATS_FILENAME, 'r').read().strip()
 
#Documentos a reportar al SRI
_LOCAL_PURCHASE_DOCUMENT_CODES = ['01', '02', '03', '04', '05', '09', '11', '12', '19', '20', '21','41', '43', '45', '47', '48']
_FOREIGN_PURCHASE_DOCUMENT_CODES = ['15']
_SALE_DOCUMENT_CODES = ['02', '04', '05', '18', '41']

class L10nEcSimplifiedTransactionalAannex(models.TransientModel):
    _name = 'l10n_ec.simplified.transactional.annex'

    @api.model
    def default_get(self, fields):
        '''
        Invocamos el default_get para popular un valor de la compania
        '''
        res = super(L10nEcSimplifiedTransactionalAannex, self).default_get(fields)
        res.update({'include_electronic_document_in_ats': self.env.user.company_id.include_electronic_document_in_ats})
        return res
 
    @api.onchange('date_start')
    def onchange_start_date(self):
        '''
        Setea la fecha de inicio y fin
        '''
        if not self.date_start:
            today = datetime.now()
            self.date_start = datetime.strptime('%s-%s-01' % (today.year,today.month), DF)
        self.date_finish = datetime.strptime('%s-%s-%s' % (self.date_start.year, self.date_start.month, calendar.monthrange(self.date_start.year, self.date_start.month)[1]), DF)
 
    def act_generate_ats(self):
        '''
        Este método acumula los errores que saltaron en la validación del ATS y levanta un segundo wizard
        para la genereración del ATS.  
        '''
        report_status = []
        report_data = self.generate_ats(report_status)
        ctx = self._context.copy()
        if report_status:
            #si tiene errores en formato humano agregamos lineas para separar de los errores
            #en de validacion xsd
            report_status.append(u'\n\n')
        try:
            root = etree.XML(report_data.toxml(encoding='utf-8'))
            try:
                schema = etree.XMLSchema(etree.XML(ATS_CONTENT.strip()))
                if not schema.validate(root):
                    report_status.append(u'Ocurrieron los siguientes errores durante la validación del reporte ATS. '
                                         u'Contáctese con el administrador del servicio o el soporte técnico '
                                         u'indicándoles con exactitud los siguientes errores ocurridos: \n'
                                         u'>>> Inicio de errores <<<\n' + unicode(schema.error_log) +
                                         u'\n>>> Fin de errores <<<')
                    ctx.update({'report_errors': True})
            except Exception as e:
                report_status.append(u'Hubo un error al validar el reporte: El archivo de validación de reporte '
                                     u'no es un XSD válido. Contáctese con el administrador del servicio o el soporte '
                                     u'técnico. Los detalles del error son los siguientes: ' + unicode(e))
                ctx.update({'report_errors': True})
        except Exception as e:
            report_status.append(u'Hubo un error al analizar el reporte: El archivo de reporte no es un XML '
                                 u'válido. Contáctese con el administrador del servicio o el soporte técnico. '
                                 u'Los detalles del error son los siguientes: ' + unicode(e))
            ctx.update({'report_errors': True})
        view = self.env.ref('ecua_ats.view_wizard_ecua_ats')
        anio, mes, dia = str(self.date_start).split('-')
        ats_filename = 'ATS' + str(mes) + str(anio) + '.xml'
        if self.include_electronic_document_in_ats:
            ats_filename = 'ATS' + str(mes) + str(anio) + '_con_rets_electrónicas.xml'
        self.write({
            'report_errors': self.with_context(ctx)._report_errors(),
            'wizard2': True,
            'date_start': self.date_start,
            'date_finish': self.date_finish,
            'ats_filename': ats_filename,
            'errors_filename': 'errores.txt' ,
            # Contenido de los reportes
            'ats_file': base64.encodestring(report_data.toprettyxml(encoding='utf-8')),
            'errors_file': base64.encodestring((u'\n'.join(report_status) or u'').encode('utf-8'))
        })
        return {
            'name': 'ANEXO TRANSACCIONAL SIMPLIFICADO (ATS)',
            'res_id': self.id,
            'view_id':  view and view.id or False,
            'view_mode': 'form',
            'res_model': 'l10n_ec.simplified.transactional.annex',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
     
    @api.model
    def generate_ats(self, report_status):
        '''
        Generar el archivo xml del ATS.
        '''
        #2.1 IDENTIFICACION DEL INFORMANTE
        init_total_time = tm()
        company = self.env.user.company_id
        anio, mes, dia = str(self.date_start).split('-')
        doc = Document()
        if not company.vat :
            report_status.append(u'Ingrese el CI/RUC/PASS de la compañía.')
 
        main = doc.createElement('iva')
        doc.appendChild(main)
 
        ruc = doc.createElement('TipoIDInformante')
        main.appendChild(ruc)
        ruc.appendChild(doc.createTextNode(company.partner_id.l10n_ec_code))
 
        IdInformante = doc.createElement('IdInformante')
        main.appendChild(IdInformante)
        IdInformante.appendChild(doc.createTextNode(company.vat or ''))
 
        razonSocial = doc.createElement('razonSocial')
        main.appendChild(razonSocial)
        #TODO jm: borrar la sig linea y descomentar la otra cuando se solvente la falla que tiene el metodo en la linea
        #de codigo return pattern.sub(lambda m: replacements[m.group(0)], text) del metodo get_name_only_characters
        razonSocial.appendChild(doc.createTextNode(company.l10n_ec_legal_name))
        #razonSocial.appendChild(doc.createTextNode(get_name_only_characters(company.l10n_ec_legal_name)))
 
        atsanio = doc.createElement('Anio')
        main.appendChild(atsanio)
        atsanio.appendChild(doc.createTextNode(anio))
         
        atsmes = doc.createElement('Mes')
        main.appendChild(atsmes)
        atsmes.appendChild(doc.createTextNode(mes))
        
        #TODO jm: implementar la sig 4 lineas de codigo, se busca la tienda general de la comprania
        #ahora ese dato lo tenemos a nivel de punto de impresion
#         suc = self.env['sale.shop'].sudo().search([('company_id','=',self.env.user.company_id.id)])
#         numEstabRuc = doc.createElement('numEstabRuc')
#         main.appendChild(numEstabRuc)
#         numEstabRuc.appendChild(doc.createTextNode(str(len(suc)).zfill(3))) 
 
        #El campo se setea al final en otra sumatoria por performance
        nTotalVentas = doc.createElement('totalVentas')
        main.appendChild(nTotalVentas)
 
        codigo = doc.createElement('codigoOperativo')
        main.appendChild(codigo)
        codigo.appendChild(doc.createTextNode('IVA'))
         
        #2.2 DATA COMPRAS
        self.write_purchase_section(doc, main, report_status)
 
        #2.3 DATA VENTAS (AGRUPADO POR PARTNER) 
        total_ventas = self.write_sale_section(doc, main, report_status)
 
        #2.4 DATA DOCUMENTOS ANULADOS
        self.write_canceled_document_section(doc, main, report_status)
 
        pfec_mes = doc.createTextNode('{0:.2f}'.format(total_ventas))
        nTotalVentas.appendChild(pfec_mes)
 
        last_total_time = tm()
        ejecution_total_time = last_total_time - init_total_time
        _logger.info(u'Tiempo ejecucion total %s seg.', str(ejecution_total_time))
        return doc
     
    @api.model
    def write_purchase_section(self, doc, main, report_status):
        '''
        Escribe la seccion de compras en el ats
        '''
        init_time = tm()
        anio, mes, dia = str(self.date_start).split('-')
        account_move_obj = self.env['account.move'].sudo()
        local_purchase_invoice_ids = account_move_obj.search([
            ('type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('l10n_latam_document_type_id.code', 'in', _LOCAL_PURCHASE_DOCUMENT_CODES),
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish)
        ])
        #TODO evaluar crear otro tipo de documento para las compras de servicios al extranjero
        foreign_purchase_invoice_ids = account_move_obj.search([
            ('type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('l10n_latam_document_type_id.code', 'in', _FOREIGN_PURCHASE_DOCUMENT_CODES),
            #TODO jm: implementar la siguiente linea, el sri_tax_support_id ya no existe
            #('sri_tax_support_id.code', 'not in', ['06','07']), #no se reportan importaciones de inventario
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish)
        ])
        purchase_invoice_ids = local_purchase_invoice_ids + foreign_purchase_invoice_ids
        last_time = tm()
        ejecution_time = last_time - init_time
        _logger.info(u'Tiempo busqueda de facturas de compras %s seg.', str(ejecution_time))
        init_time = tm()
        if purchase_invoice_ids:
            compras = doc.createElement('compras')
            main.appendChild(compras)
            for in_inv in purchase_invoice_ids:
                #TODO jm: implementar o remover
#                 if in_inv.alarmed_document:
#                     #si la factura tiene novedades agregamos al msg de error
#                     #ayuda a identificar facturas sin retencion entre otros problemas
#                     report_status.append(u'Factura ' + str(in_inv.l10n_latam_document_number) + u' ' + in_inv.warning_msgs)
                 
                detallecompras = doc.createElement('detalleCompras')
                compras.appendChild(detallecompras)
     
                codSustento = doc.createElement('codSustento')
                detallecompras.appendChild(codSustento)
                #TODO jm: borrar la sig line cuando se descomente e implemente la sig relacionada con sri_tax_support_id
                vcodSustento = ''
                #vcodSustento = in_inv.sri_tax_support_id.code or ''
                codSustento.appendChild(doc.createTextNode(vcodSustento))
                if not vcodSustento:
                    report_status.append(u'Factura ' + str(in_inv.l10n_latam_document_number) + u' no tiene codigo de sustento tributario')
     
                tpIdProv = doc.createElement('tpIdProv')
                detallecompras.appendChild(tpIdProv)
                #TODO jm: implementar la sig linea, no tenemos transaction_type
                #tpIdProv.appendChild(doc.createTextNode(in_inv.transaction_type))
     
                idProv = doc.createElement('idProv')
                detallecompras.appendChild(idProv)
                #TODO jm: implementar la sig linea, todavia no esta implementado el invoice_vat
                #idProv.appendChild(doc.createTextNode(get_identification(in_inv.invoice_vat)))
                 
                tipoComprobante = doc.createElement('tipoComprobante')
                detallecompras.appendChild(tipoComprobante)
                tipoComprobante.appendChild(doc.createTextNode(in_inv.l10n_latam_document_type_id.code))
     
                #TODO jm: implementar la siguiente seccion, tenemos que implementar el transaction_type y related_part
                #de ser el caso
#                 natural_sociedad = '02' if in_inv.commercial_partner_id.is_company else '01' #se guarda el valor para usarlo DRY
#                 #TODO 2: es necesario limpiar los caracteres extraños? se deja para una segunda revision
#                 transaction_type = get_name_only_characters(in_inv.transaction_type)
#                  
#                 if transaction_type == '03': #cuando es compra con pasaporte
#                     tipoProv_ = doc.createElement('tipoProv')
#                     detallecompras.appendChild(tipoProv_)
#                     tipoProv_.appendChild(doc.createTextNode(natural_sociedad)) #el tipo de identifica
#                      
#                     denoProv = doc.createElement('denoProv')
#                     detallecompras.appendChild(denoProv)
#                     vdenoProv = get_name_only_characters(in_inv.name_in_ascii)
#                     denoProv.appendChild(doc.createTextNode(vdenoProv))
#                  
#                 if len(transaction_type) > 2:
#                     #si no es un codigo sino un texto, agregamos el texto del error
#                     report_status.append(transaction_type)
#                          
#                 parteRel = doc.createElement('parteRel')
#                 detallecompras.appendChild(parteRel)
#                 pparteRel = doc.createTextNode('SI' if in_inv.commercial_partner_id.related_part else 'NO')
#                 #TODO: En v11 mover el dato de parte relacionada a la factura pues puede cambiar en el tiempo
#                 parteRel.appendChild(pparteRel)
     
                fechaRegistro = doc.createElement('fechaRegistro')
                detallecompras.appendChild(fechaRegistro)
                fechaRegistro.appendChild(doc.createTextNode(self._getFormatDates(in_inv.invoice_date)))
                 
                establec = doc.createElement('establecimiento')
                detallecompras.appendChild(establec)
                establec.appendChild(doc.createTextNode(in_inv.l10n_latam_document_number[0:3]))
                 
                emision = doc.createElement('puntoEmision')
                detallecompras.appendChild(emision)
                emision.appendChild(doc.createTextNode(in_inv.l10n_latam_document_number[4:7]))
                     
                secuencial = doc.createElement('secuencial')
                detallecompras.appendChild(secuencial)
                secuencial.appendChild(doc.createTextNode(in_inv.l10n_latam_document_number[8:]))
                     
                fechaEmision = doc.createElement('fechaEmision')
                detallecompras.appendChild(fechaEmision)
                fechaEmision.appendChild(doc.createTextNode(self._getFormatDates(in_inv.invoice_date)))
                
                autorizacion = doc.createElement('autorizacion')
                detallecompras.appendChild(autorizacion)
                autorizacion.appendChild(doc.createTextNode(in_inv.l10n_ec_authorization or ''))
     
                baseNoGraIva = doc.createElement('baseNoGraIva')
                detallecompras.appendChild(baseNoGraIva)
                baseNoGraIva.appendChild(doc.createTextNode('{0:.2f}'.format(in_inv.l10n_ec_base_not_subject_to_vat or 0.00)))
     
                baseImponible = doc.createElement('baseImponible')
                detallecompras.appendChild(baseImponible)
                baseImponible.appendChild(doc.createTextNode('{0:.2f}'.format(in_inv.l10n_ec_base_cero_iva or 0.00)))
     
                baseImpGrav = doc.createElement('baseImpGrav')
                detallecompras.appendChild(baseImpGrav)
                baseImpGrav.appendChild(doc.createTextNode('{0:.2f}'.format(in_inv.l10n_ec_base_doce_iva or 0.00)))
     
                baseImpExe = doc.createElement('baseImpExe')
                detallecompras.appendChild(baseImpExe)
                baseImpExe.appendChild(doc.createTextNode('{0:.2f}'.format(in_inv.l10n_ec_base_tax_free or 0.00)))
     
                montoIce = doc.createElement('montoIce')
                detallecompras.appendChild(montoIce)
                montoIce.appendChild(doc.createTextNode('0.00'))
     
                montoIva = doc.createElement('montoIva')
                detallecompras.appendChild(montoIva)
                montoIva.appendChild( doc.createTextNode('{0:.2f}'.format(in_inv.l10n_ec_vat_doce_subtotal or 0.00)))
                 
                # Porcentage de retencion
                # TODO los codigos de retencion cambiaron, hay que hacer versiones con if por fechas
                valRetBien10 = doc.createElement('valRetBien10')
                detallecompras.appendChild(valRetBien10)
                valRetBien10.appendChild(doc.createTextNode('{0:.2f}'.format(self._get_vat_withhold_values(in_inv,'721'))))
     
                valRetServ20 = doc.createElement('valRetServ20')
                detallecompras.appendChild(valRetServ20)
                valRetServ20.appendChild(doc.createTextNode('{0:.2f}'.format(self._get_vat_withhold_values(in_inv,'723'))))
     
                valorRetBienes = doc.createElement('valorRetBienes')
                detallecompras.appendChild(valorRetBienes)
                valorRetBienes.appendChild(doc.createTextNode('{0:.2f}'.format(self._get_vat_withhold_values(in_inv,'725'))))
                 
                valRetServ50 = doc.createElement('valRetServ50')
                detallecompras.appendChild(valRetServ50)
                valRetServ50.appendChild(doc.createTextNode('{0:.2f}'.format(self._get_vat_withhold_values(in_inv,'727'))))
                 
                valorRetServicios = doc.createElement('valorRetServicios')
                detallecompras.appendChild(valorRetServicios)
                valorRetServicios.appendChild(doc.createTextNode('{0:.2f}'.format(self._get_vat_withhold_values(in_inv,'729'))))
                 
                valRetServ100 = doc.createElement('valRetServ100')
                detallecompras.appendChild(valRetServ100)
                valRetServ100.appendChild(doc.createTextNode('{0:.2f}'.format(self._get_vat_withhold_values(in_inv,'731'))))
     
                totbasesImpReemb = doc.createElement('totbasesImpReemb')
                detallecompras.appendChild(totbasesImpReemb)
                ptotbasesImpReemb = doc.createTextNode('%.2f' % self._get_total_refund(in_inv))
                totbasesImpReemb.appendChild(ptotbasesImpReemb)
     
                pagoExterior = doc.createElement('pagoExterior')
                detallecompras.appendChild(pagoExterior)
                 
                # Se asume que esta en Ecuador y por eso si es del mismo pais
                # que la compania es residente
                if not in_inv.invoice_country_id:
                    pago_local_extranjero = u'Compra no tiene identificado un Pais'
                elif in_inv.invoice_country_id == in_inv.company_id.country_id:
                    pago_local_extranjero = '01' # residente!
                else:
                    #si el pais es distinto  
                    pago_local_extranjero = '02' #no residente
     
                # Codigo original, tenia un TODO de eliminacion, se lo mantiene por que da error en el codigo
                # de pago de pais al verificarlo con el XSD, ademas asi ha venido trabajando hasta le momento 
                pago_local_extranjero = '01' # residente!
     
                pagoLocExt = doc.createElement('pagoLocExt')
                pagoExterior.appendChild(pagoLocExt)
                vpagoLocExt = doc.createTextNode(pago_local_extranjero)
                pagoLocExt.appendChild(vpagoLocExt)
                if pago_local_extranjero == '01': #pago a residentes en ecuador
                    paisEfecPago = doc.createElement('paisEfecPago')
                    pagoExterior.appendChild(paisEfecPago)
                    vpaisEfecPago = doc.createTextNode('NA')
                    paisEfecPago.appendChild(vpaisEfecPago)
     
                    #Aplica convenio de doble tributacion
                    aplicConvDobTrib = doc.createElement('aplicConvDobTrib')
                    pagoExterior.appendChild(aplicConvDobTrib)
                    vaplicConvDobTrib = doc.createTextNode('NA')
                    aplicConvDobTrib.appendChild(vaplicConvDobTrib)
     
                    #Pago al exterior sujeto a retencion en aplicacion a la norma legal
                    pagExtSujRetNorLeg = doc.createElement('pagExtSujRetNorLeg')
                    pagoExterior.appendChild(pagExtSujRetNorLeg)
                    vpagExtSujRetNorLeg = doc.createTextNode('NA')
                    pagExtSujRetNorLeg.appendChild(vpagExtSujRetNorLeg)
                     
                else: # pago_local_extranjero == '02':
                    #TODO falta implementar pagos a regimenes extranjeros
                    #Se asume regimen general, #todo implementar los otros regimenes
                    #posiblemente se pueda indicar en la tabla de paises
                    #o en base al codigo de pais y mapeo por python
                    tipoRegi_value = '01'
                    tipoRegi = doc.createElement('tipoRegi')
                    pagoExterior.appendChild(tipoRegi)
                    vtipoRegi = doc.createTextNode(tipoRegi_value)
                    tipoRegi.appendChild(vtipoRegi)
                 
                    if tipoRegi == '01':
                        #País de residencia a quien se efectua el pago regimen general
                        paisEfecPagoGen = doc.createElement('paisEfecPagoGen')
                        pagoExterior.appendChild(paisEfecPagoGen)
                        vpaisEfecPagoGen = doc.createTextNode(in_inv.invoice_country_id.code or u'Compra no tiene identificado un Pais')
                        paisEfecPagoGen.appendChild(vpaisEfecPagoGen)
                                             
                    #Pais de residencia a quien se efectua el pago
                    #en regimen general se copia el paisEfecPagoGen
                    paisEfecPago = doc.createElement('paisEfecPago')
                    pagoExterior.appendChild(paisEfecPago)
                    vpaisEfecPago = doc.createTextNode(in_inv.invoice_country_id.code or u'Compra no tiene identificado un Pais')
                    paisEfecPago.appendChild(vpaisEfecPago)
                                 
                    #Denominacion del regimen fiscal preferente
                    #todo                
                    #Aplica convenio de doble tributacion
                    aplicConvDobTrib = doc.createElement('aplicConvDobTrib')
                    pagoExterior.appendChild(aplicConvDobTrib)
                    vaplicConvDobTrib = doc.createTextNode('NO') #TODO SI/NO
                    aplicConvDobTrib.appendChild(vaplicConvDobTrib)
     
                    #Pago al exterior sujeto a retencion en aplicacion a la norma legal
                    pagExtSujRetNorLeg = doc.createElement('pagExtSujRetNorLeg')
                    pagoExterior.appendChild(pagExtSujRetNorLeg)
                    vpagExtSujRetNorLeg = doc.createTextNode('NO') #TODO SI/NO
                    pagExtSujRetNorLeg.appendChild(vpagExtSujRetNorLeg)
                            
                    #Pago es un régimen fiscal preferente o de menor imposisión
                    #todo                 
                    pagoRegFis = doc.createElement('pagoRegFis')
                    pagoExterior.appendChild(pagoRegFis)
                    vpagoRegFis = doc.createTextNode('NA') #TODO SI/NO
                    pagoRegFis.appendChild(vpagoRegFis)
     
                if in_inv.total_with_tax >= 1000:
                    #excluimos pagos menores a USD 1000
                    formasDePago = doc.createElement('formasDePago')
                    detallecompras.appendChild(formasDePago)
                    for forma_pago in in_inv.payment_method_id:
                        formaPago = doc.createElement('formaPago')
                        formasDePago.appendChild(formaPago)
                        vformaPago = doc.createTextNode(forma_pago.code)
                        formaPago.appendChild(vformaPago)
                 
                #2.2.1 DATA RETENCIONES RENTA
                self.write_purchase_withhold_income_tax_section(doc, main, in_inv, detallecompras, report_status)
     
                #2.2.2 DATA NOTAS DE CREDITO Y NOTAS DE DEBITO
                self.write_purchase_credit_and_debit_note_section(doc, main, in_inv, detallecompras, report_status)
                 
                #2.2.3 DATA REEMBOLSO
                self.write_purchase_refund_section(doc, main, in_inv, detallecompras, report_status)
 
        last_time = tm()
        ejecution_time = last_time - init_time
        _logger.info(u'Tiempo ejecucion seccion compras %s seg.', str(ejecution_time))
         
    @api.model
    def write_purchase_withhold_income_tax_section(self, doc, main, in_inv, detallecompras, report_status):
        '''
        Escribe la seccion de retenciones de renta en compras en el ats
        '''
        #Las retenciones se basan en los impuestos de la factura y se adiciona el numero de retencion cuando existe,
        #al inicio del ats se usa el warning_msg para indicar cuando no se ha emitido el doc de retencion
        anio, mes, dia = str(self.date_start).split('-')
        taxes = self.get_tax_summary(in_inv) #se guarda el valor para usarlo DRY
        income_tax_withholds = [t for t in taxes if t['type_ec'] == 'withhold_income_tax']
        withholds = self.env['account.withhold'].search([
            ('id', 'in', in_inv.withhold_ids.mapped('id')),
            ('state', '=', 'approved')
        ])
        hide_withhold = False
        if int(anio) >= 2018 and int(mes) >= 1:
            #resolucion  NAC-DGERCGC16-00000092, 
            #a partir de ene2018 no se reportan retenciones electronicas
            if withholds._fields.get('allow_electronic_document', False):
                if withholds and all(withhold.allow_electronic_document for withhold in withholds) and not self.include_electronic_document_in_ats:
                    #si la retencion es electronica entonces no cargamos impuestos
                    hide_withhold = True
 
        if income_tax_withholds and in_inv.document_invoice_type_id.code not in ['41'] and not hide_withhold:
            #cuando son reembolsos no se reporta el detalle de valores retenidos (el dimm no permite)
            air_form = doc.createElement('air')
            detallecompras.appendChild(air_form)
            for tax_line in income_tax_withholds:
                if tax_line.type_ec != 'withhold_income_tax':
                    continue #no ejectuamos el lazo en este caso, solo es para retenciones de la renta
                 
                detalleAir_form = doc.createElement('detalleAir')
                air_form.appendChild(detalleAir_form)
                 
                codigoRet = doc.createElement('codRetAir')
                detalleAir_form.appendChild(codigoRet)
                vcodigoRet = tax_line.tax_code
                if not vcodigoRet or len(vcodigoRet) < 3:
                    #si no hay codigo de retencion o no es de al menos 3 digitos
                    report_status.append(u'Impuesto IR sin codigo ats, doc compra ' + str(in_inv.l10n_latam_document_number))
                pcodigoRet = doc.createTextNode(vcodigoRet or 'NA')
                codigoRet.appendChild(pcodigoRet)
 
                baseImp = doc.createElement('baseImpAir')
                detalleAir_form.appendChild(baseImp)
                pbaseImp = doc.createTextNode('{0:.2f}'.format(tax_line.base))
                baseImp.appendChild(pbaseImp)
 
                porcentajeRet = doc.createElement('porcentajeAir')
                detalleAir_form.appendChild(porcentajeRet)
                pporcentajeRet = doc.createTextNode(
                    '{0:.2f}'.format(abs(tax_line.percentage)))
                porcentajeRet.appendChild(pporcentajeRet)
 
                valorRet = doc.createElement('valRetAir')
                detalleAir_form.appendChild(valorRet)
                pvalorRet = doc.createTextNode('{0:.2f}'.format(abs(tax_line.amount)))
                valorRet.appendChild(pvalorRet)
 
            #RETENCIONES POR DIVIDENDOS #TODO Implementar
            #Fecha de Pago del Dividendo
            #Impuesto a la renta pagado por la sociedad correspondiente al dividendo
            #Año en que se generaron las utilidades atribuibles al dividendo
             
            #RETENCIONES POR BANANO #TODO Implementar
            #Cantidad de cajas estándar de banano
            #Precio de cajas estándar de banano
            #Precio de la caja de banano
 
            for withhold in withholds: 
                #De haber mas de una retencion (escenario imposible con Odoo)
                #se deberia poner estabRetencion2 para la segunda retencion
                if withhold.alarmed_document:
                    #si la factura tiene novedades agregamos al msg de error
                    #ayuda a identificar facturas sin retencion entre otros problemas
                    report_status.append(u'Retencion ' + str(withhold.l10n_latam_document_number) + u' ' + withhold.warning_msgs)
 
                estabRetencion1 = doc.createElement('estabRetencion1')
                detallecompras.appendChild(estabRetencion1)
                pestabRetencion1 = doc.createTextNode(withhold.l10n_latam_document_number[0:3])
                estabRetencion1.appendChild(pestabRetencion1)
 
                ptoEmiRetencion1 = doc.createElement('ptoEmiRetencion1')
                detallecompras.appendChild(ptoEmiRetencion1)
                pptoEmiRetencion1 = doc.createTextNode(withhold.l10n_latam_document_number[4:7])
                ptoEmiRetencion1.appendChild(pptoEmiRetencion1)
 
                secRetencion1 = doc.createElement('secRetencion1')
                detallecompras.appendChild(secRetencion1)
                psecRetencion1 = doc.createTextNode(withhold.l10n_latam_document_number[8:])
                secRetencion1.appendChild(psecRetencion1)
                 
                autRetencion1 = doc.createElement('autRetencion1')
                detallecompras.appendChild(autRetencion1)
                autRetencion1.appendChild(doc.createTextNode(str(withhold.authorizations_id.name).strip()))
 
                fechaEmiRet1 = doc.createElement('fechaEmiRet1')
                detallecompras.appendChild(fechaEmiRet1)
                pfechaEmiRet1 = doc.createTextNode(self._getFormatDates(withhold.date_withhold))
                fechaEmiRet1.appendChild(pfechaEmiRet1)
#     
#     @api.model
#     def write_purchase_credit_and_debit_note_section(self, doc, main, in_inv, detallecompras, report_status):
#         '''
#         Escribe la seccion de notas de credito y notas de debito en compras en el ats
#         '''
#         if in_inv.document_invoice_type_id.code=='04' or in_inv.document_invoice_type_id.code=='05':
#             docModificado = doc.createElement('docModificado')
#             detallecompras.appendChild(docModificado)
#             vdocModificadoo = in_inv.invoice_rectification_id.document_invoice_type_id.code or ''
#             pdocModificadoo = doc.createTextNode(vdocModificadoo)
#             docModificado.appendChild(pdocModificadoo)
#             if not vdocModificadoo:
#                 #si no es un codigo sino un texto, agregamos el texto del error
#                 report_status.append(u'Factura ' + str(in_inv.invoice_rectification_id.number) + u' no tiene tipo de documento')
#             else:
#                 pass #do nothing
# 
#             estabModificado = doc.createElement('estabModificado')
#             detallecompras.appendChild(estabModificado)
#             pestabModificado = doc.createTextNode(in_inv.invoice_rectification_id.l10n_latam_document_number[0:3])
#             estabModificado.appendChild(pestabModificado)
# 
#             ptoEmiModificado = doc.createElement('ptoEmiModificado')
#             detallecompras.appendChild(ptoEmiModificado)
#             pptoEmiModificado = doc.createTextNode(in_inv.invoice_rectification_id.l10n_latam_document_number[4:7])
#             ptoEmiModificado.appendChild(pptoEmiModificado)
# 
#             secModificado = doc.createElement('secModificado')
#             detallecompras.appendChild(secModificado)
#             psecModificado = doc.createTextNode(in_inv.invoice_rectification_id.l10n_latam_document_number[8:])
#             secModificado.appendChild(psecModificado)
# 
#             autModificado = doc.createElement('autModificado')
#             detallecompras.appendChild(autModificado)
#             Modificadoauth = doc.createTextNode(in_inv.invoice_rectification_id.authorizations_id.name)
#             autModificado.appendChild(Modificadoauth)
# 
#     @api.model    
#     def write_purchase_refund_section(self, doc, main, in_inv, detallecompras, report_status):
#         '''
#         Escribe la seccion de reembolsos en compras en el ats
#         '''
#         #TODO: Validar la implementacion para los tipos de documento 47 y 48
#         if in_inv.document_invoice_type_id.code in ['41','47','48'] and in_inv.account_refund_client_ids:
#             reembolsos = doc.createElement('reembolsos')
#             detallecompras.appendChild(reembolsos)
#             for refund_id in in_inv.account_refund_client_ids:
#                 reembolso = doc.createElement('reembolso')
#                 reembolsos.appendChild(reembolso)
#                 tipoComprobanteReemb = doc.createElement('tipoComprobanteReemb')
#                 reembolso.appendChild(tipoComprobanteReemb)
#                 tipoComprobanteReemb.appendChild(doc.createTextNode(refund_id.document_invoice_type_id.code))
# 
#                 idProvReemb = doc.createElement('tpIdProvReemb')
#                 reembolso.appendChild(idProvReemb)
#                 vidProvReemb = refund_id.transaction_type
#                 idProvReemb.appendChild(doc.createTextNode(vidProvReemb))
#                 
#                 if len(vidProvReemb) > 2:
#                     #si no es un codigo sino un texto, agregamos el texto del error
#                     report_status.append(vidProvReemb)
#                 
#                 idProvReemb = doc.createElement('idProvReemb')
#                 reembolso.appendChild(idProvReemb)
#                 idProvReemb.appendChild(doc.createTextNode(get_identification(refund_id.partner_id.vat)))
#                 
#                 establecimientoReemb = doc.createElement('establecimientoReemb')
#                 reembolso.appendChild(establecimientoReemb)
#                 establecimientoReemb.appendChild(doc.createTextNode(refund_id.number[0:3]))
#                 
#                 puntoEmisionReemb = doc.createElement('puntoEmisionReemb')
#                 reembolso.appendChild(puntoEmisionReemb)
#                 puntoEmisionReemb.appendChild(doc.createTextNode(refund_id.number[4:7]))
#                 
#                 secuencialReemb = doc.createElement('secuencialReemb')
#                 reembolso.appendChild(secuencialReemb)
#                 vsecuencialReemb = refund_id.number[8:]
#                 secuencialReemb.appendChild(doc.createTextNode(vsecuencialReemb or ''))
#                 if not vsecuencialReemb:
#                     #si no es un codigo sino un texto, agregamos el texto del error
#                     report_status.append(u'Dentro del reembolso ' + str(refund_id.refund_invoice_id.number) + \
#                                          u', la factura ' + refund_id.number + \
#                                          u' no tiene secuencial de reembolso')
#                 else:
#                     pass #do nothing
#                 
#                 fechaEmisionReemb = doc.createElement('fechaEmisionReemb')
#                 reembolso.appendChild(fechaEmisionReemb)
#                 fechaEmisionReemb.appendChild(doc.createTextNode(self._getFormatDates(refund_id.creation_date)))
#                 
#                 autorizacionReemb = doc.createElement('autorizacionReemb')
#                 reembolso.appendChild(autorizacionReemb)
#                 vautorizacionReemb = refund_id.authorizations_id.name
#                 autorizacionReemb.appendChild(doc.createTextNode(vautorizacionReemb or ''))
#                 if not vautorizacionReemb:
#                     #si no es un codigo sino un texto, agregamos el texto del error
#                     report_status.append(u'Dentro del reembolso ' + str(refund_id.refund_invoice_id.number) + \
#                                          u', la factura ' + refund_id.number + \
#                                          u' no tiene autorizacion')
# 
#                 elif len(vautorizacionReemb) not in [10, 37, 49]:
#                     report_status.append(u'Dentro del reembolso ' + str(refund_id.refund_invoice_id.number) + \
#                                          u', la factura ' + refund_id.number + \
#                                          u' tiene una autorizacion incompleta')
# 
#                 else:
#                     pass #do nothing
#                 baseImponibleReemb = doc.createElement('baseImponibleReemb')
#                 reembolso.appendChild(baseImponibleReemb)
#                 aux = doc.createTextNode('%.2f' %  abs(float(refund_id.base_vat_0)))
#                 baseImponibleReemb.appendChild(aux)
#                 
#                 baseImpGravReemb = doc.createElement('baseImpGravReemb')
#                 reembolso.appendChild(baseImpGravReemb)
#                 aux = doc.createTextNode('%.2f' % abs(float(refund_id.base_vat_no0)))
#                 baseImpGravReemb.appendChild(aux)
#                 
#                 baseNoGraIvaReemb = doc.createElement('baseNoGraIvaReemb')
#                 reembolso.appendChild(baseNoGraIvaReemb)
#                 aux = doc.createTextNode('%.2f' % abs(float(refund_id.no_vat_amount)))
#                 baseNoGraIvaReemb.appendChild(aux)
# 
#                 baseImpExeReemb = doc.createElement('baseImpExeReemb')
#                 reembolso.appendChild(baseImpExeReemb)
#                 aux = doc.createTextNode('%.2f' % abs(float(refund_id.base_tax_free)))
#                 baseImpExeReemb.appendChild(aux)
#                 
#                 montoIceRemb = doc.createElement('montoIceRemb')
#                 reembolso.appendChild(montoIceRemb)
#                 aux = doc.createTextNode('%.2f' % abs(float(refund_id.ice_amount)))
#                 montoIceRemb.appendChild(aux)
# 
#                 montoIvaRemb = doc.createElement('montoIvaRemb')
#                 reembolso.appendChild(montoIvaRemb)
#                 aux = doc.createTextNode('%.2f' % abs(float(refund_id.vat_amount_no0)))
#                 montoIvaRemb.appendChild(aux)
#     
#     @api.model
#     def write_sale_section(self, doc, main, report_status):
#         '''
#         Escribe la seccion de ventas en el ats
#         '''
#         init_time = tm()
#         total_ventas = 0.0
#         model_invoice = self.env['account.invoice'].sudo()
#         # Se ordenan las facturas por RUC de la factura, en vez del partner_id
#         # La funcion _get_sales_info se encarga de agrupar ya por el invoice_vat
#         # y de pre-procesarlas asi
#         # Se excluyen aquellas que son exportaciones
#         out_invoices = self._get_sales_info(model_invoice.search([
#             ('invoice_date', '<=', self.date_finish),
#             ('invoice_date', '>=', self.date_start),
#             ('type', 'in', ['out_invoice','out_refund']),
#             ('state','in', ('open','paid')),
#             ('document_invoice_type_id.code', 'in', _SALE_DOCUMENT_CODES),
#             '|',('fiscal_position_id.transaction_type', 'not in', ['foreign_company_export','foreign_person_export']),
#             ('fiscal_position_id', '=', False)
#         ], order='invoice_vat, document_invoice_type_id, invoice_date'))
#         last_time = tm()
#         ejecution_time = last_time - init_time
#         _logger.info(u'Tiempo busqueda facturas de ventas %s seg.', str(ejecution_time))
#         init_time = tm()
#         if out_invoices:
#             ventas_form = doc.createElement('ventas')
#             main.appendChild(ventas_form)
#             for out_inv in out_invoices:
#                 #los docs electronicos no suman al total de ventas del talon resumen
#                 if out_invoices[out_inv]['tipoEmision'] == 'F':
#                     total_ventas += out_invoices[out_inv]['amount_untaxed_signed']
# 
#                 detalle_ventas_form = doc.createElement('detalleVentas')
#                 ventas_form.appendChild(detalle_ventas_form)
# 
#                 tpIdCliente = doc.createElement('tpIdCliente')
#                 detalle_ventas_form.appendChild(tpIdCliente)
#                 vtpIdCliente = out_invoices[out_inv]['tpIdCliente']
#                 if len(vtpIdCliente) > 2:
#                     #si no es un codigo sino un texto, agregamos el texto del error
#                     report_status.append(vtpIdCliente)
#                 ptpIdCliente = doc.createTextNode(vtpIdCliente)
#                 tpIdCliente.appendChild(ptpIdCliente)
# 
#                 idCliente = doc.createElement('idCliente')
#                 detalle_ventas_form.appendChild(idCliente)
#                     # pidCliente = doc.createTextNode(ruc)
#                 pidCliente = doc.createTextNode(out_invoices[out_inv]['idCliente'])
#                 idCliente.appendChild(pidCliente)
# 
#                 if not ((out_invoices[out_inv]['tpIdCliente'] == '07' and out_invoices[out_inv]['tipoComprobante'] in ('18','41')) or \
#                         out_invoices[out_inv]['tpIdCliente'] == '07' or out_invoices[out_inv]['idCliente'] == '9999999999999'):
#                         parteRelVtas = doc.createElement('parteRelVtas')
#                         detalle_ventas_form.appendChild(parteRelVtas)
#                         # Para Ecommerce related_part no se puede hacer nada asi que toma
#                         # el valor por defecto en la creacion del partner
#                         pparteRel = doc.createTextNode('SI' if out_invoices[out_inv]['parteRelVtas'] else 'NO')
#                         parteRelVtas.appendChild(pparteRel)
#                 
#                 if out_invoices[out_inv]['tpIdCliente'] == '06':
#                         tipoCliente = doc.createElement('tipoCliente')
#                         detalle_ventas_form.appendChild(tipoCliente)
#                         data_tipoCliente = False
#                         if out_invoices[out_inv]['tipoCliente'] == '06':
#                             data_tipoCliente = '01'
#                         elif out_invoices[out_inv]['tipoCliente'] == '08':
#                             data_tipoCliente = '02'
#                         else: 
#                             #El tipo de cliente no es persona natural ni empresa extranjera
#                             mensaje = u' '.join((u'El cliente con VAT', out_invoices[out_inv]['idCliente'],
#                                       u'tiene mal identificado el tipo de cliente:', out_invoices[out_inv]['tipoCliente']))
#                             data_tipoCliente = mensaje 
#                             report_status.append(mensaje)
#                         ptipoCliente = doc.createTextNode(data_tipoCliente)
#                         tipoCliente.appendChild(ptipoCliente)
# 
#                         denoCli = doc.createElement('denoCli')
#                         detalle_ventas_form.appendChild(denoCli)
#                         pdenoCli = doc.createTextNode(out_invoices[out_inv]['denoCli'])
#                         denoCli.appendChild(pdenoCli)
# 
#                 tipoComprobante = doc.createElement('tipoComprobante')
#                 detalle_ventas_form.appendChild(tipoComprobante)
#                 ptipoComprobante = doc.createTextNode(out_invoices[out_inv]['tipoComprobante'])
#                 tipoComprobante.appendChild(ptipoComprobante)
# 
#                 tipoEmision = doc.createElement('tipoEmision')
#                 detalle_ventas_form.appendChild(tipoEmision)
#                 ptipoEmision = doc.createTextNode(out_invoices[out_inv]['tipoEmision'])
#                 tipoEmision.appendChild(ptipoEmision)
# 
#                 numeroComprobantes = doc.createElement('numeroComprobantes')
#                 detalle_ventas_form.appendChild(numeroComprobantes)
#                 pnumeroComprobantes = doc.createTextNode(str(out_invoices[out_inv]['numeroComprobantes']))
#                 numeroComprobantes.appendChild(pnumeroComprobantes)
# 
#                 baseNoGraIva = doc.createElement('baseNoGraIva')  # Base imponible no objeto de iva
#                 detalle_ventas_form.appendChild(baseNoGraIva)
#                 pbaseNoGraIva = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['baseNoGraIva']) or 0.00))
#                 baseNoGraIva.appendChild(pbaseNoGraIva)
# 
#                 baseImponible = doc.createElement('baseImponible')  # Base imponible tarifa 0% iva
#                 detalle_ventas_form.appendChild(baseImponible)
#                 pbaseImponible = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['baseImponible']) or 0.00))
#                 baseImponible.appendChild(pbaseImponible)
# 
#                 baseImpGrav = doc.createElement('baseImpGrav')  # Base imponible tarifa diferente de 0% iva
#                 detalle_ventas_form.appendChild(baseImpGrav)
#                 pbaseImpGrav = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['baseImpGrav'])or 0.00))
#                 baseImpGrav.appendChild(pbaseImpGrav)
# 
#                 montoIva = doc.createElement('montoIva')
#                 detalle_ventas_form.appendChild(montoIva)
#                 pmontoIva = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['montoIva'])or 0.00))
#                 montoIva.appendChild(pmontoIva)
#                 
#                 montoIceV = doc.createElement('montoIce')
#                 detalle_ventas_form.appendChild(montoIceV)
#                 pmontoIceV = doc.createTextNode('{0:.2f}'.format(0.00))
#                 montoIceV.appendChild(pmontoIceV)
#                 
#                 # TODO: pendiente de migrar  compensacion
#                 valorRetIva = doc.createElement('valorRetIva')
#                 detalle_ventas_form.appendChild(valorRetIva)
#                 pvalorRetIva = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['valorRetIva'])))
#                 valorRetIva.appendChild(pvalorRetIva)
#                 
#                 valorRetRenta = doc.createElement('valorRetRenta')
#                 detalle_ventas_form.appendChild(valorRetRenta)
#                 pvalorRetRenta = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['valorRetRenta'])))
#                 valorRetRenta.appendChild(pvalorRetRenta)
# 
#                 pay_codes = []
#                 if out_invoices[out_inv]['formas_pago'] and out_invoices[out_inv]['tipoComprobante'] not in ['04']:
#                     #excluimos notas de credito, codigo 04
#                     for payment_code in out_invoices[out_inv]['formas_pago']:
#                         if payment_code != False:
#                             pay_codes += [payment_code]
#                     formasDePagoV = doc.createElement('formasDePago')
#                     detalle_ventas_form.appendChild(formasDePagoV)
#                     for payment_code in pay_codes:
#                         formaPagoV = doc.createElement('formaPago')
#                         formasDePagoV.appendChild(formaPagoV)
#                         vformaPagoV = doc.createTextNode(payment_code)
#                         formaPagoV.appendChild(vformaPagoV)
#             
#             ventasEstablecimiento = doc.createElement('ventasEstablecimiento')
#             main.appendChild(ventasEstablecimiento)
#             
#             for shop in self.env['sale.shop'].search([('company_id','=',self.env.user.company_id.id)]):
#                 ventaEst = doc.createElement('ventaEst')
#                 ventasEstablecimiento.appendChild(ventaEst)
#                 codEstab = doc.createElement('codEstab')
#                 ventaEst.appendChild(codEstab)
#                 valventaEst = doc.createTextNode(str(shop.number).zfill(3))
#                 codEstab.appendChild(valventaEst)
#                 ventasEstab = doc.createElement('ventasEstab')
#                 ventaEst.appendChild(ventasEstab)
#                 total_shop = self.get_total_shop(self.date_start, self.date_finish,shop.id)['total']
#                 valventaEst = doc.createTextNode('{0:.2f}'.format(total_shop))
#                 ventasEstab.appendChild(valventaEst)
#             
#         last_time = tm()
#         ejecution_time = last_time - init_time
#         _logger.info(u'Tiempo ejecucion seccion ventas %s seg.', str(ejecution_time))
#         return total_ventas
#         
#     @api.model
#     def write_canceled_document_section(self, doc, main, report_status):
#         '''
#         Escribe la seccion de documentos anulados en el ats
#         '''
#         init_time = tm()
#         model_invoice = self.env['account.invoice'].sudo()
#         void_invoices = model_invoice.search([
#             ('invoice_date','<=', self.date_finish),
#             ('invoice_date','>=',self.date_start),
#             ('type', 'in', ['out_invoice', 'out_refund']),
#             ('document_invoice_type_id.code', 'in', _SALE_DOCUMENT_CODES),
#             ('state','=','cancel')
#         ])
#         void_withholds = self.env['account.withhold'].sudo().search([
#             ('date_withhold','<=', self.date_finish),
#             ('date_withhold','>=',self.date_start),
#             ('type','=','purchase_withhold'),
#             ('state','=','cancel')
#         ])
#         void_deliveries = self.env['stock.picking'].sudo().search([
#             ('date','<=', self.date_finish),
#             ('date','>=',self.date_start),
#             ('is_waybill','=',True), #identifica las guias de remision emitidas
#             ('state','=','cancel')
#         ])
#         
#         if void_invoices or void_withholds or void_deliveries:
#             anulados_form = doc.createElement('anulados')
#             main.appendChild(anulados_form)
#         
#         for void_invoice in void_invoices:
#             detalle_anuladas_form = doc.createElement('detalleAnulados')
#             anulados_form.appendChild(detalle_anuladas_form)
# 
#             tipoComprobante = doc.createElement('tipoComprobante')
#             detalle_anuladas_form.appendChild(tipoComprobante)
#             ptipoComprobante = doc.createTextNode(void_invoice.document_invoice_type_id.code)
#             tipoComprobante.appendChild(ptipoComprobante)
# 
#             establecimiento = doc.createElement('establecimiento')
#             detalle_anuladas_form.appendChild(establecimiento)
#             pestablecimiento = doc.createTextNode(void_invoice.l10n_latam_document_number[0:3])
#             establecimiento.appendChild(pestablecimiento)
# 
#             puntoEmision = doc.createElement('puntoEmision')
#             detalle_anuladas_form.appendChild(puntoEmision)
#             ppuntoEmision = doc.createTextNode(void_invoice.l10n_latam_document_number[4:7])
#             puntoEmision.appendChild(ppuntoEmision)
# 
#             secuencialInicio = doc.createElement('secuencialInicio')
#             detalle_anuladas_form.appendChild(secuencialInicio)
#             psecuencialInicio = doc.createTextNode(void_invoice.l10n_latam_document_number[8:])
#             secuencialInicio.appendChild(psecuencialInicio)
# 
#             secuencialFin = doc.createElement('secuencialFin')
#             detalle_anuladas_form.appendChild(secuencialFin)
#             psecuencialFin = doc.createTextNode(void_invoice.l10n_latam_document_number[8:])
#             secuencialFin.appendChild(psecuencialFin)
# 
#             autorizacion = doc.createElement('autorizacion')
#             detalle_anuladas_form.appendChild(autorizacion)
#             autorizacion.appendChild(doc.createTextNode(str(void_invoice.authorizations_id.name).strip()))
#        
#         for void_withhold in void_withholds:
#             detalle_anuladas_form = doc.createElement('detalleAnulados')
#             anulados_form.appendChild(detalle_anuladas_form)
# 
#             tipoComprobante = doc.createElement('tipoComprobante')
#             detalle_anuladas_form.appendChild(tipoComprobante)
#             ptipoComprobante = doc.createTextNode('07')
#             tipoComprobante.appendChild(ptipoComprobante)
# 
#             establecimiento = doc.createElement('establecimiento')
#             detalle_anuladas_form.appendChild(establecimiento)
#             pestablecimiento = doc.createTextNode(void_withhold.l10n_latam_document_number[0:3])
#             establecimiento.appendChild(pestablecimiento)
# 
#             puntoEmision = doc.createElement('puntoEmision')
#             detalle_anuladas_form.appendChild(puntoEmision)
#             ppuntoEmision = doc.createTextNode(void_withhold.l10n_latam_document_number[4:7])
#             puntoEmision.appendChild(ppuntoEmision)
# 
#             secuencialInicio = doc.createElement('secuencialInicio')
#             detalle_anuladas_form.appendChild(secuencialInicio)
#             psecuencialInicio = doc.createTextNode(void_withhold.l10n_latam_document_number[8:])
#             secuencialInicio.appendChild(psecuencialInicio)
# 
#             secuencialFin = doc.createElement('secuencialFin')
#             detalle_anuladas_form.appendChild(secuencialFin)
#             psecuencialFin = doc.createTextNode(void_withhold.l10n_latam_document_number[8:])
#             secuencialFin.appendChild(psecuencialFin)
# 
#             autorizacion = doc.createElement('autorizacion')
#             detalle_anuladas_form.appendChild(autorizacion)
#             vAutorizacion = void_withhold.authorizations_id.name
#             autorizacion.appendChild(doc.createTextNode(vAutorizacion or ''))
#             if not vAutorizacion:
#                 #si no es un codigo sino un texto, agregamos el texto del error
#                 report_status.append(u'La retencion ANULADA ' + void_withhold.l10n_latam_document_number + \
#                                      u' no tiene autorizacion')
#         for void_delivery in void_deliveries:
#             detalle_anuladas_form = doc.createElement('detalleAnulados')
#             anulados_form.appendChild(detalle_anuladas_form)
# 
#             tipoComprobante = doc.createElement('tipoComprobante')
#             detalle_anuladas_form.appendChild(tipoComprobante)
#             ptipoComprobante = doc.createTextNode('06')
#             tipoComprobante.appendChild(ptipoComprobante)
# 
#             establecimiento = doc.createElement('establecimiento')
#             detalle_anuladas_form.appendChild(establecimiento)
#             pestablecimiento = doc.createTextNode(void_delivery.waybill_number[0:3])
#             establecimiento.appendChild(pestablecimiento)
# 
#             puntoEmision = doc.createElement('puntoEmision')
#             detalle_anuladas_form.appendChild(puntoEmision)
#             ppuntoEmision = doc.createTextNode(void_delivery.waybill_number[4:7])
#             puntoEmision.appendChild(ppuntoEmision)
# 
#             secuencialInicio = doc.createElement('secuencialInicio')
#             detalle_anuladas_form.appendChild(secuencialInicio)
#             psecuencialInicio = doc.createTextNode(void_delivery.waybill_number[8:])
#             secuencialInicio.appendChild(psecuencialInicio)
# 
#             secuencialFin = doc.createElement('secuencialFin')
#             detalle_anuladas_form.appendChild(secuencialFin)
#             psecuencialFin = doc.createTextNode(void_delivery.waybill_number[8:])
#             secuencialFin.appendChild(psecuencialFin)
# 
#             autorizacion = doc.createElement('autorizacion')
#             detalle_anuladas_form.appendChild(autorizacion)
#             cancelauth = doc.createTextNode(str(void_delivery.authorizations_id.name).strip())
#             autorizacion.appendChild(cancelauth)
#             
#         last_time = tm()
#         ejecution_time = last_time - init_time
#         _logger.info(u'Tiempo ejecucion seccion anulados %s seg.', str(ejecution_time))
#     
#     @api.model
#     def _report_errors(self):
#         '''
#         Este método devuelve un mensaje de error si hubo problemas en la validación del ATS
#         '''
#         msgs = ''
#         if self._context.get('report_errors'):
#             msgs = u'Existen novedades en la generación del ATS, para más detalles, haga clic en el archivo "Errores.txt"'
#         return msgs

    @api.model 
    def _getFormatDates(self, fecha):
        '''
        Da formato a la fecha d/m/Y
        '''        
        return fecha.strftime('%d/%m/%Y')

    @api.model
    def _get_vat_withhold_values(self, invoice, code_tax):
        '''
        Retorna el valor sumarizado de un codigo de retencion de IVA
        #TODO v11: Unificar con el metodo get_tax_summary usando un select case y alterando tax_code
        '''
        tax_value = 0.00
        for line in invoice.line_ids:
            if code_tax == line.tax_line_id.l10n_ec_code_applied: 
                tax_value += abs(line.credit)
        return tax_value
 
    @api.model
    def _get_total_refund(self, invoice):
        '''
        Dado un id de factura calcula el valor de reembolso en caso de tenerlo, basado en los documentos ingresados
        '''
        total_refund = 0.00
        if invoice:
            for ats_line in invoice.account_refund_client_ids:
                total_refund += ats_line.base_vat_0 + ats_line.base_vat_no0 + ats_line.base_tax_free + ats_line.no_vat_amount
        return total_refund
     
#     @api.model
#     def get_tax_summary(self, invoice):
#         '''
#         Este metodo obtiene los valores de los impuestos agrupados, util pues a vecees por centros de costos
#         los impuestos se dividen en varias lineas, y se requiere consolidarles
#         '''
#         lines = self.env['account.invoice.tax.summary']
#         self.env.cr.execute('''
#             select 
#                 at.code_ats as tax_code,
#                 at.amount as percentage,
#                 sum(ait.base) as base,
#                 sum(ait.amount) as amount,
#                 ait.invoice_id,
#                 at.type_ec as type_ec
#             from account_invoice_tax ait join
#                 account_tax at
#                     on ait.tax_id=at.id
#             where ait.id in %s
#             group by tax_code, at.amount, at.type_ec, invoice_id
#         ''', (tuple(invoice.tax_line_ids.mapped('id') or [0]),)) #usamos el id cero para indicar que no hay registros
#         result = self.env.cr.fetchall()
#         for r in result:
#             res = {
#                 'tax_code': r[0],
#                 'percentage': r[1],
#                 'base': r[2],
#                 'amount': r[3],
#                 'invoice_id': r[4],
#                 'type_ec': r[5]
#             }
#             new_line = lines.new(res)
#             lines += new_line
#         return lines
#     
#     @api.model
#     def _get_sales_info(self, invoices):
#         '''
#         '''
#         group_sales = {}
#         if invoices:
#             for invoice in invoices:
#                 if invoice._fields.get('allow_electronic_document', False):
#                     emission_type = invoice.allow_electronic_document and 'E' or 'F'
#                 else:
#                     emission_type = 'F'
#                 id_partner = str(invoice.invoice_vat) + '-' + str(invoice.document_invoice_type_id.code) + '-' + emission_type
#                 values = group_sales.get(id_partner, {
#                             'numeroComprobantes': 0,
#                             'baseNoGraIva': 0.0,
#                             'baseImponible': 0.0,
#                             'baseImpGrav': 0.0,
#                             'montoIva': 0.0,
#                             'valorRetIva': 0.0,
#                             'valorRetRenta': 0.0,
#                             'amount_untaxed_signed': 0.0,
#                             'formas_pago': []
#                         })
#                 tax_with_vat = 0.0
#                 tax_with_income = 0.0
#                 for withholding in invoice.withhold_ids:
#                     if withholding.state == 'approved':
#                         if len(withholding.invoice_ids) == 1: 
#                             #cuando es mayor a uno es una retencion de tarjeta de credito
#                             #y no se reportan al ATS (o al menos nuestros clientes no requieren esta funcionalidad)
#                             for line in withholding.withhold_line_ids:
#                                 if line.tax_id.type_ec == 'withhold_vat':
#                                     tax_with_vat += line.amount
#                                 elif line.tax_id.type_ec == 'withhold_income_tax':
#                                     tax_with_income += line.amount
#                 values.update({
#                     'tpIdCliente': invoice.transaction_type,
#                     'parteRelVtas': invoice.invoice_related_part,
#                     'idCliente': get_identification(invoice.invoice_vat),
#                     'tipoComprobante': invoice.document_invoice_type_id.code,
#                     'tipoEmision': emission_type,
#                     'numeroComprobantes': values['numeroComprobantes'] + 1,
#                     'baseNoGraIva': values['baseNoGraIva'] + invoice.base_tax_free + invoice.base_not_subject_to_vat,
#                     'baseImponible': values['baseImponible'] + invoice.base_cero_iva,
#                     'baseImpGrav': values['baseImpGrav'] + invoice.base_doce_iva,
#                     'montoIva': values['montoIva'] + invoice.vat_doce_subtotal,
#                     'valorRetIva': values['valorRetIva'] + tax_with_vat,
#                     'valorRetRenta': values['valorRetRenta'] + tax_with_income,
#                     'formas_pago': list(set(values['formas_pago'] + [line.payment_method_id.code for line in invoice.account_invoice_payment_method_ids])),
#                     'compensaciones': {'tipoCompe': '0', 'monto': 0}, #implementar
#                     'amount_untaxed_signed': values['amount_untaxed_signed'] + invoice.amount_untaxed_signed
#                 })
#                 # La identificacion para tipoCliente y denoCli es requerida
#                 # unicamente si el codigo del transaction_type en
#                 # la factura es '06'
#                 if invoice.transaction_type == '06':
#                     values.update({
#                         'tipoCliente': get_invoice_ident_type(invoice), 
#                         'denoCli': get_name_only_characters(invoice.name_in_ascii)
#                     })                        
#                 group_sales[id_partner] = values
#         return group_sales
#     
#     @api.model
#     def get_total_shop(self, date_start, date_finish, codShop):
#         '''
#         '''
#         precalculated = self._precalculate_sums(date_start, date_finish)
#         return precalculated['by_shop'].get(codShop, {'total': 0.0, 'ivaComp': 0.0})
# 
#     @api.model
#     def _precalculate_sums(self, date_start, date_finish):
#         '''
#         Precalcula sumas de valores a diferentes niveles (totales, por tienda, ...).
# 
#         ADVERTENCIA: el total general es más grande que el total por tiendas porque eventualmente
#           no se asignan parte del amount_untaxed en base_0 ni base_12. Esto puede deberse a una mala
#           logica para llenar base_0 y base_12 pero eso ya es problema de la factura.
# 
#         Hay que revisar si queremos eso o cambiamos para poner amount_untaxed en lugar de la suma de
#           esos dos campos.
#         '''
#         _precalculated = {
#             'total': 0.0,
#             'by_shop': {}
#         }
#         total = 0
#         obj_invoice = self.env['account.invoice']
#         search_domain = [
#            ('invoice_date','<=', self.date_finish),
#            ('invoice_date','>=',self.date_start),
#            ('state', 'in', ('open', 'paid')),
#            ('type', 'in', ('out_invoice', 'out_refund')),
#            ('document_invoice_type_id.code', 'in', _SALE_DOCUMENT_CODES)
#         ]
#         if 'allow_electronic_document' in obj_invoice._fields:
#             #se excluyen documentos electronicos, 
#             #solamente cuando el modulo de docs electronicos esta instalado
#             search_domain.append(('allow_electronic_document','=', False))
#         invoice_id_list = self.env['account.invoice'].search(search_domain)
#         for invoice in invoice_id_list:
#             shop_id = invoice.printer_id and invoice.printer_id.shop_id and invoice.printer_id.shop_id.id
#             if shop_id:
#                 _precalculated['by_shop'].setdefault(shop_id, {'total': 0.0, 'ivaComp': 0.0})
#                 subtotal = float('{0:.2f}'.format(invoice.base_doce_iva)) + float('{0:.2f}'.format(invoice.base_cero_iva))
#                 subtotal = subtotal * (1 if invoice.type == 'out_invoice' else -1)
#                 _precalculated['by_shop'][shop_id]['total'] += subtotal
#                 total += float('{0:.2f}'.format(subtotal))
#                 #TODO: compensacion por ley de solidaridad
#                 #Seccion compensacion por ley de solidaridad
#                 #Debe sumarse las compensaciones en facturas de venta
#                 #if 'solidarity_compensation' in obj_invoice._columns and invoice.solidarity_compensation != 0.0:
#                 #self._precalculated['by_shop'][shop_id]['ivaComp'] += float('{0:.2f}'.format(abs(invoice.solidarity_compensation \
#         _precalculated['total'] = total
#         return _precalculated

    def _get_summary_report_name(self):
        '''
        '''
        for wizard in self:
            wizard.summary_filename = 'sumario.html'
 
    #Columns
    ats_filename = fields.Char(
        string='ATS Filename',
        size=64,
        help='Filename for the ATS report'
        )
    summary_filename = fields.Char(
        string='Summary Filename',
        compute=_get_summary_report_name,
        store=False,
        size=64,
        help='Filename for the summary report'
        )
    errors_filename = fields.Char(
        string='Errors Filename',
        size=32,
        help='Filename for the errors report'
        )
    ats_file = fields.Binary(
        string='ATS File',
        help='ATS file content'
        )
    summary_file = fields.Binary(
        string='Summary File',
        help='Summary file content'
        )
    errors_file = fields.Binary(
        string='Errors File',
        help='Errors file content'
        )
    #Campos básicos
    date_start = fields.Date(
        string='Fecha Desde',
        help=''
        )
    date_finish = fields.Date(
        string='Fecha Hasta',
        help=''
        )
    report_status = fields.Text(
        string='Report status',
        help='This field defines el status report'
        )
    wizard2 = fields.Boolean(
        string='Wizard2',
        help='This field defines if you press the button to generate ats'
        )
    report_errors = fields.Text(
        string='Report Errors',
        help='This field defines if there are errors in the generation of ATS'
        )
    include_electronic_document_in_ats = fields.Boolean(
        string=u'Incluir retenciones electrónicas emitidas a proveedores en el ATS',
        help=u'Active esta opción si desea incluir las retenciones electrónicas emitidas a proveedores en el ATS.'
        )

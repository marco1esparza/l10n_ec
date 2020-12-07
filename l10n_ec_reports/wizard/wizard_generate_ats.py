# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
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

from odoo.addons.l10n_ec_reports.models.l10n_ec_auxiliar_function import get_name_only_characters
 
ATS_FILENAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resources', 'ats_29_08_2016.xsd')
ATS_CONTENT = open(ATS_FILENAME, 'rb').read().strip()
 
#Documentos a reportar al SRI
_LOCAL_PURCHASE_DOCUMENT_CODES = ['01', '02', '03', '04', '05', '09', '11', '12', '19', '20', '21','41', '43', '45', '47', '48']
_FOREIGN_PURCHASE_DOCUMENT_CODES = ['15']
_SALE_DOCUMENT_CODES = ['02', '04', '05', '18', '41']
_WITHHOLD_CODES = ['07']

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
            report_status.append(u'\n')
        try:
            root = etree.XML(report_data.toxml(encoding='utf-8'))
            try:
                schema = etree.XMLSchema(etree.XML(ATS_CONTENT.strip()))
                if not schema.validate(root):
                    report_status.append(u'Ocurrieron los siguientes errores durante la validación del reporte ATS. '
                                         u'Contáctese con el administrador del servicio o el soporte técnico '
                                         u'indicándoles con exactitud los siguientes errores ocurridos: \n'
                                         u'>>> Inicio de errores <<<\n' + schema.error_log +
                                         u'\n>>> Fin de errores <<<')
                    ctx.update({'report_errors': True})
            except Exception as e:
                report_status.append(u'Hubo un error al validar el reporte: El archivo de validación de reporte '
                                     u'no es un XSD válido. Contáctese con el administrador del servicio o el soporte '
                                     u'técnico. Los detalles del error son los siguientes: ' + str(e))
                ctx.update({'report_errors': True})
        except Exception as e:
            report_status.append(u'Hubo un error al analizar el reporte: El archivo de reporte no es un XML '
                                 u'válido. Contáctese con el administrador del servicio o el soporte técnico. '
                                 u'Los detalles del error son los siguientes: ' + str(e))
            ctx.update({'report_errors': True})
        view = self.env.ref('l10n_ec_reports.view_wizard_ats_form')
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
        if not company.vat:
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
        razonSocial.appendChild(doc.createTextNode(get_name_only_characters(company.l10n_ec_legal_name)))
 
        atsanio = doc.createElement('Anio')
        main.appendChild(atsanio)
        atsanio.appendChild(doc.createTextNode(anio))
         
        atsmes = doc.createElement('Mes')
        main.appendChild(atsmes)
        atsmes.appendChild(doc.createTextNode(mes))

        suc = []
        printers = self.env['l10n_ec.sri.printer.point'].sudo().search([('company_id','=',self.env.user.company_id.id)])
        for printer in printers:
            suc.append(printer.name.split('-')[0])
        suc = list(set(suc))
        numEstabRuc = doc.createElement('numEstabRuc')
        main.appendChild(numEstabRuc)
        numEstabRuc.appendChild(doc.createTextNode(str(len(suc)).zfill(3))) 
 
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
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('l10n_latam_document_type_id.code', 'in', _LOCAL_PURCHASE_DOCUMENT_CODES),
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish)
        ])
        #TODO: evaluar crear otro tipo de documento para las compras de servicios al extranjero
        foreign_purchase_invoice_ids = account_move_obj.search([
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('state', '=', 'posted'),
            ('l10n_latam_document_type_id.code', 'in', _FOREIGN_PURCHASE_DOCUMENT_CODES),
            ('l10n_ec_sri_tax_support_id.code', 'not in', ['06','07']), #no se reportan importaciones de inventario
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
                #La factura que lleve retencion y no la tenga, debe ser reportada para su posterior revision
                if in_inv.line_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type in ['withhold_vat','withhold_income_tax']):
                    if not in_inv.l10n_ec_withhold_ids or not in_inv.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted'):
                        report_status.append(u'Factura ' + str(in_inv.l10n_latam_document_number) + u' no tiene retencion')
                 
                detallecompras = doc.createElement('detalleCompras')
                compras.appendChild(detallecompras)
     
                codSustento = doc.createElement('codSustento')
                detallecompras.appendChild(codSustento)
                vcodSustento = in_inv.l10n_ec_sri_tax_support_id.code or ''
                codSustento.appendChild(doc.createTextNode(vcodSustento))
                if not vcodSustento:
                    report_status.append(u'Factura ' + str(in_inv.l10n_latam_document_number) + u' no tiene codigo de sustento tributario')
     
                tpIdProv = doc.createElement('tpIdProv')
                detallecompras.appendChild(tpIdProv)
                tpIdProv.appendChild(doc.createTextNode(in_inv.l10n_ec_transaction_type))
     
                idProv = doc.createElement('idProv')
                detallecompras.appendChild(idProv)
                idProv.appendChild(doc.createTextNode(in_inv.partner_id.vat))
                 
                tipoComprobante = doc.createElement('tipoComprobante')
                detallecompras.appendChild(tipoComprobante)
                tipoComprobante.appendChild(doc.createTextNode(in_inv.l10n_latam_document_type_id.code))

                natural_sociedad = '02' if in_inv.commercial_partner_id.is_company else '01' #se guarda el valor para usarlo DRY
                transaction_type = get_name_only_characters(in_inv.l10n_ec_transaction_type)
                  
                if transaction_type == '03': #cuando es compra con pasaporte
                    tipoProv_ = doc.createElement('tipoProv')
                    detallecompras.appendChild(tipoProv_)
                    tipoProv_.appendChild(doc.createTextNode(natural_sociedad)) #el tipo de identificacion
                      
                    denoProv = doc.createElement('denoProv')
                    detallecompras.appendChild(denoProv)
                    vdenoProv = get_name_only_characters(in_inv.partner_id.name) #name_in_ascii
                    denoProv.appendChild(doc.createTextNode(vdenoProv))
                  
                if len(transaction_type) > 2:
                    #si no es un codigo sino un texto, agregamos el texto del error
                    report_status.append(transaction_type)
                
                #TODO: En v15 mover el dato de parte relacionada a la factura pues puede cambiar en el tiempo
                parteRel = doc.createElement('parteRel')
                detallecompras.appendChild(parteRel)
                pparteRel = doc.createTextNode('SI' if in_inv.commercial_partner_id.l10n_ec_related_part else 'NO')
                parteRel.appendChild(pparteRel)
     
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
                 
                #Porcentage de retencion
                #TODO: los codigos de retencion cambiaron, hay que hacer versiones con if por fechas
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
                if not in_inv.l10n_ec_invoice_country_id:
                    pago_local_extranjero = u'Compra no tiene identificado un Pais.'
                elif in_inv.l10n_ec_invoice_country_id == in_inv.company_id.country_id:
                    pago_local_extranjero = '01' # residente!
                else:
                    #si el pais es distinto
                    pago_local_extranjero = '02' #no residente
            
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
                    #TODO: falta implementar pagos a regimenes extranjeros
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
                        vpaisEfecPagoGen = doc.createTextNode(in_inv.l10n_ec_invoice_country_id.code or u'Compra no tiene identificado un Pais.')
                        paisEfecPagoGen.appendChild(vpaisEfecPagoGen)
                        
                    #Pais de residencia a quien se efectua el pago
                    #en regimen general se copia el paisEfecPagoGen
                    paisEfecPago = doc.createElement('paisEfecPago')
                    pagoExterior.appendChild(paisEfecPago)
                    vpaisEfecPago = doc.createTextNode(in_inv.l10n_ec_invoice_country_id.code or u'Compra no tiene identificado un Pais.')
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

                if in_inv.l10n_ec_total_with_tax >= 1000:
                    #excluimos pagos menores a USD 1000
                    formasDePago = doc.createElement('formasDePago')
                    detallecompras.appendChild(formasDePago)
                    for forma_pago in in_inv.l10n_ec_payment_method_id:
                        formaPago = doc.createElement('formaPago')
                        formasDePago.appendChild(formaPago)
                        vformaPago = doc.createTextNode(forma_pago.code)
                        formaPago.appendChild(vformaPago)
                 
                #2.2.1 DATA RETENCIONES RENTA
                self.write_purchase_withhold_income_tax_section(doc, main, in_inv, detallecompras, report_status)
     
                #2.2.2 DATA NOTAS DE CREDITO Y NOTAS DE DEBITO
                self.write_purchase_credit_and_debit_note_section(doc, main, in_inv, detallecompras, report_status)
                 
                #TODO jm: implementar reembolsos y descomentar la sig linea
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
        income_tax_withholds = in_inv.l10n_ec_withhold_ids.l10n_ec_withhold_line_ids.filtered(
            lambda l: l.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_tax'] and l.move_id.state == 'posted'
        ).sorted(key=lambda l: l.tax_id.l10n_ec_code_ats) 
        if income_tax_withholds and in_inv.l10n_latam_document_type_id.code not in ['41'] and self.include_electronic_document_in_ats:
            #cuando son reembolsos no se reporta el detalle de valores retenidos (el dimm no permite)
            air_form = doc.createElement('air')
            detallecompras.appendChild(air_form)
            for tax_line in income_tax_withholds:
                 
                detalleAir_form = doc.createElement('detalleAir')
                air_form.appendChild(detalleAir_form)
                 
                codigoRet = doc.createElement('codRetAir')
                detalleAir_form.appendChild(codigoRet)
                vcodigoRet = tax_line.tax_id.l10n_ec_code_ats
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
                pporcentajeRet = doc.createTextNode('{0:.2f}'.format(abs(tax_line.tax_id.amount)))
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
            
            withholds = in_inv.l10n_ec_withhold_ids.filtered(lambda l: l.state == 'posted') 
            for withhold in withholds: 
                #De haber mas de una retencion (escenario imposible con Odoo)
                #se deberia poner estabRetencion2 para la segunda retencion
                if withhold.edi_state != 'sent':
                    #si la factura tiene novedades agregamos al msg de error
                    #ayuda a identificar facturas sin retencion entre otros problemas
                    report_status.append(u'Retencion ' + str(withhold.l10n_latam_document_number) + u', documento electronico por enviar.')
 
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
                autRetencion1.appendChild(doc.createTextNode(str(withhold.l10n_ec_authorization or '').strip()))
 
                fechaEmiRet1 = doc.createElement('fechaEmiRet1')
                detallecompras.appendChild(fechaEmiRet1)
                pfechaEmiRet1 = doc.createTextNode(self._getFormatDates(withhold.invoice_date))
                fechaEmiRet1.appendChild(pfechaEmiRet1)
  
    @api.model
    def write_purchase_credit_and_debit_note_section(self, doc, main, in_inv, detallecompras, report_status):
        '''
        Escribe la seccion de notas de credito y notas de debito en compras en el ats
        '''
        if in_inv.l10n_latam_document_type_id.code=='04' or in_inv.l10n_latam_document_type_id.code=='05':
            docModificado = doc.createElement('docModificado')
            detallecompras.appendChild(docModificado)
            vdocModificado = in_inv.reversed_entry_id.l10n_latam_document_type_id.code or ''
            pdocModificado = doc.createTextNode(vdocModificado)
            docModificado.appendChild(pdocModificado)
            if not vdocModificado:
                #si no es un codigo sino un texto, agregamos el texto del error
                report_status.append(u'Factura ' + str(in_inv.reversed_entry_id.l10n_latam_document_number) + u' no tiene tipo de documento.')
            else:
                pass #do nothing
 
            estabModificado = doc.createElement('estabModificado')
            detallecompras.appendChild(estabModificado)
            pestabModificado = doc.createTextNode(in_inv.reversed_entry_id.l10n_latam_document_number[0:3])
            estabModificado.appendChild(pestabModificado)
 
            ptoEmiModificado = doc.createElement('ptoEmiModificado')
            detallecompras.appendChild(ptoEmiModificado)
            pptoEmiModificado = doc.createTextNode(in_inv.reversed_entry_id.l10n_latam_document_number[4:7])
            ptoEmiModificado.appendChild(pptoEmiModificado)
 
            secModificado = doc.createElement('secModificado')
            detallecompras.appendChild(secModificado)
            psecModificado = doc.createTextNode(in_inv.reversed_entry_id.l10n_latam_document_number[8:])
            secModificado.appendChild(psecModificado)
 
            autModificado = doc.createElement('autModificado')
            detallecompras.appendChild(autModificado)
            Modificadoauth = doc.createTextNode(in_inv.reversed_entry_id.l10n_ec_authorization or '')
            autModificado.appendChild(Modificadoauth)

    @api.model
    def write_purchase_refund_section(self, doc, main, in_inv, detallecompras, report_status):
        '''
        Escribe la seccion de reembolsos en compras en el ats
        '''
        #TODO: Validar la implementacion para los tipos de documento 47 y 48
        if in_inv.l10n_latam_document_type_id.code in ['41','47','48'] and in_inv.refund_ids:
            reembolsos = doc.createElement('reembolsos')
            detallecompras.appendChild(reembolsos)
            for refund_id in in_inv.refund_ids:
                reembolso = doc.createElement('reembolso')
                reembolsos.appendChild(reembolso)
                tipoComprobanteReemb = doc.createElement('tipoComprobanteReemb')
                reembolso.appendChild(tipoComprobanteReemb)
                tipoComprobanteReemb.appendChild(doc.createTextNode(refund_id.l10n_latam_document_type_id.code))
 
                idProvReemb = doc.createElement('tpIdProvReemb')
                reembolso.appendChild(idProvReemb)
                vidProvReemb = refund_id.transaction_type
                idProvReemb.appendChild(doc.createTextNode(vidProvReemb))
                 
                if len(vidProvReemb) > 2:
                    #si no es un codigo sino un texto, agregamos el texto del error
                    report_status.append(vidProvReemb)
                 
                idProvReemb = doc.createElement('idProvReemb')
                reembolso.appendChild(idProvReemb)
                idProvReemb.appendChild(doc.createTextNode(refund_id.partner_id.vat))
                 
                establecimientoReemb = doc.createElement('establecimientoReemb')
                reembolso.appendChild(establecimientoReemb)
                establecimientoReemb.appendChild(doc.createTextNode(refund_id.number[0:3]))
                 
                puntoEmisionReemb = doc.createElement('puntoEmisionReemb')
                reembolso.appendChild(puntoEmisionReemb)
                puntoEmisionReemb.appendChild(doc.createTextNode(refund_id.number[4:7]))
                 
                secuencialReemb = doc.createElement('secuencialReemb')
                reembolso.appendChild(secuencialReemb)
                vsecuencialReemb = refund_id.number[8:]
                secuencialReemb.appendChild(doc.createTextNode(vsecuencialReemb or ''))
                if not vsecuencialReemb:
                    #si no es un codigo sino un texto, agregamos el texto del error
                    report_status.append(u'Dentro del reembolso ' + str(refund_id.move_id.l10n_latam_document_number) + \
                                         u', la factura ' + refund_id.number + \
                                         u' no tiene secuencial de reembolso')
                else:
                    pass #do nothing
                 
                fechaEmisionReemb = doc.createElement('fechaEmisionReemb')
                reembolso.appendChild(fechaEmisionReemb)
                fechaEmisionReemb.appendChild(doc.createTextNode(self._getFormatDates(refund_id.creation_date)))
                 
                autorizacionReemb = doc.createElement('autorizacionReemb')
                reembolso.appendChild(autorizacionReemb)
                vautorizacionReemb = refund_id.authorization
                autorizacionReemb.appendChild(doc.createTextNode(vautorizacionReemb or ''))
                if not vautorizacionReemb:
                    #si no es un codigo sino un texto, agregamos el texto del error
                    report_status.append(u'Dentro del reembolso ' + str(refund_id.move_id.l10n_latam_document_number) + \
                                         u', la factura ' + refund_id.number + \
                                         u' no tiene autorizacion')
 
                elif len(vautorizacionReemb) not in [10, 37, 49]:
                    report_status.append(u'Dentro del reembolso ' + str(refund_id.move_id.l10n_latam_document_number) + \
                                         u', la factura ' + refund_id.number + \
                                         u' tiene una autorizacion incompleta')
 
                else:
                    pass #do nothing
                baseImponibleReemb = doc.createElement('baseImponibleReemb')
                reembolso.appendChild(baseImponibleReemb)
                aux = doc.createTextNode('%.2f' %  abs(float(refund_id.base_vat_0)))
                baseImponibleReemb.appendChild(aux)
                 
                baseImpGravReemb = doc.createElement('baseImpGravReemb')
                reembolso.appendChild(baseImpGravReemb)
                aux = doc.createTextNode('%.2f' % abs(float(refund_id.base_vat_no0)))
                baseImpGravReemb.appendChild(aux)
                 
                baseNoGraIvaReemb = doc.createElement('baseNoGraIvaReemb')
                reembolso.appendChild(baseNoGraIvaReemb)
                aux = doc.createTextNode('%.2f' % abs(float(refund_id.no_vat_amount)))
                baseNoGraIvaReemb.appendChild(aux)
 
                baseImpExeReemb = doc.createElement('baseImpExeReemb')
                reembolso.appendChild(baseImpExeReemb)
                aux = doc.createTextNode('%.2f' % abs(float(refund_id.base_tax_free)))
                baseImpExeReemb.appendChild(aux)
                 
                montoIceRemb = doc.createElement('montoIceRemb')
                reembolso.appendChild(montoIceRemb)
                aux = doc.createTextNode('%.2f' % abs(float(refund_id.ice_amount)))
                montoIceRemb.appendChild(aux)
 
                montoIvaRemb = doc.createElement('montoIvaRemb')
                reembolso.appendChild(montoIvaRemb)
                aux = doc.createTextNode('%.2f' % abs(float(refund_id.vat_amount_no0)))
                montoIvaRemb.appendChild(aux)

    @api.model
    def write_sale_section(self, doc, main, report_status):
        '''
        Escribe la seccion de ventas en el ats
        '''
        init_time = tm()
        total_ventas = 0.0
        account_move_obj = self.env['account.move'].sudo()
        # Se ordenan las facturas por RUC de la factura, en vez del partner_id
        # La funcion _get_sales_info se encarga de agrupar ya por el partner_id.vat
        # y de pre-procesarlas asi
        # Se excluyen aquellas que son exportaciones
        out_invoices = self._get_sales_info(account_move_obj.search([
            ('move_type', 'in', ['out_invoice','out_refund']),
            ('state', '=', 'posted'),
            ('l10n_latam_document_type_id.code', 'in', _SALE_DOCUMENT_CODES),
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish),
            '|',('fiscal_position_id', 'not in', [self.env.ref('l10n_ec.fp_foreing_company_exports').id, self.env.ref('l10n_ec.fp_foreing_person_exports').id]),
            ('fiscal_position_id', '=', False)
        ], order='partner_id, l10n_latam_document_type_id, invoice_date'))        
        last_time = tm()
        ejecution_time = last_time - init_time
        _logger.info(u'Tiempo busqueda facturas de ventas %s seg.', str(ejecution_time))
        init_time = tm()
        if out_invoices:
            ventas_form = doc.createElement('ventas')
            main.appendChild(ventas_form)
            for out_inv in out_invoices:
                #los docs electronicos no suman al total de ventas del talon resumen
                if out_invoices[out_inv]['tipoEmision'] == 'F':
                    total_ventas += out_invoices[out_inv]['amount_untaxed_signed']
  
                detalle_ventas_form = doc.createElement('detalleVentas')
                ventas_form.appendChild(detalle_ventas_form)
  
                tpIdCliente = doc.createElement('tpIdCliente')
                detalle_ventas_form.appendChild(tpIdCliente)
                vtpIdCliente = out_invoices[out_inv]['tpIdCliente']
                if len(vtpIdCliente) > 2:
                    #si no es un codigo sino un texto, agregamos el texto del error
                    report_status.append(vtpIdCliente)
                ptpIdCliente = doc.createTextNode(vtpIdCliente)
                tpIdCliente.appendChild(ptpIdCliente)
  
                idCliente = doc.createElement('idCliente')
                detalle_ventas_form.appendChild(idCliente)
                pidCliente = doc.createTextNode(out_invoices[out_inv]['idCliente'])
                idCliente.appendChild(pidCliente)
  
                if not ((out_invoices[out_inv]['tpIdCliente'] == '07' and out_invoices[out_inv]['tipoComprobante'] in ('18','41')) or \
                        out_invoices[out_inv]['tpIdCliente'] == '07' or out_invoices[out_inv]['idCliente'] == '9999999999999'):
                        parteRelVtas = doc.createElement('parteRelVtas')
                        detalle_ventas_form.appendChild(parteRelVtas)
                        # Para Ecommerce related_part no se puede hacer nada asi que toma
                        # el valor por defecto en la creacion del partner
                        pparteRel = doc.createTextNode('SI' if out_invoices[out_inv]['parteRelVtas'] else 'NO')
                        parteRelVtas.appendChild(pparteRel)
                  
                if out_invoices[out_inv]['tpIdCliente'] == '06':
                        tipoCliente = doc.createElement('tipoCliente')
                        detalle_ventas_form.appendChild(tipoCliente)
                        data_tipoCliente = False
                        if out_invoices[out_inv]['tipoCliente'] == '06':
                            data_tipoCliente = '01'
                        elif out_invoices[out_inv]['tipoCliente'] == '08':
                            data_tipoCliente = '02'
                        else: 
                            #El tipo de cliente no es persona natural ni empresa extranjera
                            mensaje = u' '.join((u'El cliente con VAT', out_invoices[out_inv]['idCliente'],
                                      u'tiene mal identificado el tipo de cliente:', out_invoices[out_inv]['tipoCliente']))
                            data_tipoCliente = mensaje 
                            report_status.append(mensaje)
                        ptipoCliente = doc.createTextNode(data_tipoCliente)
                        tipoCliente.appendChild(ptipoCliente)
  
                        denoCli = doc.createElement('denoCli')
                        detalle_ventas_form.appendChild(denoCli)
                        pdenoCli = doc.createTextNode(out_invoices[out_inv]['denoCli'])
                        denoCli.appendChild(pdenoCli)
  
                tipoComprobante = doc.createElement('tipoComprobante')
                detalle_ventas_form.appendChild(tipoComprobante)
                ptipoComprobante = doc.createTextNode(out_invoices[out_inv]['tipoComprobante'])
                tipoComprobante.appendChild(ptipoComprobante)
  
                tipoEmision = doc.createElement('tipoEmision')
                detalle_ventas_form.appendChild(tipoEmision)
                ptipoEmision = doc.createTextNode(out_invoices[out_inv]['tipoEmision'])
                tipoEmision.appendChild(ptipoEmision)
  
                numeroComprobantes = doc.createElement('numeroComprobantes')
                detalle_ventas_form.appendChild(numeroComprobantes)
                pnumeroComprobantes = doc.createTextNode(str(out_invoices[out_inv]['numeroComprobantes']))
                numeroComprobantes.appendChild(pnumeroComprobantes)
  
                baseNoGraIva = doc.createElement('baseNoGraIva')  # Base imponible no objeto de iva
                detalle_ventas_form.appendChild(baseNoGraIva)
                pbaseNoGraIva = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['baseNoGraIva']) or 0.00))
                baseNoGraIva.appendChild(pbaseNoGraIva)
  
                baseImponible = doc.createElement('baseImponible')  # Base imponible tarifa 0% iva
                detalle_ventas_form.appendChild(baseImponible)
                pbaseImponible = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['baseImponible']) or 0.00))
                baseImponible.appendChild(pbaseImponible)
  
                baseImpGrav = doc.createElement('baseImpGrav')  # Base imponible tarifa diferente de 0% iva
                detalle_ventas_form.appendChild(baseImpGrav)
                pbaseImpGrav = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['baseImpGrav'])or 0.00))
                baseImpGrav.appendChild(pbaseImpGrav)
  
                montoIva = doc.createElement('montoIva')
                detalle_ventas_form.appendChild(montoIva)
                pmontoIva = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['montoIva'])or 0.00))
                montoIva.appendChild(pmontoIva)
                
                montoIceV = doc.createElement('montoIce')
                detalle_ventas_form.appendChild(montoIceV)
                pmontoIceV = doc.createTextNode('{0:.2f}'.format(0.00))
                montoIceV.appendChild(pmontoIceV)
                
                # TODO: pendiente de migrar  compensacion
                valorRetIva = doc.createElement('valorRetIva')
                detalle_ventas_form.appendChild(valorRetIva)
                pvalorRetIva = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['valorRetIva'])))
                valorRetIva.appendChild(pvalorRetIva)
                
                valorRetRenta = doc.createElement('valorRetRenta')
                detalle_ventas_form.appendChild(valorRetRenta)
                pvalorRetRenta = doc.createTextNode('{0:.2f}'.format(float(out_invoices[out_inv]['valorRetRenta'])))
                valorRetRenta.appendChild(pvalorRetRenta)
  
                pay_codes = []
                if out_invoices[out_inv]['formas_pago'] and out_invoices[out_inv]['tipoComprobante'] not in ['04']:
                    #excluimos notas de credito, codigo 04
                    for payment_code in out_invoices[out_inv]['formas_pago']:
                        if payment_code != False:
                            pay_codes += [payment_code]
                    formasDePagoV = doc.createElement('formasDePago')
                    detalle_ventas_form.appendChild(formasDePagoV)
                    for payment_code in pay_codes:
                        formaPagoV = doc.createElement('formaPago')
                        formasDePagoV.appendChild(formaPagoV)
                        vformaPagoV = doc.createTextNode(payment_code)
                        formaPagoV.appendChild(vformaPagoV)
              
            ventasEstablecimiento = doc.createElement('ventasEstablecimiento')
            main.appendChild(ventasEstablecimiento)
            
            shops = []
            printers = self.env['l10n_ec.sri.printer.point'].sudo().search([('company_id','=',self.env.user.company_id.id)])
            for printer in printers:
                shops.append(printer.name.split('-')[0])
            shops = list(set(shops))
            for shop in shops:
                ventaEst = doc.createElement('ventaEst')
                ventasEstablecimiento.appendChild(ventaEst)
                codEstab = doc.createElement('codEstab')
                ventaEst.appendChild(codEstab)
                valventaEst = doc.createTextNode(str(shop).zfill(3))
                codEstab.appendChild(valventaEst)
                ventasEstab = doc.createElement('ventasEstab')
                ventaEst.appendChild(ventasEstab)
                total_shop = self.get_total_shop(self.date_start, self.date_finish, shop)['total']
                valventaEst = doc.createTextNode('{0:.2f}'.format(total_shop))
                ventasEstab.appendChild(valventaEst)
              
        last_time = tm()
        ejecution_time = last_time - init_time
        _logger.info(u'Tiempo ejecucion seccion ventas %s seg.', str(ejecution_time))
        return total_ventas

    @api.model
    def write_canceled_document_section(self, doc, main, report_status):
        '''
        Escribe la seccion de documentos anulados en el ats
        '''
        init_time = tm()
        void_invoices = self.env['account.move'].sudo().search([
            ('move_type', 'in', ['out_invoice','out_refund']),
            ('state', '=', 'cancel'),
            ('l10n_latam_document_type_id.code', 'in', _SALE_DOCUMENT_CODES),
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish)
        ])
        void_withholds = self.env['account.move'].sudo().search([
            ('move_type', 'in', ['entry']),
            ('state', '=', 'cancel'),
            ('l10n_latam_document_type_id.code', 'in', _WITHHOLD_CODES),
            ('l10n_ec_withhold_type', 'in', ['in_withhold']),
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish)
        ])
#         #TODO jm: implementar guias de remision en v15
#         void_deliveries = self.env['stock.picking'].sudo().search([
#             ('date','<=', self.date_finish),
#             ('date','>=',self.date_start),
#             ('is_waybill','=',True), #identifica las guias de remision emitidas
#             ('state','=','cancel')
#         ])
         
        if void_invoices or void_withholds: #or void_deliveries:
            anulados_form = doc.createElement('anulados')
            main.appendChild(anulados_form)
         
        for void_invoice in void_invoices:
            detalle_anuladas_form = doc.createElement('detalleAnulados')
            anulados_form.appendChild(detalle_anuladas_form)
 
            tipoComprobante = doc.createElement('tipoComprobante')
            detalle_anuladas_form.appendChild(tipoComprobante)
            ptipoComprobante = doc.createTextNode(void_invoice.l10n_latam_document_type_id.code)
            tipoComprobante.appendChild(ptipoComprobante)
 
            establecimiento = doc.createElement('establecimiento')
            detalle_anuladas_form.appendChild(establecimiento)
            pestablecimiento = doc.createTextNode(void_invoice.l10n_latam_document_number[0:3])
            establecimiento.appendChild(pestablecimiento)
 
            puntoEmision = doc.createElement('puntoEmision')
            detalle_anuladas_form.appendChild(puntoEmision)
            ppuntoEmision = doc.createTextNode(void_invoice.l10n_latam_document_number[4:7])
            puntoEmision.appendChild(ppuntoEmision)
 
            secuencialInicio = doc.createElement('secuencialInicio')
            detalle_anuladas_form.appendChild(secuencialInicio)
            psecuencialInicio = doc.createTextNode(void_invoice.l10n_latam_document_number[8:])
            secuencialInicio.appendChild(psecuencialInicio)
 
            secuencialFin = doc.createElement('secuencialFin')
            detalle_anuladas_form.appendChild(secuencialFin)
            psecuencialFin = doc.createTextNode(void_invoice.l10n_latam_document_number[8:])
            secuencialFin.appendChild(psecuencialFin)
 
            autorizacion = doc.createElement('autorizacion')
            detalle_anuladas_form.appendChild(autorizacion)
            autorizacion.appendChild(doc.createTextNode(str(void_invoice.l10n_ec_authorization or '').strip()))
        
        for void_withhold in void_withholds:
            detalle_anuladas_form = doc.createElement('detalleAnulados')
            anulados_form.appendChild(detalle_anuladas_form)
 
            tipoComprobante = doc.createElement('tipoComprobante')
            detalle_anuladas_form.appendChild(tipoComprobante)
            ptipoComprobante = doc.createTextNode('07')
            tipoComprobante.appendChild(ptipoComprobante)
 
            establecimiento = doc.createElement('establecimiento')
            detalle_anuladas_form.appendChild(establecimiento)
            pestablecimiento = doc.createTextNode(void_withhold.l10n_latam_document_number[0:3])
            establecimiento.appendChild(pestablecimiento)
 
            puntoEmision = doc.createElement('puntoEmision')
            detalle_anuladas_form.appendChild(puntoEmision)
            ppuntoEmision = doc.createTextNode(void_withhold.l10n_latam_document_number[4:7])
            puntoEmision.appendChild(ppuntoEmision)
 
            secuencialInicio = doc.createElement('secuencialInicio')
            detalle_anuladas_form.appendChild(secuencialInicio)
            psecuencialInicio = doc.createTextNode(void_withhold.l10n_latam_document_number[8:])
            secuencialInicio.appendChild(psecuencialInicio)
 
            secuencialFin = doc.createElement('secuencialFin')
            detalle_anuladas_form.appendChild(secuencialFin)
            psecuencialFin = doc.createTextNode(void_withhold.l10n_latam_document_number[8:])
            secuencialFin.appendChild(psecuencialFin)
 
            autorizacion = doc.createElement('autorizacion')
            detalle_anuladas_form.appendChild(autorizacion)
            vAutorizacion = void_withhold.l10n_ec_authorization
            autorizacion.appendChild(doc.createTextNode(vAutorizacion or ''))
            if not vAutorizacion:
                #si no es un codigo sino un texto, agregamos el texto del error
                report_status.append(u'La retencion ANULADA ' + void_withhold.l10n_latam_document_number + \
                                     u' no tiene autorizacion.')
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
#             cancelauth = doc.createTextNode(str(void_delivery.l10n_ec_authorization).strip())
#             autorizacion.appendChild(cancelauth)
        
        last_time = tm()
        ejecution_time = last_time - init_time
        _logger.info(u'Tiempo ejecucion seccion anulados %s seg.', str(ejecution_time))
     
    @api.model
    def _report_errors(self):
        '''
        Este método devuelve un mensaje de error si hubo problemas en la validación del ATS
        '''
        msgs = ''
        if self._context.get('report_errors'):
            msgs = u'Existen novedades en la generación del ATS, para más detalles, haga clic en el archivo "Errores.txt"'
        return msgs

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
            for ats_line in invoice.refund_ids:
                total_refund += ats_line.base_vat_0 + ats_line.base_vat_no0 + ats_line.base_tax_free + ats_line.no_vat_amount
        return total_refund
     
    @api.model
    def _get_sales_info(self, invoices):
        '''
        '''
        group_sales = {}
        if invoices:
            for invoice in invoices:
                if invoice._fields.get('edi_document_ids', False):
                    if invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'l10n_ec_tax_authority'):
                        emission_type = 'E'
                    else:
                        emission_type = 'F'
                else:
                    emission_type = 'F'
                id_partner = str(invoice.partner_id.vat) + '-' + str(invoice.l10n_latam_document_type_id.code) + '-' + emission_type
                values = group_sales.get(id_partner, {
                            'numeroComprobantes': 0,
                            'baseNoGraIva': 0.0,
                            'baseImponible': 0.0,
                            'baseImpGrav': 0.0,
                            'montoIva': 0.0,
                            'valorRetIva': 0.0,
                            'valorRetRenta': 0.0,
                            'amount_untaxed_signed': 0.0,
                            'formas_pago': []
                        })
                tax_with_vat = 0.0
                tax_with_income = 0.0
                for withhold in invoice.l10n_ec_withhold_ids:
                    if withhold.state == 'posted':
                        if len(withhold.l10n_ec_withhold_origin_ids) == 1: 
                            #cuando es mayor a uno es una retencion de tarjeta de credito
                            #y no se reportan al ATS (o al menos nuestros clientes no requieren esta funcionalidad)
                            for line in withhold.l10n_ec_withhold_line_ids:
                                if line.tax_id.tax_group_id.l10n_ec_type == 'withhold_vat':
                                    tax_with_vat += line.amount
                                elif line.tax_id.tax_group_id.l10n_ec_type == 'withhold_income_tax':
                                    tax_with_income += line.amount
                values.update({
                    'tpIdCliente': invoice.l10n_ec_transaction_type,
                    'parteRelVtas': invoice.partner_id.l10n_ec_related_part,
                    'idCliente': invoice.partner_id.vat,
                    'tipoComprobante': invoice.l10n_latam_document_type_id.code,
                    'tipoEmision': emission_type,
                    'numeroComprobantes': values['numeroComprobantes'] + 1,
                    'baseNoGraIva': values['baseNoGraIva'] + invoice.l10n_ec_base_tax_free + invoice.l10n_ec_base_not_subject_to_vat,
                    'baseImponible': values['baseImponible'] + invoice.l10n_ec_base_cero_iva,
                    'baseImpGrav': values['baseImpGrav'] + invoice.l10n_ec_base_doce_iva,
                    'montoIva': values['montoIva'] + invoice.l10n_ec_vat_doce_subtotal,
                    'valorRetIva': values['valorRetIva'] + tax_with_vat,
                    'valorRetRenta': values['valorRetRenta'] + tax_with_income,
                    'formas_pago': list(set(values['formas_pago'] + [line.payment_method_id.code for line in invoice.l10n_ec_invoice_payment_method_ids])),
                    'compensaciones': {'tipoCompe': '0', 'monto': 0}, #implementar
                    'amount_untaxed_signed': values['amount_untaxed_signed'] + invoice.amount_untaxed_signed
                })
                # La identificacion para tipoCliente y denoCli es requerida
                # unicamente si el codigo del transaction_type en
                # la factura es '06'
                if invoice.l10n_ec_transaction_type == '06':
                    values.update({
                        'tipoCliente': invoice.partner_id.get_invoice_ident_type(), 
                        'denoCli': get_name_only_characters(invoice.partner_id.name)
                    })
                group_sales[id_partner] = values
        return group_sales

    @api.model
    def get_total_shop(self, date_start, date_finish, shop):
        '''
        '''
        precalculated = self._precalculate_sums(date_start, date_finish)
        return precalculated['by_shop'].get(shop, {'total': 0.0, 'ivaComp': 0.0})
 
    @api.model
    def _precalculate_sums(self, date_start, date_finish):
        '''
        Precalcula sumas de valores a diferentes niveles (totales, por tienda, ...).
 
        ADVERTENCIA: el total general es más grande que el total por tiendas porque eventualmente
          no se asignan parte del amount_untaxed en base_0 ni base_12. Esto puede deberse a una mala
          logica para llenar base_0 y base_12 pero eso ya es problema de la factura.
 
        Hay que revisar si queremos eso o cambiamos para poner amount_untaxed en lugar de la suma de
          esos dos campos.
        '''
        total = 0
        _precalculated = {
            'total': 0.0,
            'by_shop': {}
        }
        invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice','out_refund']),
            ('state', '=', 'posted'),
            ('l10n_latam_document_type_id.code', 'in', _SALE_DOCUMENT_CODES),
            ('invoice_date','>=', self.date_start),
            ('invoice_date','<=', self.date_finish)
        ])
        for invoice in invoices:
            manual = True
            if invoice._fields.get('edi_document_ids', False):
                if invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'l10n_ec_tax_authority'):
                    manual = False
            if manual:
                shop = invoice.l10n_ec_printer_id.name[:3]
                _precalculated['by_shop'].setdefault(shop, {'total': 0.0, 'ivaComp': 0.0})
                subtotal = float('{0:.2f}'.format(invoice.l10n_ec_base_doce_iva)) + float('{0:.2f}'.format(invoice.l10n_ec_base_cero_iva))
                subtotal = subtotal * (1 if invoice.move_type == 'out_invoice' else -1)
                _precalculated['by_shop'][shop]['total'] += subtotal
                total += float('{0:.2f}'.format(subtotal))
        _precalculated['total'] = total
        return _precalculated

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

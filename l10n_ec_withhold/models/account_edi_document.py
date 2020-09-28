# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from lxml import etree
import base64

from odoo.addons.l10n_ec_edi.models.common_methods import clean_xml, validate_xml_vs_xsd, XSD_SRI_100_RETENCION


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _l10n_ec_generate_request_xml_file(self):
        '''
        Escribe el archivo xml request en el campo designado para ello
        '''
        res = super(AccountEdiDocument, self)._l10n_ec_generate_request_xml_file()
        #generamos y validamos el documento
        if self.move_id.type in ('entry') and self.move_id.l10n_ec_withhold_type in ['in_withhold'] and self.move_id.l10n_latam_document_type_id.code in ['07']:
            etree_content = self._l10n_ec_get_xml_request_for_withhold()
            xml_content = clean_xml(etree_content)
            try: #validamos el XML contra el XSD
                if self.move_id.type in ('entry') and self.move_id.l10n_ec_withhold_type in ['in_withhold'] and self.move_id.l10n_latam_document_type_id.code in ['07']: #Retenciones en compras
                    validate_xml_vs_xsd(xml_content, XSD_SRI_100_RETENCION)
            except ValueError: 
                raise UserError(u'No se ha enviado al servidor: ¿quiza los datos estan mal llenados?:' + ValueError[1])        
            self.l10n_ec_request_xml_file_name = self.move_id.name + '_draft.xml'
            self.l10n_ec_request_xml_file = base64.encodestring(xml_content)
        return res
    
    @api.model
    def _l10n_ec_get_xml_request_for_withhold(self):
        '''
        '''
        def get_electronic_tax_type_code(withhold_category_dummy):
            '''Retorna el codigo numero solicitado en el doc electronico del SRI 
            para cada tipo de impuesto de retencion
            '''
            if withhold_category_dummy == 'withhold_income_tax': return 1
            elif withhold_category_dummy == 'withhold_vat': return 2 
            elif withhold_category_dummy == 'other': return 6

        def get_electronic_tax_code(withhold_category_dummy, percentage, tax_code):
            """
            Analiza si un codigo de impuesto es de tipo IVA y lo devuelve segun los
            parametros del SRI.
            :return: Devuelve un numero entero del codigo del impuesto.
            """
            code = False
            if withhold_category_dummy == 'withhold_income_tax' or withhold_category_dummy == 'isd':
                code = tax_code
            elif withhold_category_dummy == 'withhold_vat':
                if abs(percentage) == 0.0: #retencion iva 0%
                    code = 7
                elif abs(percentage) == 10.0:
                    code = 9
                elif abs(percentage) == 20.0:
                    code = 10
                elif abs(percentage) == 30.0:
                    code = 1
                elif abs(percentage) == 70.0:
                    code = 2
                elif abs(percentage) == 100.0:
                    code = 3
            if not code:
                raise ValidationError('El impuesto "%s" no tiene definido ningun codigo.' % line.tax_id.name)
            return code

        # INICIO CREACION DE LA RETENCION
        withhold = etree.Element('comprobanteRetencion', {'id': 'comprobante', 'version': '1.0.0'})
        # CREACION INFO TRIBUTARIA
        infoTributaria = etree.SubElement(withhold, 'infoTributaria')
        infoTribElements = [
            ('ambiente', self.move_id.company_id.l10n_ec_environment_type),
            ('tipoEmision', '1'),
            ('razonSocial', self.move_id.company_id.l10n_ec_legal_name)
        ]
        if self.move_id.company_id.partner_id.l10n_commercial_name:
            infoTribElements.append(('nombreComercial', self.move_id.company_id.partner_id.l10n_commercial_name))
        infoTribElements.extend([
            ('ruc', self.move_id.company_id.partner_id.vat),
            ('claveAcceso', self.l10n_ec_access_key),
            ('codDoc', '07'),
            ('estab', self.move_id.l10n_latam_document_number[0:3]),
            ('ptoEmi', self.move_id.l10n_latam_document_number[4:7]),
            ('secuencial', self.move_id.l10n_latam_document_number[8:]),
            ('dirMatriz', self.move_id.company_id.street)
        ])
        self.create_TreeElements(infoTributaria, infoTribElements)
        # CREACION INFO Retencion
        infoCompRetencion = etree.SubElement(withhold, 'infoCompRetencion')
        infoCompRetencionElements = [
            ('fechaEmision', datetime.strftime(self.move_id.invoice_date,'%d/%m/%Y')),
            ('dirEstablecimiento', self.move_id.l10n_ec_printer_id.printer_point_address)
        ]
        if self.move_id.company_id.l10n_ec_special_contributor_number:
            infoFactElements.append(('contribuyenteEspecial', self.move_id.company_id.l10n_ec_special_contributor_number))
        get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
        infoCompRetencionElements.extend([
            ('obligadoContabilidad', 'SI' if self.move_id.company_id.l10n_ec_forced_accounting else 'NO'),
            ('tipoIdentificacionSujetoRetenido', self.move_id.partner_id.get_invoice_ident_type()),
            ('razonSocialSujetoRetenido', get_invoice_partner_data['invoice_name']),
            ('identificacionSujetoRetenido', get_invoice_partner_data['invoice_vat']),
            ('periodoFiscal', str(self.move_id.invoice_date.month).zfill(2) + '/' + str(self.move_id.invoice_date.year))
        ])
        self.create_TreeElements(infoCompRetencion, infoCompRetencionElements)
        # CREACION DE LOS IMPUESTOS
        # DETALLES DE LA RETENCION
        detalles = etree.SubElement(withhold, 'impuestos')        
        for line in self.move_id.l10n_ec_withhold_line_ids:
            detalle_data = []
            porc_ret = abs(line.tax_id.amount)
            type_ec = line.tax_id.tax_group_id.l10n_ec_type
            tax_code = line.tax_id.l10n_ec_code_ats
            impuesto = self.create_SubElement(detalles, 'impuesto')
            detalle_data.append(('codigo', get_electronic_tax_type_code(type_ec)))
            detalle_data.append(('codigoRetencion', get_electronic_tax_code(type_ec, porc_ret, tax_code)))
            detalle_data.append(('baseImponible', line.base))
            detalle_data.append(('porcentajeRetener', '{0:.2f}'.format(porc_ret)))
            detalle_data.append(('valorRetenido', round(line.amount, 2)))
            detalle_data.append(('codDocSustento', line.move_id.l10n_ec_withhold_origin_ids[0].l10n_latam_document_type_id.code))
            detalle_data.append(('numDocSustento', line.move_id.l10n_ec_withhold_origin_ids[0].l10n_latam_document_number.replace('-','')))
            detalle_data.append(('fechaEmisionDocSustento', datetime.strftime(line.move_id.l10n_ec_withhold_origin_ids[0].invoice_date,'%d/%m/%Y')))
            self.create_TreeElements(impuesto, detalle_data)
        infoAdicional = self.create_SubElement(withhold, 'infoAdicional')
        if get_invoice_partner_data['invoice_email']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'email'}, text=get_invoice_partner_data['invoice_email'])
        if get_invoice_partner_data['invoice_address']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'direccion'}, text=get_invoice_partner_data['invoice_address'])
        if get_invoice_partner_data['invoice_phone']:
            self.create_SubElement(infoAdicional, 'campoAdicional', attrib={'nombre': 'telefono'}, text=get_invoice_partner_data['invoice_phone'])
        return withhold

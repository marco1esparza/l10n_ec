# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from lxml import etree
import base64

from odoo.addons.l10n_ec_edi.models.common_methods import clean_xml, validate_xml_vs_xsd, XSD_SRI_110_GUIA_REMISION

from odoo.addons.l10n_ec_edi.models.account_edi_document import _MICROCOMPANY_REGIME_LABEL

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _l10n_ec_generate_request_xml_file(self):
        '''
        Escribe el archivo xml request en el campo designado para ello
        '''
        res = super(AccountEdiDocument, self)._l10n_ec_generate_request_xml_file()
        #generamos y validamos el documento
        if self.move_id.is_waybill():
            etree_content = self._l10n_ec_get_xml_request_for_shipment()
            xml_content = clean_xml(etree_content)
            try: #validamos el XML contra el XSD
                if self.move_id.is_waybill():
                    validate_xml_vs_xsd(xml_content, XSD_SRI_110_GUIA_REMISION)
            except ValueError: 
                raise UserError(u'No se ha enviado al servidor: ¿quiza los datos estan mal llenados?:' + ValueError[1])        
            self.l10n_ec_request_xml_file_name = self.move_id.name + '_draft.xml'
            self.l10n_ec_request_xml_file = base64.encodestring(xml_content)
        return res
    
    @api.model
    def _l10n_ec_get_xml_request_for_shipment(self):
        '''
        '''
        # INICIO CREACION DE GUIA DE REMISION
        guiaRemision = etree.Element('guiaRemision', {'id': 'comprobante', 'version': '1.1.0'})
        # CREACION INFO TRIBUTARIA
        infoTributaria = etree.SubElement(guiaRemision, 'infoTributaria')
        infoTribElements = [
            ('ambiente', self.move_id.company_id._get_l10n_ec_environment_type()),
            ('tipoEmision', '1'),
            ('razonSocial', self.move_id.company_id.l10n_ec_legal_name)
        ]
        if self.move_id.company_id.partner_id.l10n_ec_commercial_name:
            infoTribElements.append(('nombreComercial', self.move_id.company_id.partner_id.l10n_ec_commercial_name))
        infoTribElements.extend([
            ('ruc', self.move_id.company_id.partner_id.vat),
            ('claveAcceso', self.l10n_ec_access_key),
            ('codDoc', '06'),
            ('estab', self.move_id.l10n_latam_document_number[0:3]),
            ('ptoEmi', self.move_id.l10n_latam_document_number[4:7]),
            ('secuencial', self.move_id.l10n_latam_document_number[8:]),
            ('dirMatriz', self.move_id.company_id.street)
        ])
        self.create_TreeElements(infoTributaria, infoTribElements)
        # CREACION INFO GUIA DE REMISION
        infoGuiaRemision = etree.SubElement(guiaRemision, 'infoGuiaRemision')
        infoGuiaRemisionElements = [
            ('dirEstablecimiento', self.move_id.l10n_ec_printer_id.printer_point_address),
            ('dirPartida', self.move_id.l10n_ec_printer_id.printer_point_address),
            ('razonSocialTransportista', self.move_id.l10n_ec_stock_carrier_id.name),
            ('tipoIdentificacionTransportista', self.move_id.l10n_ec_stock_carrier_id.get_ident_type()),
            ('rucTransportista', self.move_id.l10n_ec_stock_carrier_id.vat),
            ('obligadoContabilidad', 'SI' if self.move_id.company_id.l10n_ec_forced_accounting else 'NO'),
        ]
        if self.move_id.company_id.l10n_ec_special_contributor_number:
            infoGuiaRemisionElements.append(
                ('contribuyenteEspecial', self.move_id.company_id.l10n_ec_special_contributor_number))
        infoGuiaRemisionElements.extend([
            ('fechaIniTransporte', self.move_id.invoice_date.strftime('%d/%m/%Y')),
            ('fechaFinTransporte', self.move_id.invoice_date_due.strftime('%d/%m/%Y')),
            ('placa', self.move_id.l10n_ec_stock_carrier_id.license_plate),
        ])
        self.create_TreeElements(infoGuiaRemision, infoGuiaRemisionElements)
        # CREACION DE LOS DETALLES
        # DETALLES DE LA GUIA DE REMISION
        destinatarios = etree.SubElement(guiaRemision, 'destinatarios')
        destinatario = self.create_SubElement(destinatarios, 'destinatario')
        get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
        destinatario_data = [
            ('identificacionDestinatario', get_invoice_partner_data['invoice_vat']),
            ('razonSocialDestinatario', get_invoice_partner_data['invoice_name']),
            ('dirDestinatario', self.move_id.l10n_ec_waybill_loc_dest_address),
            ('motivoTraslado', self.move_id.l10n_ec_move_reason),
        ]
        invoice_ids = self.move_id.l10n_ec_stock_picking_id.sale_id and self.move_id.l10n_ec_stock_picking_id.sale_id.invoice_ids.filtered(
            lambda x: x.state in ['posted'] and x.amount_total > 0)
        if invoice_ids:
            if invoice_ids[0].l10n_latam_document_type_id.code == '18':
                destinatario_data.append(('codDocSustento', '01'))
            else:
                destinatario_data.append(('codDocSustento', invoice_ids[0].l10n_latam_document_type_id.code))
            destinatario_data.append(('numDocSustento', invoice_ids[0].name))
            destinatario_data.append(('numAutDocSustento', invoice_ids[0].l10n_ec_authorization))
            destinatario_data.append(('fechaEmisionDocSustento', invoice_ids[0].date_invoice))
        self.create_TreeElements(destinatario, destinatario_data)
        detalles = self.create_SubElement(destinatario, 'detalles')
        for each in self.move_id.l10n_ec_move_line_ids:
            detalle_data = []
            detalle = self.create_SubElement(detalles, 'detalle')
            product_code = each.product_id.default_code and each.product_id.default_code or each.product_id.barcode
            if product_code:
                detalle_data.append(('codigoInterno', product_code))
            detalle_data.append(('descripcion', each.product_id.name))
            detalle_data.append(('cantidad', each.qty_done))
            self.create_TreeElements(detalle, detalle_data)
            #detalle_adic = self.create_SubElement(detalle, 'detallesAdicionales')
            #if 'product_uom_id' in each._fields:
            #    self.create_SubElement(detalle_adic, 'detAdicional',
            #                           attrib={'nombre': 'UnidadDeMedida'},
            #                           text=each.product_uom_id.name or 'NO APLICA')
        infoAdicional = self.create_SubElement(guiaRemision, 'infoAdicional')
        if self.move_id.narration:
            self.create_SubElement(infoAdicional, 'campoAdicional',
                                   attrib={'nombre': 'Novedades'},
                                   text=self.move_id.narration.replace('\n', ' '))
        if self.move_id.l10n_ec_stock_picking_id.origin:
            self.create_SubElement(infoAdicional, 'campoAdicional',
                                   attrib={'nombre': 'Pedido'}, text=self.move_id.l10n_ec_stock_picking_id.origin)
        return guiaRemision

    def _get_additional_info(self):
        self.ensure_one()
        additional_info = super()._get_additional_info()
        if self.move_id.is_waybill():
            additional_info = []
            get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
            if self.move_id.company_id.l10n_ec_regime == 'micro':
                additional_info.append('Regimen: %s' % _MICROCOMPANY_REGIME_LABEL)
            if self.move_id.company_id.l10n_ec_withhold_agent == 'designated_withhold_agent':
                additional_info.append('Agente de Retencion: %s' % ''.join([u'Resolución Nro. ', self.move_id.company_id.l10n_ec_wihhold_agent_number]))
            if get_invoice_partner_data['invoice_email']:
                additional_info.append('Email: %s' % get_invoice_partner_data['invoice_email'])
            if get_invoice_partner_data['invoice_address']:
                additional_info.append('Direccion: %s' % get_invoice_partner_data['invoice_address'])
            if get_invoice_partner_data['invoice_phone']:
                additional_info.append('Telefono: %s' % get_invoice_partner_data['invoice_phone'])
        return additional_info

    def _prepare_jobs(self):
        #make withholds is_withhold() look like invoice is_invoice() for account_edi to process it
        to_process = super(AccountEdiDocument, self.with_context(l10n_ec_send_email_others_docs=True))._prepare_jobs()
        return to_process

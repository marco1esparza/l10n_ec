# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.tools import float_repr

import re
from datetime import date, datetime
import logging
import base64

import xml.etree.ElementTree as ElementTree
from xml.dom import minidom

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'
    
    #Redefinitions based on account_edi
    def _is_required_for_invoice(self, invoice):
        """ Indicate if this EDI must be generated for the invoice passed as parameter.

        :param invoice: An account.move having the invoice type.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        self.ensure_one()
        if self.code != 'l10n_ec_sale_18':
            if invoice.l10n_latam_country_code == 'EC':
                if invoice.l10n_ec_printer_id.l10n_ec_allow_electronic_document:
                    if invoice.l10n_latam_document_type_id.code in ['18']:
                        return True
        return super()._is_required_for_invoice(invoice)

    def _needs_web_services(self):
        """ Indicate if the EDI must be generated asynchronously through to some web services.

        :return: True if such a web service is available, False otherwise.
        """
        self.ensure_one()
        return True if self.code in ['l10n_ec_sale_18'] else super()._needs_web_services() 

    
    def _is_compatible_with_journal(self, journal):
        """ Indicate if the EDI format should appear on the journal passed as parameter to be selected by the user.
        If True, this EDI format will be selected by default on the journal.

        :param journal: The journal.
        :returns:       True if this format can be enabled by default on the journal, False otherwise.
        """
        # TODO Implementar, no se requiere en la primera versión
        return super()._is_compatible_with_journal(journal)

    def _is_embedding_to_invoice_pdf_needed(self):
        self.ensure_one()
        return False if self.l10n_latam_country_code == 'EC' else super()._is_embedding_to_invoice_pdf_needed()

    def _post_invoice_edi(self, invoices, test_mode=False):
        """ Create the file content representing the invoice (and calls web services if necessary).

        :param invoices:    A list of invoices to post.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * attachment:       The attachment representing the invoice in this edi_format if the edi was successfully posted.
        * error:            An error if the edi was not successfully posted.
        """
        #replaces good old attempt_electronic_document from v10
        #llamamos a super para anexar los errores en "edi_result"
        edi_result = super()._post_invoice_edi(invoices, test_mode=test_mode)
        if self.code not in ['l10n_ec_sale_18']:
            return edi_result
        if test_mode:
                return edi_result
        for invoice in invoices:
            #First some validations
            if invoice.edi_state in ('sent'):
                raise ValidationError("No se puede enviar al SRI documentos previamente enviados: Documento %s" % str(self.name))
            if invoice.edi_state in ('canceled'):
                raise ValidationError("No se puede enviar al SRI documentos previamente anulados: Documento %s \n"
                                      "En su lugar debe crear un nuevo documento electrónico" % str(self.name)) 
            if invoice.edi_state not in ('to_send'):
                raise ValidationError("Error, solo se puede enviar al SRI documentos en estado A ENVIAR: Documento" %s % str(self.name))
            if len(invoice.edi_document_ids) != 1: #Primera versión, como en v10, relación 1 a 1
                raise ValidationError("Error, es extraño pero hay más de un documento electrónico a enviar" %s % str(invoice.name))
            document = invoice.edi_document_ids.filtered(lambda r: r.state == "to_send")
            #Firts try to download reply, if not available try sending again
            response_state, response, msgs = document._l10n_ec_download_electronic_document_reply()
            if response_state == 'non-existent':
                document._l10n_ec_upload_electronic_document()
                time.sleep(1) # Esperamos 1 segundo para que el SRI procese el documento
                response_state, response, msgs = document._l10n_ec_download_electronic_document_reply()
            if msgs: #TODO V13: Capturar y presentar mejor los errores
                edi_result[invoice] = {
                    'error': self._l10n_ec_edi_format_error_message(_("Failure reported by Tax Authority:"), msgs),
                }
                continue
            if response_state in ['sent']:
                #Create attachment, only if successful
                datas = self._l10n_ec_build_external_xml(response).encode('utf-8')
                electronic_document_attachment = self.env['ir.attachment'].create({
                    'name': invoice.name,
                    'res_id': invoice.id,
                    'res_model': invoice._name,
                    'type': 'binary',
                    'datas': datas,
                    'mimetype': 'application/xml',
                    'description': _('Ecuadorian electronic document for the %s document.') % invoice.name,
                })
                edi_result[invoice] = {'attachment': electronic_document_attachment}
                #Chatter, no_new_invoice to prevent creation of another new invoice "from the attachment"
                invoice.with_context(no_new_invoice=True).message_post(
                    body=_("The ecuadorian electronic document was successfully created, signed and validated by the tax authority"),
                    attachment_ids=electronic_document_attachment.ids,
                )
        return edi_result

    def _cancel_invoice_edi(self, invoices, test_mode=False):
        """Calls the web services to cancel the invoice of this document.

        :param invoices:    A list of invoices to cancel.
        :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
        :returns:           A dictionary with the invoice as key and as value, another dictionary:
        * success:          True if the invoice was successfully cancelled.
        * error:            An error if the edi was not successfully cancelled.
        """
        # TO OVERRIDE
        edi_result = super()._cancel_invoice_edi(invoices, test_mode=test_mode)
        if self.code  not in ['l10n_ec_sale_18']:
            return edi_result
        if test_mode:
            return edi_result
        for invoice in invoices:
            #here invoice refers to any document, an invoice, withhold, waybill
            document = invoice.edi_document_ids.filtered(lambda r: r.state == "to_cancel")
            #Firts try to download reply, if not available try sending again
            response_state, response, msgs = document._l10n_ec_download_electronic_document_reply()
            if msgs: #TODO V13: Capturar y presentar mejor los errores
                edi_result[invoice] = {
                    'error': self._l10n_ec_edi_format_error_message(_("Failure reported by Tax Authority:"), msgs),
                }
                continue
            if response_state not in ['non-existent']:
                msg = ''
                edi_result[invoice] = {
                    'error': self._l10n_ec_edi_format_error_message(_("First you should void the document in SRI web site"), msgs),
                }                
            if response_state in ['non-existent']:
                res = {'success': True} #indicates cancell operation success
                edi_result[invoice] = res
                #Chatter, no_new_invoice to prevent creation of another new invoice "from the attachment"
                invoice.with_context(no_new_invoice=True).message_post(
                    body=_("The ecuadorian electronic document was successfully voided")
                )
        return edi_result
    
    def _l10n_ec_edi_format_error_message(self, error_title, errors):
        #TODO: Agregar fecha y hora del error, pues en v13 ya no tenemos el campo de fecha de ultimo reintento
        bullet_list_msg = ''.join('<li>%s</li>' % msg for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)
    
    def _l10n_ec_build_external_xml(self, result):
        '''
        Costruye un xml similar al del SRI para ser almacenado y enviado por correo
        Tiene las siguientes particularidaes:
        - Almacena el contenido del comprobante en un CDATA para evitar distorsiones
        - No hay formato del SRI establecido para este xml, nos basamos en el porveedor puntonet para construirlo
        @result es la respuesta del webservice del SRI
        '''
        root = ElementTree.Element("RespuestaAutorizacionComprobante")
        ElementTree.SubElement(root, "claveAccesoConsultada").text = result.claveAccesoConsultada
        ElementTree.SubElement(root, "numeroComprobantes").text = result.numeroComprobantes
        autorizaciones = ElementTree.SubElement(root, "autorizaciones")
        autorizacion = ElementTree.SubElement(autorizaciones, "autorizacion")
        ElementTree.SubElement(autorizacion, "estado").text = result.autorizaciones.autorizacion[0].estado
        # Cuando el documento es 'NO AUTORIZADO' se envia el numero 0000000000 como autorizacion
        if 'numeroAutorizacion' in result.autorizaciones.autorizacion[0]: 
            ElementTree.SubElement(autorizacion, "numeroAutorizacion").text = result.autorizaciones.autorizacion[0].numeroAutorizacion
        else: 
            ElementTree.SubElement(autorizacion, "numeroAutorizacion").text = '0000000000'
        date_format = result.autorizaciones.autorizacion[0].fechaAutorizacion.strftime('%Y-%m-%dT%H:%M:%S.000%Z')
        ElementTree.SubElement(autorizacion, "fechaAutorizacion").text = date_format
        ElementTree.SubElement(autorizacion, "ambiente").text = result.autorizaciones.autorizacion[0].ambiente
        # pulimos la respuesta para hacerla estandar
        comprobante = result.autorizaciones.autorizacion[0].comprobante
        comprobante = "<![CDATA[" + comprobante + "]]>" 
        ElementTree.SubElement(autorizacion, "comprobante").text = comprobante 
        # Mensajes retornados
        mensajes = ElementTree.SubElement(autorizacion, "mensajes")
        mesage_tit = ''
        mesage_desc = ''
        data_error = result.autorizaciones.autorizacion[0].mensajes
        if data_error:
            data_error = data_error[0][0]
            mesage_tit = data_error.tipo + ", " + data_error.identificador + ", " + data_error.mensaje
            mesage_desc = data_error.informacionAdicional
        ElementTree.SubElement(mensajes, "mensaje").text = mesage_tit
        ElementTree.SubElement(mensajes, "detalle").text = mesage_desc
        parse_pretty = minidom.parseString('<?xml version="1.0" encoding="utf-8"?>' + ElementTree.tostring(root, encoding='utf-8').decode())
        response = parse_pretty.toprettyxml()
        # Cambiar codigo mayor que, menor que, comillas simples por el caracter adecuado
        response = response.replace("&lt;", "<")
        response = response.replace("&gt;", ">")
        response = response.replace("&quot;", "'")
        return response
        
        
# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.tests.common import Form
from odoo.exceptions import UserError, ValidationError, except_orm
from odoo.tools import float_repr

import re
from datetime import date, datetime
import logging
import base64

import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from time import sleep

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'
    
    #Redefinitions based on account_edi
    def _is_required_for_invoice(self, invoice):
        """ Indicate if this EDI must be generated for the move passed as parameter.
        :param invoice: An account.move having the invoice type.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        self.ensure_one()
        withhold = invoice #for ease reading
        if withhold.country_code == 'EC' and self.code == 'l10n_ec_tax_authority':
            is_required_for_invoice = False
            if not withhold.l10n_ec_printer_id.allow_electronic_document:
                #first lets verify that the printer point is an electronic one
                return is_required_for_invoice
            #Retenciones compra
            if withhold.is_withholding() and withhold.l10n_ec_withhold_type == 'in_withhold':
                is_required_for_invoice = True
            return is_required_for_invoice
        return super()._is_required_for_invoice(withhold)
    
#     def _post_invoice_edi(self, invoices, test_mode=False):
#         """ Create the file content representing the invoice (and calls web services if necessary).
#         :param invoices:    A list of invoices to post.
#         :param test_mode:   A flag indicating the EDI should only simulate the EDI without sending data.
#         :returns:           A dictionary with the invoice as key and as value, another dictionary:
#         * attachment:       The attachment representing the invoice in this edi_format if the edi was successfully posted.
#         * error:            An error if the edi was not successfully posted.
#         """
#         #replaces good old attempt_electronic_document from v10
#         #llamamos a super para anexar los errores en "edi_result"
#         edi_result = super()._post_invoice_edi(invoices, test_mode=test_mode)
#         if self.code != 'l10n_ec_tax_authority':
#             return edi_result
#         for invoice in invoices:
#             #First some validations
#             msgs = []
#             if not test_mode:
#                 # Si no tenemos Modo test por context, entonces evaluamos que la company_id este en modo Demo
#                 enviroment_type = invoice.company_id.l10n_ec_environment_type
#                 if enviroment_type and enviroment_type == '0':
#                     test_mode = True
#             # Si estamos en Modo test y tenemos documentos electronicos y tenemos request
#             # asignamos el attachment con dicho documento.
#             edi_ec = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'l10n_ec_tax_authority')
#             if test_mode and not edi_ec.attachment_id:
#                 attachment = self.env['ir.attachment'].create({
#                     'name': invoice.name+'.xml',
#                     'res_id': invoice.id,
#                     'res_model': invoice._name,
#                     'type': 'binary',
#                     'datas': edi_ec.l10n_ec_request_xml_file,
#                     'mimetype': 'application/xml',
#                     'description': _('Demo Ecuadorian electronic document for the %s document.') % invoice.name,
#                 })
#                 edi_result[invoice] = {'attachment': attachment}
#                 return edi_result
#             if invoice.edi_state in ('sent'):
#                 raise ValidationError("No se puede enviar al SRI documentos previamente enviados: Documento %s" % str(self.name))
#             if invoice.edi_state in ('canceled'):
#                 raise ValidationError("No se puede enviar al SRI documentos previamente anulados: Documento %s \n"
#                                       "En su lugar debe crear un nuevo documento electrónico" % str(self.name)) 
#             if invoice.edi_state not in ('to_send'):
#                 raise ValidationError("Error, solo se puede enviar al SRI documentos en estado A ENVIAR: Documento" %s % str(self.name))
#             if len(edi_ec) != 1: #Primera versión, como en v10, relación 1 a 1
#                 raise ValidationError("Error, es extraño pero hay más de un documento electrónico a enviar" %s % str(invoice.name))
#             document = edi_ec.filtered(lambda r: r.state == "to_send")
#             #Firts try to download reply, if not available try sending again
#             response_state, response = document._l10n_ec_download_electronic_document_reply()
#             if response_state == 'non-existent':
#                 try:
#                     document._l10n_ec_upload_electronic_document()
#                 except except_orm as err: #Most errors captured inside Odoo
#                     msgs.append(err.name)
#                 except: #all other errors drop to standard output (screen and log)
#                     raise
#                 else:
#                     sleep(2) # Esperamos 2 segundos para que el SRI procese el documento
#                     response_state, response = document._l10n_ec_download_electronic_document_reply()
#                 finally:
#                     pass #nothing to do until now
#             elif response_state == 'rejected':
#                 msgs.append(str(response.autorizaciones.autorizacion[0].mensajes))
#                 msgs.append('Corrija el problema reportado por el SRI, anule el documento en Odoo, y reintente nuevamente')
#             if msgs:
#                 edi_result[invoice] = {
#                     'error': self._l10n_ec_edi_format_error_message(_("Errors reported by Tax Authority:"), msgs),
#                 }
#                 continue
#             if response_state in ['sent']:
#                 #Create attachment, only if successful
#                 datas = self._l10n_ec_build_external_xml(response).encode('utf-8')
#                 datas = base64.encodebytes(datas)
#                 electronic_document_attachment = self.env['ir.attachment'].create({
#                     'name': invoice.name+'.xml',
#                     'res_id': invoice.id,
#                     'res_model': invoice._name,
#                     'type': 'binary',
#                     'datas': datas,
#                     'mimetype': 'application/xml',
#                     'description': _('Ecuadorian electronic document for the %s document.') % invoice.name,
#                 })
#                 edi_result[invoice] = {'attachment': electronic_document_attachment}
#         return edi_result

        

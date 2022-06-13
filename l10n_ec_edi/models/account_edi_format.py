# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import traceback
import unicodedata
from datetime import datetime
from functools import partial
from io import BytesIO
from random import randint
from xml.etree.ElementTree import Element, SubElement, tostring

from odoo import _, api, fields, models
from odoo.addons.l10n_ec_edi.models.xml_utils import L10nEcXmlUtils
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import file_open, float_repr, float_round
from odoo.tools.xml_utils import _check_with_xsd
from odoo.exceptions import UserError
from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Error as ZeepError

_logger = logging.getLogger(__name__)

TEST_URL = {
    "reception": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
    "authorization": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
}

PRODUCTION_URL = {
    "reception": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl",
    "authorization": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl",
}

DEFAULT_TIMEOUT_WS = 20

class AccountEdiFormat(models.Model):

    _inherit = "account.edi.format"

    def _is_compatible_with_journal(self, journal):
        # For Ecuador include the journals for sales invoices, purchase liquidations and purchase withholds 
        if journal.country_code != "EC":
            return super(AccountEdiFormat, self)._is_compatible_with_journal(journal)
        if journal.type == 'sale' and journal.l10n_latam_use_documents: #Only sales with use documents should be electronic
            return self.code == "ecuadorian_edi"
        elif journal.type == 'general' and journal.l10n_ec_withhold_type == 'in_withhold': #Purchase withhold
            return self.code == "ecuadorian_edi"
        elif journal.type == 'purchase': #TODO Odoo: implement or explain the purchase liquidation
            return self.code == "ecuadorian_edi"
        else:
            return False

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        if invoice.country_code != "EC":
            return super(AccountEdiFormat, self)._is_required_for_invoice(invoice)

        internal_type = invoice.l10n_latam_document_type_id.internal_type
        return self.code == "ecuadorian_edi" \
            and (invoice.move_type in ('out_invoice', 'out_refund') or internal_type == 'purchase_liquidation'
                 or invoice.journal_id.l10n_ec_withhold_type == 'in_withhold')

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == "ecuadorian_edi" or super(AccountEdiFormat, self)._needs_web_services()

    def _check_move_configuration(self, move):
        # OVERRIDE
        if self.code != "ecuadorian_edi":
            return super(AccountEdiFormat, self)._check_move_configuration(move)

        errors = []
        if self._is_required_for_invoice(move):
            journal = move.journal_id
            address = journal.l10n_ec_emission_address_id
            if not move.company_id.vat:
                errors.append(
                    _("You must set vat identification for company %s", move.company_id.display_name)
                )
            if not address:
                errors.append(
                    _("You must set emission address on journal %s", journal.display_name)
                )
            if address and not address.street:
                errors.append(
                    _("You must set address on contact %s, fields street must be filled",
                      address.display_name)
                )
            if address and not address.commercial_partner_id.street:
                errors.append(
                    _("You must set headquarter address on contact %s, fields street must be filled",
                        address.commercial_partner_id.display_name
                      )
                )
            if not move.l10n_ec_sri_payment_id and move.journal_id.l10n_ec_withhold_type != 'in_withhold':
                errors.append(
                    _("You have to configure Payment Method SRI on document: %s.", move.display_name)
                )

        if not move.commercial_partner_id.country_id:
            errors.append(
                _("You have to configure Country to Partner: %s.", move.commercial_partner_id.name)
            )
        if not move.commercial_partner_id.street:
            errors.append(
                _("You have to configure Street to Partner: %s.", move.commercial_partner_id.name)
            )

        if move.move_type == "out_refund" and not move.reversed_entry_id:
            errors.append(
                _("Credit Note %s must have original invoice related, try to use wizard 'Add Credit Note' on original invoice",
                    move.display_name
                  )
            )
        if move.l10n_latam_document_type_id.internal_type == "debit_note" and not move.debit_origin_id:
            errors.append(
                _("Debit Note %s must have original invoice related, try to use wizard 'Add Debit Note' on original invoice",
                    move.display_name
                  )
            )
        return errors

    def _post_invoice_edi(self, invoices):
        if self.code != "ecuadorian_edi":
            return super(AccountEdiFormat, self)._post_invoice_edi(invoices)

        res = {}
        for invoice in invoices:
            if not invoice.l10n_ec_authorization_number:  # Assign auth. number if necessary
                invoice.l10n_ec_authorization_number = self._l10n_ec_get_access_key(invoice)
            xml_content, errors = self._l10n_ec_generate_xml(invoice)

            # Error management
            if errors:
                blocking_level = "error"
                attachment = None
            else:
                errors, blocking_level, attachment = self._l10n_ec_send_xml_to_authorize(invoice, xml_content)

            res.update(
                {
                    invoice: {
                        "success": not errors,
                        "error": "<br/>".join(errors),
                        "attachment": attachment,
                        "blocking_level": blocking_level,
                    }
                }
            )
        return res

    def _cancel_invoice_edi(self, invoices):
        if invoices.filtered(lambda x: x.country_code != "EC"):
            return super(AccountEdiFormat, self)._cancel_invoice_edi(invoices)

        res = {}
        for invoice in invoices:
            authorization, authorization_date, errors = self._l10n_ec_get_authorization_status(invoice)
            if authorization:
                errors.append(
                    _("You cannot cancel a document that is still authorized (%s, %s), check the SRI portal",
                      authorization, authorization_date)
                )
            res[invoice] = {
                "success": not errors,
                "error": "\n".join(errors),
            }
        return res

    # ===== HELPERS =====

    def _l10n_ec_get_xml_filename(self, invoice, authorized=False):
        current_document = invoice
        invoices_name = "%s" % current_document.display_name
        return invoices_name + (authorized and _("_authorized") or "") + ".xml"

    def _l10n_ec_generate_xml(self, invoice):
        # Gather XML values
        invoice_info = {
            'invoice': invoice,
            'secuencial': str(self._l10n_ec_get_only_sequence(invoice)).rjust(9, "0"),
            'format_num_2': self._l10n_ec_format_number,
            'format_num_6': partial(self._l10n_ec_format_number, decimals=6),
            'clean_str': self._l10n_ec_clean_str,
            'strftime': partial(datetime.strftime, format="%d/%m/%Y"),
        }
        invoice_info.update(invoice.l10n_ec_get_invoice_edi_data())

        # Render and validate XML
        xml_content = self.env.ref("l10n_ec_edi.common_main_template")._render(invoice_info)
        xml_content = L10nEcXmlUtils._cleanup_xml_content(xml_content)
        xsd_errors = self._l10n_ec_validate_with_xsd(xml_content, invoice.l10n_latam_document_type_id.internal_type)

        xml_string = tostring(xml_content)
        xml_signed = invoice.company_id.l10n_ec_certificate_id.action_sign(xml_string)
        xml_signed = b'<?xml version="1.0" encoding="utf-8" standalone="no"?>' + xml_signed.encode()
        return xml_signed, xsd_errors

    def _l10n_ec_send_xml_to_authorize(self, invoice, xml_content):
        # === STEP 1 ===
        errors, info = [], []
        if not invoice.l10n_ec_authorization_date:
            # Submit the generated XML
            response, zeep_errors = self._l10n_ec_get_client_service_response(invoice, "reception", xml=xml_content)
            if zeep_errors:
                return zeep_errors, "error", False
            try:
                response_state = response.estado
                response_checks = response.comprobantes and response.comprobantes.comprobante or []
            except AttributeError as e:
                return [str(e)], "error", False

            # Parse govt's response for errors or response state
            already_authorized = False
            if response_state == "DEVUELTA":
                for check in response_checks:
                    for msg in check.mensajes.mensaje:
                        errors.append(" - ".join(
                            map(lambda x: x or '',
                                [msg.identificador, msg.informacionAdicional, msg.mensaje, msg.tipo]))
                        )
                        if msg.identificador == "43":  # Access key already registered
                            already_authorized = True
            elif response_state != "RECIBIDA":
                errors.append(_("SRI response state: %s", response_state))

            # If any errors have been found (other than those indicating already-authorized document)
            if errors and not already_authorized:
                return errors, "error", False

        # === STEP 2 ===
        # get authorization status & store response
        attachment = False
        authorization_num, authorization_date, auth_errors = self._l10n_ec_get_authorization_status(invoice)
        errors.extend(auth_errors)
        if authorization_num and authorization_date:
            if invoice.l10n_ec_authorization_number != authorization_num:
                info.append(f"Authorization number {authorization_num} does not match "
                            "document's {invoice.l10n_ec_authorization_number}")
            invoice.l10n_ec_authorization_number = authorization_num
            invoice.l10n_ec_authorization_date = authorization_date.strftime(DTF)
            attachment = self.env["ir.attachment"].create({
                "name": self._l10n_ec_get_xml_filename(invoice, True),
                "res_id": invoice.id,
                "res_model": invoice._name,
                "type": "binary",
                "raw": self._l10n_ec_create_authorization_file(invoice, xml_content, authorization_num, authorization_date),
                "mimetype": "application/xml",
                "description": f"Ecuadorian electronic document generated for document {invoice.display_name}."
            })
            invoice.with_context(no_new_invoice=True).message_post(
                body=_(
                    f"Electronic document authorized.<br/>"
                    f"<strong>Authorization num:</strong><br/>{invoice.l10n_ec_authorization_number}<br/>"
                    f"<strong>Authorization date:</strong><br/>{invoice.l10n_ec_authorization_date}",
                ),
                attachment_ids=attachment.ids,
            )
        else:
            info.append(f"Document with access key {invoice.l10n_ec_authorization_number} "
                        "received by govt and pending authorization.")

        return errors or info, "error" if errors else "info", attachment

    def _l10n_ec_get_authorization_status(self, invoice):
        authorization_num, authorization_date = False, False

        response, zeep_errors = self._l10n_ec_get_client_service_response(
            invoice, "authorization",
            claveAccesoComprobante=invoice.l10n_ec_authorization_number
        )
        if zeep_errors:
            return authorization_num, authorization_date, zeep_errors
        try:
            response_auth_list = response.autorizaciones and response.autorizaciones.autorizacion or []
        except AttributeError as err:
            return authorization_num, authorization_date, [str(err)]

        errors = []
        if not response_auth_list:
            errors.append(_("Document not authorized by SRI, please try again later"))
        elif not isinstance(response_auth_list, list):
            response_auth_list = [response_auth_list]

        for doc in response_auth_list:
            if doc.estado == "AUTORIZADO":
                authorization_num = doc.numeroAutorizacion
                authorization_date = doc.fechaAutorizacion
            else:
                messages = doc.mensajes
                messages_list = messages.mensaje
                if messages:
                    if not isinstance(messages_list, list):
                        messages_list = messages
                    for msg in messages_list:
                        errors.append(" - ".join(
                            map(lambda x: x or '',
                                [msg.identificador, msg.informacionAdicional, msg.mensaje, msg.tipo])))
        return authorization_num, authorization_date, errors

    def _l10n_ec_get_client_service_response(self, invoice, mode, **kwargs):
        if invoice.company_id.l10n_ec_production_env:
            wsdl_url = PRODUCTION_URL.get(mode)
        else:
            wsdl_url = TEST_URL.get(mode)

        errors = []
        try:
            transport = Transport(timeout=DEFAULT_TIMEOUT_WS)
            client = Client(wsdl=wsdl_url, transport=transport)
            if mode == "reception":
                response = client.service.validarComprobante(**kwargs)
            elif mode == "authorization":
                response = client.service.autorizacionComprobante(**kwargs)
            if not response:
                errors.append(_("No response received."))
        except ZeepError as e:
            errors.append(_(
                f"The SRI service failed with the following error: {e}, "
                f"traceback: {''.join(traceback.format_tb(e.__traceback__))}"
            ))
        return response, errors

    # ===== HELPERS (static) =====

    @api.model
    def _l10n_ec_get_access_key(self, invoice):
        company = invoice.company_id
        document_code_sri = invoice.l10n_ec_get_document_code_sri()
        environment = company.l10n_ec_production_env and "2" or "1"
        serie = invoice.journal_id.l10n_ec_entity + invoice.journal_id.l10n_ec_emission
        sequencial = str(self._l10n_ec_get_only_sequence(invoice)).rjust(9, "0")
        num_filler = "31215214"  # can be any 8 digits, thanks @3cloud !
        emission = "1"  # emision normal, ya no se admite contingencia (2)

        if not (document_code_sri and company.partner_id.vat and environment
                and serie and sequencial and num_filler and emission):
            return ""

        now_date = invoice.date.strftime("%d%m%Y")
        key_value = now_date + document_code_sri + company.partner_id.vat + environment + serie + sequencial + num_filler + emission
        return key_value + str(self._l10n_ec_get_check_digit(key_value))

    @api.model
    def _l10n_ec_get_check_digit(self, key):
        sum_total = sum([int(key[-i - 1]) * (i % 6 + 2) for i in range(len(key))])
        sum_check = 11 - (sum_total % 11)
        if sum_check >= 10:
            sum_check = 11 - sum_check
        return sum_check

    @api.model
    def _l10n_ec_get_only_sequence(self, invoice):
        number = invoice.l10n_latam_document_number
        try:
            number_splited = number.split("-")
            res = int(number_splited[2])
        except Exception as e:
            _logger.debug(f"Error getting sequence: {e}")
            res = None
        return res

    @api.model
    def _l10n_ec_create_authorization_file(self, invoice, xml_file_content, authorization_number, authorization_date):
        xml_response = self.env.ref("l10n_ec_edi.authorization_template")._render({
            'xml_file_content': xml_file_content.decode(),
            'mode': "PRODUCCION" if invoice.company_id.l10n_ec_production_env else "PRUEBAS",
            'authorization_number': authorization_number,
            'authorization_date': authorization_date.strftime(DTF),
        })
        xml_response = L10nEcXmlUtils._cleanup_xml_content(xml_response)
        return tostring(xml_response).decode()

    def _l10n_ec_validate_with_xsd(self, xml_doc, doc_type):
        try:
            xsd_attachment = self.env.ref(f"l10n_ec_edi.{doc_type}_xsd")
        except ValueError:
            xsd_doc = file_open((f'./l10n_ec_edi/data/xsd/{doc_type}.xsd'))
            xsd_attachment = self.env['ir.attachment'].create({
                "name": f"{doc_type}_xsd",
                "type": "binary",
                "raw": xsd_doc.read(),
                "mimetype": "application/xml",
                "description": f"XSD validation file for {doc_type.replace('_', '')}s",
            })
            self.env['ir.model.data'].create({
                'name': f"{doc_type}_xsd",
                'module': 'l10n_ec_edi',
                'res_id': xsd_attachment.id,
                'model': 'ir.attachment',
                'noupdate': True,
            })
        with BytesIO(xsd_attachment.raw) as xsd:
            try:
                _check_with_xsd(xml_doc, xsd, self.env)
                return []
            except UserError as e:
                return [str(e)]

    # ===== PRIVATE (static) =====

    @api.model
    def _l10n_ec_format_number(self, value, decimals=2):
        return float_repr(float_round(value, decimals), decimals)

    @api.model
    def _l10n_ec_clean_str(self, s, max_len=300):
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')[:max_len]

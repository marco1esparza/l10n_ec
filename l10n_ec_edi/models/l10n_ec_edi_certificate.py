# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
from base64 import b64decode, b64encode
from datetime import datetime
from random import randrange

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from odoo import fields, models, tools
from odoo.addons.l10n_ec_edi.models.xml_utils import L10nEcXmlUtils
from odoo.exceptions import UserError
from odoo.tools.translate import _
from OpenSSL import crypto

_logger = logging.getLogger(__name__)


STATES = {"unverified": [("readonly", False), ]}


class L10nEcCertificate(models.Model):
    _name = "l10n_ec.certificate"
    _description = "Sign Cert File"

    name = fields.Char(string="Name", required=True)
    file_name = fields.Char("File Name", readonly=True)
    file_content = fields.Binary("Sign Cert File", readonly=True, states=STATES)
    password = fields.Char("Password", readonly=True, states=STATES)
    private_key = fields.Text(string="Private Key", readonly=True)
    active = fields.Boolean("Active?", default=True)
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    state = fields.Selection(
        [("unverified", "Unverified"), ("valid", "Valid"), ("expired", "Expired"), ],
        string="State",
        default="unverified",
        readonly=True,
    )
    emission_date = fields.Date(string="Emission Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)
    subject_serial_number = fields.Char(string="Serial Number(Subject)", readonly=True)
    subject_common_name = fields.Char(string="Subject Common Name", readonly=True)
    issuer_common_name = fields.Char(string="Issuer Common Name", readonly=True)
    cert_serial_number = fields.Char(string="Serial Number", readonly=True)
    cert_version = fields.Char(string="Version", readonly=True)

    def action_validate_and_load(self):
        file_content = base64.b64decode(self.file_content)
        try:
            p12 = crypto.load_pkcs12(file_content, self.password)
        except Exception as ex:
            _logger.warning(tools.ustr(ex))
            raise UserError(
                _(
                    "Error opening the signature, possibly the signature key has been entered incorrectly or the file is not supported."
                )
            )

        cert = p12.get_certificate()
        issuer = cert.get_issuer()
        subject = cert.get_subject()
        private_key = crypto.dump_privatekey(
            crypto.FILETYPE_PEM, p12.get_privatekey()
        ).decode()
        vals = {
            "emission_date": datetime.strptime(
                cert.get_notBefore().decode("utf-8"), "%Y%m%d%H%M%SZ"
            ),
            "expiration_date": datetime.strptime(
                cert.get_notAfter().decode("utf-8"), "%Y%m%d%H%M%SZ"
            ),
            "subject_common_name": subject.CN,
            "subject_serial_number": subject.serialNumber,
            "issuer_common_name": issuer.CN,
            "cert_serial_number": cert.get_serial_number(),
            "cert_version": cert.get_version(),
            "state": "valid",
            "private_key": private_key,
        }
        self.write(vals)
        return True

    @tools.ormcache("file_content", "private_key", "password")
    def load_p12(self, file_content, private_key, password):
        try:
            private_key = crypto.load_privatekey(
                crypto.FILETYPE_PEM, private_key, password,
            )
            return crypto.load_pkcs12(file_content, password)
        except Exception as ex:
            _logger.warning("Error open key file: %s", ex)
            raise UserError(
                _(
                    "Error opening the signature, possibly the signature key has been entered incorrectly or the file is not supported"
                )
            )

    def action_sign(self, xml_string_data):
        if not self.state == "valid":
            raise UserError(
                _("Current Cert %s is not on valid state, please check")
                % (self.display_name)
            )

        self.ensure_one()

        def new_range():
            return randrange(100000, 999999)  # TODO use uuid ?

        # Signature rendering: prepare reference identifiers
        signature_id = "Signature{}".format(new_range())
        qweb_values = {
            'signature_id': signature_id,
            'signature_property_id': "{}-SignedPropertiesID{}".format(signature_id, new_range()),
            'certificate_id': "Certificate{}".format(new_range()),
            'reference_uri': "Reference-ID-{}".format(new_range()),
            'signed_properties_id': "SignedPropertiesID{}".format(new_range())
        }

        # Load and select certificate (only used to find issuer data)
        file_content = base64.b64decode(self.file_content)
        p12 = self.load_p12(
            file_content, self.private_key.encode("ascii"), self.password.encode()
        )

        is_digital_signature = False
        x509 = None
        x509_to_review = p12.get_certificate().to_cryptography()
        for extension in x509_to_review.extensions:
            if extension.oid._name == "keyUsage" and extension.value.digital_signature:
                is_digital_signature = True
                break
        if not is_digital_signature:
            ca_certificates_list = p12.get_ca_certificates()
            if ca_certificates_list is not None:
                for x509_inst in ca_certificates_list:
                    x509_cryp = x509_inst.to_cryptography()
                    for extension in x509_cryp.extensions:
                        if (
                            extension.oid._name == "keyUsage"
                            and extension.value.digital_signature
                        ):
                            x509 = x509_inst
                            break
        if x509 is not None:
            p12.set_certificate(x509)
            p12.set_privatekey(self.private_key)
        issuer = p12.get_certificate().get_issuer()
        # TODO Investigate diff between the code above and pkcs12.load_key_and_certificates()

        # Load key and certificates (p12.get_privatekey() has no attribute 'sign'
        cert_private, cert_public, dummy = pkcs12.load_key_and_certificates(
            b64decode(self.with_context(bin_size=False).file_content),  # Without bin_size=False, size is returned instead of content
            self.password.encode(),
            backend=default_backend(),
        )
        public_key = cert_public.public_key()  # p12.get_certificate().public_key(): no attribute public_key

        # Signature rendering: prepare certificate values
        qweb_values.update({
            "sig_certif_digest": b64encode(cert_public.fingerprint(hashes.SHA1())).decode(),
            'x509_certificate': L10nEcXmlUtils._base64_print(b64encode(cert_public.public_bytes(encoding=serialization.Encoding.DER))),
            'rsa_modulus': L10nEcXmlUtils._base64_print(b64encode(L10nEcXmlUtils._int_to_bytes(public_key.public_numbers().n))),
            'rsa_exponent': L10nEcXmlUtils._base64_print(b64encode(L10nEcXmlUtils._int_to_bytes(public_key.public_numbers().e))),
            'x509_issuer_description': "CN={}, OU={}, O={}, C={}".format(issuer.CN, issuer.OU, issuer.O, issuer.C),
            'x509_serial_number': self.cert_serial_number,
        })

        # Parse document, append rendered signature
        doc = L10nEcXmlUtils._cleanup_xml_content(xml_string_data.decode())
        signature_str = self.env.ref("l10n_ec_edi.ec_edi_signature")._render(qweb_values)
        signature = L10nEcXmlUtils._cleanup_xml_signature(signature_str)
        doc.append(signature)

        # Compute digest values for references
        L10nEcXmlUtils._reference_digests(signature.find("ds:SignedInfo", namespaces=L10nEcXmlUtils.NS_MAP), base_uri="#comprobante")

        # Sign (writes into SignatureValue)
        L10nEcXmlUtils._fill_signature(signature, cert_private)

        return etree.tostring(doc, encoding="UTF-8").decode()

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.exceptions import UserError
from OpenSSL import crypto
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64
import logging

_logger = logging.getLogger(__name__)


EC_STATE_SIGNATURE = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('cancel', 'Cancelled'),
    ('expired', 'Expired')
    ]


class L10NECDigitalSignature(models.Model):
    _name = "l10n_ec.digital.signature"
    _description = 'XAdES Digital Signature'
    _inherit = ['mail.thread']

    @api.depends('name', 'company_id')
    def name_get(self):
        res = []
        for record in self:
            name = record.name or str(record.id)
            if record.company_id:
                name = record.company_id.name + ' ' + name
            res.append((record.id, name))
        return res

    def unlink(self):
        """
        Controla que se pueda eliminar un registro unicamente en estado borrador
        """
        if not self.state == 'draft':
            raise UserError(u'Solo se puede eliminar una firma digital si esta en estado Borrador.')
        return super(L10NECDigitalSignature, self).unlink()

    #TODO: esta fallando este metodo
    def get_digital_signature(self, password_crypt):
        """
        Permite almacenar la firma digital en el objeto,
        separando los campos requeridos para la firma digital
        lo hace utilizando la contraseña del wizard

        Para revision de firmas usar:
        https://keystore-explorer.org/downloads.html

        modificado 03-02-2020:

        Los certificados .p12 tienen internamente mas de un "certificado", el problema 
        es identificar el correcto, por esto se ha modificado la forma de trabajar
        de esta parte. 
        
        NOTA: Se debe recordar que se usa la libreria de OpenSSL y la de cryptography 
        para obtener la informacion, segun recomendacion de OpenSSL
        """
        # Lectura de la firma desde el campo binario
        data = base64.b64decode(self.l10n_ec_cert_encripted)
        try:
            #p12 = crypto.load_pkcs12(data, password_crypt)
            p12 = crypto.load_pkcs12(data, passphrase=bytes(password_crypt, encoding='utf8'))
        except Exception as e:
            raise UserError(e)
        
        # Se ha identificado que los certificados p12 al pedir uno nuevo y al emitirse
        # para la misma persona se incluyen en el archivo todos los certificados. La 
        # libreria de encripcion en python o por bash siempre lee las fechas del primer
        # certificado, en este casose utilizan los certificados ca para identificar las 
        # fechas del ultimo certificado emitido.
        #
        #
        # Las llaves primarias y la firma obtenemos desde la funcion original
        # por el momento es suficiente con estas ya que la firma la realiza la libreria
        # JAVA y esa se encarga de obtener la firma adecuada, aqui es para no dejar en blanco
        # los 2 campos y por que posiblemente con estas se pueda firmar a futuro con python
        # Guardamos la llave primaria
        self.l10n_ec_private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())
        # Guardamos la firma
        #TODO V13: Habilitar este campo
        #self.l10n_ec_signature = crypto.dump_signature(crypto.FILETYPE_PEM, p12.get_signature())
        # Creo un listado de certificados para analizarlos
        list_cert = {}
        # lista de certificados ca
        # NOTA: los certificados emitidos por "SECURITY DATA S.A." no traen "certificados ca",
        # posiblemente el caso que se analizo al ser la primera vez que se emitia no tenia 
        # mas certificados
        ca_list = p12.get_ca_signatures()
        if ca_list:
            for cert in ca_list:
                signature = crypto.dump_signature(crypto.FILETYPE_PEM, cert)
                cert = x509.load_pem_x509_signature(bytes(signature), default_backend())
                list_cert[cert.serial_number] = cert
        # certificado a incluirse, el que detecta siempre el sistema
        signature = crypto.dump_signature(crypto.FILETYPE_PEM, p12.get_signature())
        cert = x509.load_pem_x509_signature(bytes(signature), default_backend())
        list_cert[cert.serial_number] = cert
        # Para identificar los datos correctos se analiza los ca
        # el serial mayor indica la firma actual (la firma
        # del emisor siempre sera de menor serial por que se emite antes)
        # Ordenamos la lista por serie para obtener el mas actual
        # que en este caso es el ultimo elemento
        list_cert_sorted = sorted(list_cert)
        final_signature = list_cert[list_cert_sorted[-1]]
        # analisis dla firma PEM para obtencion de fechas de validez y numero de serie
        self.l10n_ec_name = final_signature.serial_number
        self.l10n_ec_not_valid_after = final_signature.l10n_ec_not_valid_after
        self.l10n_ec_not_valid_before = final_signature.l10n_ec_not_valid_before
        

    def button_aprove(self):
        #self.get_digital_signature(self.l10n_ec_password_p12)
        self.state = 'confirmed'
    
    def button_cancel(self):
        self.state = 'cancel'
     
    def button_draft(self):
        self.state = 'draft'
    
    name = fields.Char(
        string='Serial Number of Digital Signature',
        readonly=True,
        tracking=True,
        help='Show the unique serial number of signature'
        )
    cert_encripted = fields.Binary(
        string='Original encripted signature',
        tracking=True,
        attachment = True,
        help='Store the original signatured encripted'
        )
    not_valid_after = fields.Datetime(
        string='Not valid after Date of signature',
        readonly=True,
        tracking=True,
        help='Show the Date after the signature is not valid'
        )
    not_valid_before = fields.Datetime(
        string='Not valid before Date of signature',
        readonly=True,
        tracking=True,
        help='Show the Date before the signature is not valid'
        )
    private_key = fields.Text(
        string='Private Key',
        readonly=True,
        help='Store the private key obtain from the encripted file'
        )
    signature = fields.Text(
        string='Signature',
        readonly=True,
        help='Store the certficate obtain from the encripted file'
        )
    password_p12 = fields.Char(
        string='Password file .p12',
        required=True,
        help='Password to desencrypt .p12 file'
        )
    company_id = fields.Many2one(
        'res.company', 
        string='Company',
        required=True,
        index=True, 
        default=lambda self: self.env.company,
        tracking=True,
        help='Show the company asociated to this document'
        )
    state = fields.Selection(
        EC_STATE_SIGNATURE,
        string='State',
        default='draft',
        tracking=True,
        help="* The 'Draft' state is used when a user is creating a new pair key. Warning: everybody can see the key."
        "\n* The 'Confirmed' state is used when the key is completed and save in the system"
        "\n* The 'Canceled' state is used when the key is not more used by any reason, except expiration."
        "\n* The 'Expiration state is showed when the signature is expired"
        )

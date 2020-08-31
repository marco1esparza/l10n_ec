# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import os
import subprocess
import base64
import logging
_logger = logging.getLogger(__name__)


class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'   
    
    def _l10n_ec_sign_digital_xml(self, access_key, cert_encripted, password_p12, draft_electronic_document_in_xml, path_temp='/tmp/'):
        '''
        Realizamos el firmado del documento xml previo a su envio
        Se utiliza libreria externa en JAVA compilada por TRESCLOUD
        Parametros de uso:
            String pathSignature = args[0];
            String passSignature = args[1];
            String xmlPath = args[2];
            String pathOut = args[3];
            String nameFileOut = args[4];
        '''        
        def write_file(path, data):
            '''
            allow write a file
            '''
            f=open(path,'w')
            f.write(data)
            f.close()
        def open_file(path):
            '''
            allow read a file and return the content
            '''    
            f=open(path,'r')
            data = f.read()
            return data
        # todo se maneja por archivo, para evitar problemas se usa la clave para nombrarlos
        # path general: /tmp/
        path_temp = "/tmp/"
        file_p12 = path_temp + access_key + ".p12"
        file_xml = path_temp + access_key + ".xml"
        file_sign_xml = access_key + "_sign.xml"
        # creacion de archivos
        if not cert_encripted:
            _logger.error('La firma digital tiene una longitud de 0 bytes')
            raise NameError('La firma digital tiene una longitud de 0 bytes')
        write_file(file_p12, base64.b64decode(cert_encripted))
        write_file(file_xml, base64.b64decode(draft_electronic_document_in_xml))
        # ejecucion del aplicativo
        JAR_PATH = '../java-lib/3CXAdESBESSSign.jar'
        JAVA_CMD = 'java'
        sign_path = os.path.join(os.path.dirname(__file__), JAR_PATH)
        command = [
            JAVA_CMD,
            '-jar',
            sign_path,
            file_p12,
            password_p12,
            file_xml,
            path_temp,
            file_sign_xml
        ]
        try:
            subprocess.check_output(command)
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            output = e.output
            _logger.error('Llamada a proceso JAVA codigo: %s' % returncode)
            _logger.error('Error: %s' % output)
            raise NameError('Error: %s' % output)
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        res = p.communicate()
        if 'Error:' in res[0]:
            _logger.error('Error en proceso JAVA: %s' % str(res))
            raise NameError('Error al firmar el documento electronico, revise el log del sistema')
        xml_sign = open_file(path_temp + file_sign_xml)
        os.remove(file_p12)
        os.remove(file_xml)
        os.remove(path_temp + file_sign_xml)
        return base64.b64encode(xml_sign)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import os
import subprocess
import base64
import logging
_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError


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
            f.buffer.write(data)
            #f.write(data)
            f.close()
        def open_file(path):
            '''
            allow read a file and return the content
            '''    
            f=open(path,'rb')
            data = f.read()
            return data
        def run_command(command):
            p = subprocess.Popen(command,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.STDOUT)
            
            
            return iter(p.stdout.readline, b'')
        # todo se maneja por archivo, para evitar problemas se usa la clave para nombrarlos
        # path general: /tmp/
        path_temp = "/tmp/"#"."#
        file_p12 = path_temp + access_key + ".p12"
        file_xml = path_temp + access_key + ".xml"
        file_sign_xml = access_key + "_sign.xml"
        # creacion de archivos
        if not cert_encripted:
            raise UserError('La firma digital tiene 0 bytes, quizá deba subir su firma digital en Contabilidad / Configuración / Firmas Digitales')
        write_file(file_p12, base64.b64decode(cert_encripted))
        write_file(file_xml, base64.b64decode(draft_electronic_document_in_xml))
        # ejecucion del aplicativo
        JAR_PATH = '../java-lib/3CXAdESBESSSign.jar'
        JAVA_CMD = '/home/odoo/jdk-14.0.2/bin/java' #Odoo.sh path for java
        try: #lets find out if java is installed elsewhere
            has_java_installed = list(run_command([
                'java',
                '-XX:MaxHeapSize=512m', 
                '-XX:InitialHeapSize=512m',
                '-XX:CompressedClassSpaceSize=64m',
                '-XX:MaxMetaspaceSize=128m',
                '-XX:+UseConcMarkSweepGC',
                '-version',
                ]))
        except FileNotFoundError:
            print("File does not exist")
        except:
            raise
        else:
            #no exception raised, java is installed
            if has_java_installed:
                JAVA_CMD = 'java'
        finally:
            pass
        sign_path = os.path.join(os.path.dirname(__file__), JAR_PATH)
        command = [
            JAVA_CMD,
            #Parameters to avoid Error occurred during initialization of VM Could not allocate metaspace: 1073741824 bytes
            '-XX:MaxHeapSize=512m', 
            '-XX:InitialHeapSize=512m',
            '-XX:CompressedClassSpaceSize=64m',
            '-XX:MaxMetaspaceSize=128m',
            '-XX:+UseConcMarkSweepGC',
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
        except FileNotFoundError as err:
            raise UserError('Error, perhaps Java is not installed, contact technical support: %s' % str(err))
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            output = e.output
            _logger.error('Llamada a proceso JAVA codigo: %s' % returncode)
            _logger.error('Error: %s' % output)
            raise UserError('Error: %s' % output)
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        #para que esta secci[on... parece repetida__
        outs, errs = p.communicate()
        if errs:
            raise UserError('Error en proceso JAVA: %s' % str(errs))
        xml_sign = open_file(path_temp + file_sign_xml)
        os.remove(file_p12)
        os.remove(file_xml)
        os.remove(path_temp + file_sign_xml)
        return base64.b64encode(xml_sign).decode()


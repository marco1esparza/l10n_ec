# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from lxml import etree
import unicodedata
import re
import os


def _load_xsd(file_):
    '''
    Carga los archivos XSD a memoria
    '''
    try:
        return etree.XMLSchema(etree.parse(file_))
    except etree.XMLSchemaParseError as e:
        raise ImportError(
            'Cannot generate XSD Instance: %s, with data:\n%r' % (type(e).__name__, e.__dict__)
        )

#generamos las instancias XSD
path = os.path.abspath(os.path.dirname(__file__))
XSD_SRI_110_FACTURA = _load_xsd(path+'/../resources/sri_110_factura.xsd')
XSD_SRI_110_NOTA_CREDITO = _load_xsd(path+'/../resources/Nota_Credito_V_1_1_0.xsd')


def get_SRI_normalized_text(text):
    '''
    Estandariza la codificacion a ASCII para mapear acentos y eliminar
    caracteres extraños.
    Acepta cualquier caracter diferente del fin de linea.
    Se ha conversado con Santiago este tema y se decide eliminar solo los
    fines de linea pues es lo que indica la expresion regular del pattern
    [^\n]* utilizado en los campos de tipo texto del xsd.
    '''
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii','ignore')
    #TODO: implementar la linea comentada y borrar la siguiente
    #text_SRI_compliant = re.sub('\n', '', ascii_text)
    text_SRI_compliant = ascii_text
    text_SRI_compliant = text_SRI_compliant.strip()
    return text_SRI_compliant

def clean_xml(etree_content, context={}):
    """
    Genera un XML compacto eliminado lineas en blanco y saltos de linea
    Ademas codifica el texto para permitir
    """
    return etree.tostring(etree_content, pretty_print=False, encoding='UTF-8')

def validate_xml_vs_xsd(xml_content, xsd_instance):
    '''
    Dado un contenido XML de entrada, y un contenido XSD de validacion XML.
    Dado una funcion de validacion semantica (algo de lo que un XSD no se puede encargar).
    Primero ocurre una validacion a nivel XML/XSD.
    '''
    try:
        root = etree.XML(xml_content.strip())
    except Exception as e:
        raise ValidationError('Error en la estructura del XML: %s' % str(e))
    if not xsd_instance.validate(root):
        str_error = "\n"
        for error in xsd_instance.error_log: 
            str_error += error.message + "\n"
        raise ValidationError('El XML presenta los siguientes errores al validar contra el XSD: %s' % str_error)
    
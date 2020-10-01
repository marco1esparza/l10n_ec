# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unicodedata
import re

def get_name_only_characters(name):
        '''
        Elimina/reemplaza del nombre caracteres particulares como:
        .,-/()´&
        Esto lo hace especifcamente por caracter
        Ademas normaliza el texto segun estandar SRI
        '''
        text = name
        if text:
            text = text.replace('.', '')
            text = text.replace(',', '')
            text = text.replace('-', ' ')
            text = text.replace('/', ' ')
            text = text.replace('(', '')
            text = text.replace(')', '')
            text = text.replace(u'´', ' ') 
            text = get_printable_ASCII_text(text)
        return text

def get_printable_ASCII_text(text):
    """
    Reemplazo de la antigua funcion strip_accents_and_tildes
    Entrega solo caracteres que se encuentran entre los imprimibles ASCII (solo es referencial)
    Orden de funcionamiento:
     - Mapeo de caracteres a posibles caracteres ASCII
     - Caracteres no compatibles son ignorados
     - Mapeo de caracteres especiales: ñ->n, Ñ->N, &->Y
     - Limpieza de espacios en blanco al incio y al final 
    """
    mapping = {
        'ñ': 'n',
        'Ñ': 'N',
        '&': 'Y',
        '_': ' '
        }
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii','ignore')
    ascii_replaced = multi_replace(ascii_text, mapping)
    return ascii_replaced.strip()

def multi_replace(text, replacements):
    '''
    Realiza sustituciones mediante expresiones regulares.
    '''
    rep = dict(('(%s)' % re.escape(k), v) for k, v in replacements.items())
    pattern = re.compile("|".join(rep.keys()))
    return pattern.sub(lambda m: replacements[m.group(0)], text)

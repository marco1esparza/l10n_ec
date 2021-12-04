# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def _l10n_ec_set_ecommerce_labels(cr, registry):
    '''Se settea los valores para la traducción de los labels de campos en inglés como: "NIF" (cédula), "Company Name" (Compañía) y "Name" (Nombre)'''
    # TODO: Realizar que sea general para otras traducciones
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.cr.execute(
        '''
            SELECT id 
            FROM ir_translation 
            WHERE lang = 'es_EC' 
                AND module = 'website_sale' 
                AND src = 'TIN / VAT'
        ''')
    records = env.cr.dictfetchall()
    total_records = len(records)
    for record in records:
        translation = env['ir.translation'].browse(record['id'])
        translation.write({'value': 'Cédula/RUC/Pasaporte'})
        _logger.info(u'Cambiando traducción de label de campo de cédula en módulo de Ecommerce. Total: %s registros' % total_records)
    env.cr.execute(
        '''
            SELECT id 
            FROM ir_translation 
            WHERE lang = 'es_EC' 
                AND module = 'website_sale' 
                AND src = 'Company Name'
        ''')
    records = env.cr.dictfetchall()
    total_records = len(records)
    for record in records:
        translation = env['ir.translation'].browse(record['id'])
        translation.write({'value': 'Nombre para la factura'})
        _logger.info(u'Cambiando traducción de label de campo de compañía en módulo de Ecommerce. Total: %s registros' % total_records)
    env.cr.execute(
        '''
            SELECT id 
            FROM ir_translation 
            WHERE lang = 'es_EC' 
                AND module = 'website_sale' 
                AND type = 'model_terms' 
                AND src = 'Name'
        ''')
    records = env.cr.dictfetchall()
    total_records = len(records)
    for record in records:
        translation = env['ir.translation'].browse(record['id'])
        translation.write({'value': 'Su nombre'})
        _logger.info(u'Cambiando traducción de label de campo de nombre en módulo de Ecommerce. Total: %s registros' % total_records)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    _SOURCE = [
        ('proyectox', 'Proyectox Versión 8'),
        ('trescloud_v7', 'Trescloud Versión 7'),
        ('trescloud_v10', 'Trescloud Versión 10'),
        ('trescloud_v13', 'Trescloud Versión 13'),
        ('trescloud_v14', 'Trescloud Versión 14'),
        ('trescloud_v15', 'Trescloud Versión 15'),
        ('trescloud_v16', 'Trescloud Versión 16'),
        ('other', 'Otros proveedores')
    ]

    _REFUND_VS_INVOICE_CONTROL = [
        ('local_refund', 'Notas de crédito locales'),
        ('without_control', 'Sin control')
    ]

    db_source = fields.Selection(
        _SOURCE,
        string='Origen',
        default='trescloud_v14',
        help='Campo informativo del origen de la base de datos del cual se migro la información, permite ejecutar ciertos script de migración.'
    ) #TODO V15, moverlo a la tabla de parametros
    l10n_ec_refund_value_control = fields.Selection(
        _REFUND_VS_INVOICE_CONTROL,
        string='Control del valor de las notas de crédito',
        default='local_refund',
        help='En el caso de que la opción Notas de crédito locales este marcado, validará que la suma de las notas de crédito emitidas no sobrepase el valor de la factura.'
    )

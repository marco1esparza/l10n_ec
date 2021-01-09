# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import re


class L10nEcSRIPrinterPoint(models.Model):
    _inherit = 'l10n_ec.sri.printer.point'
    
    automatic_numbering = fields.Boolean(
        string=u'Numeración Automática',
        default=True,
        help=u'Desactivela para "igualarse" facturas digitados en su anterior sistema ' 
             u'(aplica para documentos emitidos por mi empresa tales como facturas, notas de crédito, liquidaciones de compra',
        track_visibility='onchange',
    )
    
    @api.onchange('automatic_numbering')
    def _onchange_partner_id(self):
        if not self.automatic_numbering:
            return {
                'warning': {'title': _('Advertencia'), 'message': _('Esta es una opción avanzada, si no está seguro descarte los cambios'),},
                 }
    
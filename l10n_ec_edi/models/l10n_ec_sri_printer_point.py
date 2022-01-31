# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import re


class L10nEcSRIPrinterPoint(models.Model):
    _name = 'l10n_ec.sri.printer.point'
    _description = "Printer Point"
    _order = 'sequence, id'
    _inherit = ['mail.thread']
    
    automatic_numbering = fields.Boolean(
        string=u'Numeración Automática',
        default=True,
        help=u'Desactivela para "igualarse" facturas digitados en su anterior sistema ' 
             u'(aplica para documentos emitidos por mi empresa tales como facturas, notas de crédito, liquidaciones de compra',
        tracking=True,
    )
    
    @api.onchange('automatic_numbering')
    def _onchange_partner_id(self):
        if not self.automatic_numbering:
            return {
                'warning': {'title': _('Advertencia'), 'message': _('Esta es una opción avanzada, si no está seguro descarte los cambios'),},
                 }
    
    _sql_constraints = [('l10n_ec_sri_printer_point_name_unique', 'unique(name, company_id)', 'El punto de emisión debe ser único por compañía.')]
    
    name = fields.Char(
        string='Printer Point',
        size=7, copy=False,
        help='This number is assigned by the SRI',
        tracking=True,
    )

    sequence = fields.Integer(default=10,help="The first printer is used by default when creating new invoices, unless specified otherwise in user profile",)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)
        
    allow_electronic_document = fields.Boolean(
        string=u'Emitir documentos electrónicos',
        default=True,
        help=u'Active esta opción para habilitar la emisión de doc electrónicos',
        tracking=True,
    )
    
    printer_point_address = fields.Char(string='Printer Point Address', help='This is the address used for invoice reports of this Printer Point')

    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the SRI Printer Point without removing it.",
        tracking=True,
    )

    @api.constrains('name')
    def _check_name(self):
        valid = re.search("([0-9]{3,}-[0-9]{3,})", self.name)
        if not valid:
            raise ValidationError('El numero del Punto de Emision debe ser del formato ###-### (Ej. 001-001)')

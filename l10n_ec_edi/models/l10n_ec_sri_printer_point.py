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

    @api.depends('name')
    def _get_prefix(self):
        '''
        Este método genera el prefijo concatenando la tienda y el punto de emisión
        '''
        for printer in self:
            if printer.name:
                printer.prefix = printer.name + '-'

    _sql_constraints = [('l10n_ec_sri_printer_point_name_unique', 'unique(name, company_id)', 'El punto de emisión debe ser único por compañía.')]
    
    name = fields.Char(string='Printer Point', size=7, copy=False, help='This number is assigned by the SRI')
    
    sequence = fields.Integer(default=10,help="The first printer is used by default when creating new invoices, unless specified otherwise in user profile",)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)
    
    prefix = fields.Char(compute='_get_prefix', string='Printer Prefix', method=True)
    
    allow_electronic_document = fields.Boolean(string=u'Emitir documentos electrónicos', default=True, help=u'Active esta opción para habilitar la emisión de doc electrónicos')
    
    sequence_ids = fields.One2many('ir.sequence', 'l10n_ec_printer_id', string="Sequences")
    
    printer_point_address = fields.Char(string='Printer Point Address', help='This is the address used for invoice reports of this Printer Point')

    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the SRI Printer Point without removing it."
    )

    @api.model
    def create(self, values):
        """ Create Document sequences after create the journal """
        res = super().create(values)
        res._create_document_sequences()
        return res

    def _create_document_sequences(self):
        self.ensure_one()
        if self.company_id.country_id != self.env.ref('base.ec'):
            return True

        sequences = self.sequence_ids
        sequences.unlink()

        # Create Sequences
        internal_types = ['invoice', 'debit_note', 'credit_note']
        domain = [('country_id.code', '=', 'EC'), ('internal_type', 'in', internal_types),
                  ('l10n_ec_authorization', '=', 'own'), ('code', '!=', '41')]
        documents = self.env['l10n_latam.document.type'].search(domain)
        for document in documents:
            sequences |= self.env['ir.sequence'].create({
                'name': '%s - %s' % (document.name, self.name),
                'padding': 9, 'prefix': self.prefix,
                'l10n_latam_document_type_id': document.id,
                'l10n_ec_printer_id': self.id,
            })
        return sequences

    @api.constrains('name')
    def _check_name(self):
        valid = re.search("([0-9]{3,}-[0-9]{3,})", self.name)
        if not valid:
            raise ValidationError('El numero del Punto de Emision debe ser del formato ###-### (Ej. 001-001)')

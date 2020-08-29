# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import re


class L10NECSRIPrinterPoint(models.Model):
    _name = 'l10n.ec.sri.printer.point'
    _rec_name = 'l10n_ec_name'
    _auto = True

    def unlink(self):
        '''
        Invocamos el metodo unlink para eliminar el punto de impresion y las secuencias asociadas
        '''
        for printer in self:
            if printer.l10n_ec_invoice_sequence_id:
                printer.l10n_ec_invoice_sequence_id.unlink()
            if printer.l10n_ec_credit_note_sequence_id:
                printer.l10n_ec_credit_note_sequence_id.unlink()
            if printer.l10n_ec_debit_note_sequence_id:
                printer.l10n_ec_debit_note_sequence_id.unlink()
            if printer.l10n_ec_purchase_clearance_sequence_id:
                printer.l10n_ec_purchase_clearance_sequence_id()
            if printer.l10n_ec_withhold_sequence_id:
                printer.l10n_ec_withhold_sequence_id.unlink()
            if printer.l10n_ec_waybill_sequence_id:
                printer.l10n_ec_waybill_sequence_id.unlink()
        return super(L10NECSRIPrinterPoint, self).unlink()

    @api.model
    def get_next_sequence_number(self, printer, document_type, number):
        '''
        For a specific type of document, the current printer tries to get
          the next number from the sequence. if no sequence exists, we must
          return the same input number or current printer's prefix. If the
          number is well-formatted and for the current printer point, we must
          return such number - respecting it.
        ''' 
        number = (number or '').strip()
        if not printer or re.match('^\d{3}-\d{3}-\d{9}$', number) and number.startswith(printer.l10n_ec_prefix):
            return number 
        sequence = {
            'invoice': printer.l10n_ec_invoice_sequence_id,
            'refund': printer.l10n_ec_credit_note_sequence_id,
            'debit': printer.l10n_ec_debit_note_sequence_id,
            'purchClear': printer.l10n_ec_purchase_clearance_sequence_id,
            'withhold': printer.l10n_ec_withhold_sequence_id,
            'waybill': printer.l10n_ec_waybill_sequence_id
        }.get(document_type, False)
        if not sequence:
            return number or printer.l10n_ec_prefix
        return sequence.next_by_id()

    @api.depends('l10n_ec_name')
    def _get_prefix(self):
        '''
        Este método genera el prefijo concatenando la tienda y el punto de emisión
        '''
        for printer in self:
            if printer.l10n_ec_name:
                printer.l10n_ec_prefix = printer.l10n_ec_name + '-'

    #Columns
    l10n_ec_name = fields.Char(
        string='Printer Point', size=7,
        copy=False, 
        help='This number is assigned by the SRI'
        )
    l10n_ec_prefix = fields.Char(
        compute='_get_prefix',
        string='Printer Prefix',
        method=True,
        store=True, #TODO: No ganamos mucho con que sea store=True.. mejor false
        help=''
        )
    l10n_ec_allow_electronic_document = fields.Boolean(
        string=u'Permitir la emisión de doc electrónicos', 
        help=u'Active esta opción para habilitar la emisión de doc electrónicos'
        )
    l10n_ec_invoice_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Customer Invoices Sequential',
        domain=[('code', '=', 'l10n.ec.sri.printer.point')],
        copy=False,
        help='If specified, will be used by the printer point to specify the next number for the invoices'
        )
    l10n_ec_credit_note_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Credit Notes Sequential',
        domain=[('code', '=', 'l10n.ec.sri.printer.point')],
        copy=False,
        help='If specified, will be used by the printer point to specify the next number for the credit notes'
        )
    l10n_ec_debit_note_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Debit Notes Sequential',
        domain=[('code', '=', 'l10n.ec.sri.printer.point')],
        copy=False,
        help='If specified, will be used by the printer point to specify the next number for the debit notes'
        )
    l10n_ec_purchase_clearance_sequence_id = fields.Many2one(
        'ir.sequence', 
        string=u'Secuencial para liquidación de compras',
        domain=[('code', '=', 'l10n.ec.sri.printer.point')],
        copy=False,
        help=u'Si llena este campo, será usado por el punto de emisión para especificar la secuencia para la liquidaciones de compra electrónicas.'
        )
    l10n_ec_withhold_sequence_id = fields.Many2one('ir.sequence',
        string='Withholds Sequential',
        domain=[('code', '=', 'l10n.ec.sri.printer.point')],
        copy=False,
        help='If specified, will be used by the printer point to specify the next number for the withholds'
        )
    l10n_ec_waybill_sequence_id = fields.Many2one('ir.sequence',
            string='Waybills Sequential',
            domain=[('code', '=', 'l10n.ec.sri.printer.point')],
            copy=False, 
            help='If specified, will be used by the printer point to specify the next number for the waybills'
            )    
    l10n_ec_company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id.id,
        help=''
        )
    l10n_ec_printer_point_address = fields.Char(
        string='Printer Point Address',
        help='This is the address used for invoice reports of this Printer Point'
        )

    @api.constrains('l10n_ec_name')
    def _number_unique(self):
        '''
        Este método verifica que el punto de impresion sea único
        '''
        for printer in self:
            duplicate_ids = self.search([('l10n_ec_name','=',printer.l10n_ec_name), ('l10n_ec_company_id','=',printer.l10n_ec_company_id.id), ('id','!=',printer.id)])
            if duplicate_ids:
                raise ValidationError(u'El punto de emisión debe ser único por compañía.')

    @api.constrains('l10n_ec_invoice_sequence_id', 'l10n_ec_credit_note_sequence_id', 'l10n_ec_debit_note_sequence_id',
                    'l10n_ec_purchase_clearance_sequence_id', 'l10n_ec_withhold_sequence_id', 'l10n_ec_waybill_sequence_id')
    def _verify_repeated_sequences(self):
        '''
        Este metodo garantiza que no existan secuenciales consumidos en otros puntos de impresion
        '''
        sequences = []
        for printer in self:
            if printer.l10n_ec_invoice_sequence_id:
                sequences.append(printer.l10n_ec_invoice_sequence_id.id)
            if printer.l10n_ec_credit_note_sequence_id:
                sequences.append(printer.l10n_ec_credit_note_sequence_id.id)
            if printer.l10n_ec_debit_note_sequence_id:
                sequences.append(printer.l10n_ec_debit_note_sequence_id.id)
            if printer.l10n_ec_purchase_clearance_sequence_id:
                sequences.append(printer.l10n_ec_purchase_clearance_sequence_id.id)
            if printer.l10n_ec_withhold_sequence_id:
                sequences.append(printer.l10n_ec_withhold_sequence_id.id)
            if printer.l10n_ec_waybill_sequence_id:
                sequences.append(printer.l10n_ec_waybill_sequence_id.id)
            if sequences:
                found = self.search(['&', ('id', '!=', printer.id),
                                     '|', ('l10n_ec_invoice_sequence_id', 'in', sequences),
                                     '|', ('l10n_ec_credit_note_sequence_id', 'in', sequences),
                                     '|', ('l10n_ec_debit_note_sequence_id', 'in', sequences),
                                     '|', ('l10n_ec_purchase_clearance_sequence_id', 'in', sequences),
                                     '|', ('l10n_ec_withhold_sequence_id', 'in', sequences),
                                          ('l10n_ec_waybill_sequence_id', 'in', sequences)])
                if found:
                    raise ValidationError(u'Al menos uno de los secuenciales está repetido o en uso dentro de otro punto de emisión.')

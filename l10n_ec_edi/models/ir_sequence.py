# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    l10n_ec_printer_id = fields.Many2one('l10n_ec.sri.printer.point', string='Punto de emisión', ondelete="cascade")

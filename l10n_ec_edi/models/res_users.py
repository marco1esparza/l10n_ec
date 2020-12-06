# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Users(models.Model):
    _inherit = 'res.users'
    
    #TODO V15, moverlo al l10n_ec_account_extended
    l10n_ec_printer_id = fields.Many2one(
        'l10n_ec.sri.printer.point',
        string='Default Printer Point',
        ondelete='restrict',
        help='Punto de emisión asignado al usuario, por ejemplo 001-001'
        )

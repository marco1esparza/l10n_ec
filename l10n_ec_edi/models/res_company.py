# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'

    #Columns
    #Estos dos campos son utiles para la emisión de facturas electrónicas
    l10n_ec_special_contributor_number = fields.Char(
        string='Special Tax Contributor Number',
        track_visibility='onchange',
        help='If set, your company is considered a Special Tax Contributor, this number will be printed in electronic invoices and reports'
        )
    l10n_ec_forced_accounting = fields.Boolean(
        string='Forced to Keep Accounting Books',
        track_visibility='onchange',
        help='If set you are obligated to keep accounting, it will be used for printing electronic invoices and reports'
        )

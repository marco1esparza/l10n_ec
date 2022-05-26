# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ec_legal_name = fields.Char(  # TODO not used (for now ?)
        string="Company legal name"
    )
    l10n_ec_production_env = fields.Boolean(
        string="Use production servers",
        default=False,
    )
    l10n_ec_certificate_id = fields.Many2one(
        string="Certificate file for Ecuadorian EDI",
        comodel_name="l10n_ec.certificate",
        ondelete="restrict",
    )
    l10n_ec_special_contributor_number = fields.Char(
        string='Special Tax Contributor Number',
        help='If set, your company is considered a Special Tax Contributor, this number will be printed in electronic invoices and reports'
    )
    l10n_ec_forced_accounting = fields.Boolean(
        string='Forced to Keep Accounting Books',
        default=True,
        help='Check if you are obligated to keep accounting books, will be used for printing electronic invoices and reports',
    )
    l10n_ec_regime = fields.Selection([
        ('regular', 'Regimen Regular (sin msgs adicionales en el RIDE)'),
        ('rimpe', 'Régimen RIMPE')
    ],
        string=u"Regimen",
        default='regular',
        required=True,
        # TODO help text ?
    )

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ec_contributor_type_id = fields.Many2one(
        'l10n_ec.contributor.type',
        company_dependent=True,
        string='Contributor Type',
        help=''
    )

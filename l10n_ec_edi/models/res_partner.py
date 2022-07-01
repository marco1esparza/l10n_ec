# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + ['l10n_ec_contributor_type_id']

    l10n_ec_contributor_type_id = fields.Many2one(
        'l10n_ec.contributor.type',
        string='Contributor Type',
        help=''
    )

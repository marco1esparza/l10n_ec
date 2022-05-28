# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    #TODO JOSE: Debe ser un campo property
    contributor_type_id = fields.Many2one(
        'l10n_ec.contributor.type',
        string='Contributor Type',
        help=''
        )

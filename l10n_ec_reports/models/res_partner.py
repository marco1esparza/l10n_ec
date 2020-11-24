# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    #Columns
    l10n_ec_related_part = fields.Boolean(
        string='Related Part',
        help='Select the option if the company is a related party, the system will use other accounting '
             'accounts to record purchases and sales. Related parties are other companies or persons that '
             'participate directly or indirectly in the management, administration, control or capital of '
             'our company. Example of related party may be a shareholder of our company.'
        )

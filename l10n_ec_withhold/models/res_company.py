# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    #Columns
    l10n_ec_issue_withholds = fields.Boolean(
        string='Issue Withhols',
        default=True,
        help='If set Odoo will automatically compute purchase withholds for relevant vendor bills'
        )
    l10n_ec_fallback_profit_withhold_goods = fields.Many2one(
        'account.tax',
        string='Withhold consumibles',
        help='When no profit withhold is found in partner or product, if product is a stockable or consumible'
        'the withhold fallbacks to this tax code'
        )
    l10n_ec_fallback_profit_withhold_services = fields.Many2one(
        'account.tax',
        string='Withhold services',
        help='When no profit withhold is found in partner or product, if product is a service or not set'
        'the withhold fallbacks to this tax code'
        )    
    l10n_ec_profit_withhold_tax_credit_card = fields.Many2one(
        'account.tax',
        string='Withhold Credit Card',
        help='When payment method will be credit card apply this withhold',
        )

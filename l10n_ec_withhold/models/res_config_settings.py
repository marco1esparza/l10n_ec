# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    #Columns
    l10n_ec_issue_withholds = fields.Boolean(
        string='Issue Withhols',
        related='company_id.l10n_ec_issue_withholds',
        readonly=False
        )
    l10n_ec_fallback_profit_withhold_goods = fields.Many2one(
        'account.tax', string='Withhold consumibles',
        related='company_id.l10n_ec_fallback_profit_withhold_goods',
        readonly=False
        )
    l10n_ec_fallback_profit_withhold_services = fields.Many2one(
        'account.tax', string='Withhold services',
        related='company_id.l10n_ec_fallback_profit_withhold_services',
        readonly=False
        )
    l10n_ec_profit_withhold_tax_credit_card = fields.Many2one(
        'account.tax', string='Withhold Credit Card',
        related='company_id.l10n_ec_profit_withhold_tax_credit_card',
        readonly=False
        )

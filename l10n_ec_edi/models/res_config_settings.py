# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    l10n_ec_legal_name = fields.Char(
        related="company_id.l10n_ec_legal_name",
        readonly=False,
    )
    l10n_ec_production_env = fields.Boolean(
        related="company_id.l10n_ec_production_env",
        readonly=False,
    )
    l10n_ec_certificate_id = fields.Many2one(
        related="company_id.l10n_ec_certificate_id",
        readonly=False,
    )
    l10n_ec_forced_accounting = fields.Boolean(
        related="company_id.l10n_ec_forced_accounting",
        readonly=False,
    )
    l10n_ec_special_contributor_number = fields.Char(
        related="company_id.l10n_ec_special_contributor_number",
        readonly=False,
    )
    l10n_ec_wihhold_agent_number = fields.Char(
        related="company_id.l10n_ec_wihhold_agent_number",
        readonly=False,
    )
    l10n_ec_regime = fields.Selection(
        related="company_id.l10n_ec_regime",
        readonly=False,
    )
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

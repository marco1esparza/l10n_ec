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
    l10n_ec_wihhold_agent_number = fields.Char(
        string='Withhold Agent Number',
        help=u"Last digits from the SRI resolution number in which your company became a designated withholder agent. \n"
        u"If the resolution number where NAC-DNCRASC20-00000001 ten the number should be 1",
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
        help=u"Will show an additional label on the RIDE and XML called 'CONTRIBUYENTE REGIMEN RIMPE', \n"
        u"select it if your company is in the SRI Excel registry, \n"
        u"It doesn't affect the computation of withholds\n"
    )
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

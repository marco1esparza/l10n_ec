# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContributorType(models.Model):
    _name = 'l10n_ec.contributor.type'
    _description = 'Contributor Type'
    _order = 'sequence, id'
    
    sequence = fields.Integer(
        default=15
    )
    name = fields.Char(
        string='Name',
        required=True,
    )
    profit_withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Profit withhold',
        domain=[('tax_group_id.l10n_ec_type', 'in', ('withhold_income_sale', 'withhold_income_purchase')),('type_tax_use', '=', 'none')],
        help='This tax is suggested on vendors withhold wizard based on prevalence. '
        'The profit withhold prevalence order is payment method (credit cards retains 0%), this contributor type, then product, finally fallback on account settings'
    )
    vat_goods_withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Goods VAT withhold',
        domain=[('tax_group_id.l10n_ec_type', 'in', ('withhold_vat_sale', 'withhold_vat_purchase')),('type_tax_use', '=', 'none')],
        help='This tax is suggested on vendors withhold wizard for consumable and stockable products, if not set no vat withhold is suggested'
    )
    vat_services_withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Services VAT withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', ('withhold_vat_sale', 'withhold_vat_purchase')),('type_tax_use', '=', 'none')],
        help='This tax is suggested on vendors withhold wizard for services, if not set no vat withhold is suggested'
    )
    active = fields.Boolean(
        default=True,
        help='Set active to false to hide the Contributor Type without removing it.',
    )

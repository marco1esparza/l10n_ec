# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContributorType(models.Model):
    _name = 'l10n_ec.contributor.type'
    _description = 'Contributor Type'
    _order = 'sequence, id'
    _inherit = ['mail.thread']
    
    sequence = fields.Integer(
        default=15
        )
    name = fields.Char(
        string='Name',
        copy=False,
        tracking=True,
        help='',
        )
    profit_withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Force profit withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'),('type_tax_use', '=', 'purchase')],
        help='If set forces the vat withhold tax on applicable purchases (also a withhold is required on document type). '
        'The profit withhold prevalence order is payment method (credit cards retains 0%), then partner, then product'
        )
    vat_goods_withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Goods VAT withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_vat'),('type_tax_use', '=', 'purchase')],
        help='If set forces vat withhold in invoice lines with product in applicable purchases (also depends on document type)'
        )
    vat_services_withhold_tax_id = fields.Many2one(
        'account.tax',
        string='Services VAT withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_vat'),('type_tax_use', '=', 'purchase')],
        help='This field defines the VAT withholding tax for services'
        )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company
        )
    active = fields.Boolean(
        default=True,
        help='Set active to false to hide the Contributor Type without removing it.',
        tracking=True
    )

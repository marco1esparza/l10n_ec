# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'
    
    l10n_ec_vat_withhold_goods = fields.Many2one(
        'account.tax',
        string='Goods VAT withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_vat'),('type_tax_use', '=', 'purchase')],
        oldname='withhold_tax_for_goods',
        help='If set forces vat withhold in invoice lines with product in applicable purchases (also depends on document type)')
    l10n_ec_vat_withhold_services = fields.Many2one(
        'account.tax',
        string='Services VAT withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_vat'),('type_tax_use', '=', 'purchase')],
        oldname='withhold_tax_for_services',
        help='This field defines the VAT withholding tax for services'
        )
    
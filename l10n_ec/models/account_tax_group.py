# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

_TYPE_EC = [
    ("vat12", "VAT 12%"),
    ("vat14", "VAT 14%"),
    ("zero_vat", "VAT 0%"),
    ("not_charged_vat", "VAT Not Charged"),
    ("exempt_vat", "VAT Exempt"),
    ("withhold_vat_sale", "VAT Withhold Sale"),
    ("withhold_vat_purchase", "VAT Withhold Purchase"),
    ("withhold_income_sale", "Profit Withhold Sale"),
    ("withhold_income_purchase", "Profit Withhold Purchase"),
    ("ice", "Special Consumptions Tax (ICE)"),
    ("irbpnr", "Plastic Bottles (IRBPNR)"),
    ("outflows_tax", "Exchange Outflows"),
    ("other", "Others"),
]


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    l10n_ec_type = fields.Selection(
        _TYPE_EC, string="Type Ecuadorian Tax", help="Ecuadorian taxes subtype"
    )

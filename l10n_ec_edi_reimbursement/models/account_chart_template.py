# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """
        Se sobrescribe para cargar cuenta de producto de reembolso.
        """
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        company._create_account_refund_product()
        return res

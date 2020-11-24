# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def get_paperformat(self):
        paperformat_id = super(IrActionsReport, self).get_paperformat()
        if self.env.company.country_code == 'EC' and self.report_name in ('account.report_invoice') and not self.paperformat_id:
            paperformat_id = self.env.ref('l10n_ec_edi.paperformat_euro_no_margin')
        return paperformat_id

# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.depends('type', 'company_id', 'company_id.country_id')
    def _compute_compatible_edi_ids(self):
        res = super()._compute_compatible_edi_ids()
        factur_x = self.env.ref('account_edi_facturx.edi_facturx_1_0_05', raise_if_not_found=False)

        for journal in self.filtered(lambda j: j.country_code == 'EC'):
            if factur_x:
                journal.compatible_edi_ids -= factur_x
        return res

    @api.depends('type', 'company_id', 'company_id.country_id')
    def _compute_edi_format_ids(self):
        res = super()._compute_edi_format_ids()
        factur_x = self.env.ref('account_edi_facturx.edi_facturx_1_0_05', raise_if_not_found=False)

        for journal in self.filtered(lambda j: j.country_code == 'EC'):
            if factur_x:
                journal.edi_format_ids -= factur_x
        return res
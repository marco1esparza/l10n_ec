# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools.misc import format_date


class report_print_check(models.Model):
    _inherit = 'account.payment'

    def _check_build_page_info(self, i, p):
        page = super(report_print_check, self)._check_build_page_info(i, p)
        page.update({
            'payment_date_ecuador': format_date(self.env, self.date, date_format='yyyy-MM-dd'),
        })
        return page

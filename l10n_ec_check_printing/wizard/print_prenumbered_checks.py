# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PrintPreNumberedChecks(models.TransientModel):
    _inherit = "print.prenumbered.checks"
    
    @api.onchange('next_check_number')
    def onchange_next_check_number(self):
        #Ecuadorian check numbers has always 6 digits
        if not self.env.company.country_code == 'EC':
            return True
        if len(self.next_check_number) < 6:
            self.next_check_number = self.next_check_number.zfill(6)
    
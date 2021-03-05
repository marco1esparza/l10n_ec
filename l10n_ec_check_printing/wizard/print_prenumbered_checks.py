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
    
    def print_checks(self):
        #save check beneficiary
        res = super(PrintPreNumberedChecks, self).print_checks()
        payments = self.env['account.payment'].browse(self.env.context['payment_ids'])
        for payment in payments:
            payment.l10n_ec_check_beneficiary_name = self.l10n_ec_check_beneficiary_name or payment.partner_id.commercial_partner_id.name
        return res
    
    @api.depends()
    def _l10n_ec_compute_singlepayment(self):
        payment_ids = self.env.context['payment_ids']
        l10n_ec_singlepayment = False
        if len(payment_ids) == 1:
            l10n_ec_singlepayment = True
        self.l10n_ec_singlepayment = l10n_ec_singlepayment
    
    l10n_ec_check_beneficiary_name = fields.Char(
        string='Check Beneficiary',
        help='Supplier name to print in check, usefull as sometimes it is required to issue the check to other supplier or to a third party'
        )
    l10n_ec_singlepayment = fields.Boolean(
        string='Multipayment',
        compute='_l10n_ec_compute_singlepayment',
        )

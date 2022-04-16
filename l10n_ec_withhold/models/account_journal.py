# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    @api.onchange('company_id', 'type', 'l10n_ec_withhold')
    def onchange_withhold_type(self):
        self.l10n_latam_use_documents = (self.type in ['sale', 'purchase'] and self.l10n_latam_company_use_documents) or \
                                        (self.type in ['general'] and self.l10n_latam_company_use_documents and self.l10n_ec_withhold in ['sale', 'purchase'])

    _L10n_EC_WITHHOLD = [
        ('sale', 'Sales'),
        ('purchase', 'Purchases')
    ]

    #Columns
    l10n_ec_withhold = fields.Selection(
        _L10n_EC_WITHHOLD,
        string='Withhold'
        )

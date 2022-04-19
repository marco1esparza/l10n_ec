# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    @api.onchange('type', 'l10n_ec_withhold_type')
    def onchange_withhold_type(self):
        #TODO: Make method specific for Ecuador only
        if self.type != 'general':
            self.l10n_ec_withhold_type = False
        elif self.type == 'general' and self.l10n_ec_withhold_type == 'in_withhold':
            self.l10n_latam_use_documents = True
            #TODO also set edi_format_ids to ecuadorian edi 
        elif self.type == 'general' and self.l10n_ec_withhold_type == 'out_withhold':
            self.l10n_latam_use_documents = True
            #TODO also remove edi_format_ids
        elif self.type == 'general' and self.l10n_ec_withhold_type == False:
            self.l10n_latam_use_documents = False
            #TODO also remove edi_format_ids
    
    @api.constrains('l10n_ec_withhold_type')
    def check_use_document(self):
        for rec in self:
            if rec.env['account.move'].search([('journal_id', '=', rec.id), ('posted_before', '=', True)], limit=1):
                raise ValidationError(_(
                    'You can not modify the field "Withhold Type?" if there are validated withholds in this journal!'))
    
    l10n_ec_withhold_type = fields.Selection(
        [('out_withhold', 'Sales Withhold'),
         ('in_withhold', 'Purchase Withhold')],
        string='Withhold Type'
        )

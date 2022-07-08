# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    @api.depends('l10n_ec_withhold_type')
    def _compute_edi_format_ids(self):
        # Add the dependency to l10n_ec_withhold_type used by '_is_compatible_with_journal()'
        return super()._compute_edi_format_ids()

    @api.depends('l10n_ec_withhold_type')
    def _compute_compatible_edi_ids(self):
        # Add the dependency to l10n_ec_withhold_type'
        return super()._compute_compatible_edi_ids()
    
    @api.onchange('type', 'l10n_ec_withhold_type')
    def _onchange_withhold_type(self):
        #forcefully clear the field as the field becomes invisible
        if self.type != 'general':
            self.l10n_ec_withhold_type = False
    
    @api.onchange('company_id', 'type','l10n_ec_withhold_type')
    def _onchange_company(self):
        # Sets l10n_latam_use_documents for withholds
        super()._onchange_company()
        self.l10n_latam_use_documents = self.l10n_latam_use_documents or (self.l10n_ec_withhold_type and self.l10n_latam_company_use_documents)
    
    @api.constrains('l10n_ec_withhold_type')
    def _l10n_ec_check_moves_withhold_type(self):
        for rec in self:
            if rec.env['account.move'].search([('journal_id', '=', rec.id), ('posted_before', '=', True)], limit=1):
                raise ValidationError(_(
                    'You can not modify the "Withhold Type" if there are validated withholds in this journal!'))
    
    @api.constrains('l10n_ec_entity', 'l10n_ec_emission','type','l10n_ec_withhold_type','l10n_ec_is_purchase_liquidation')
    def l10n_ec_check_duplicated_entity_emmision(self):
        for journal in self:
            if not journal.country_code == 'EC' or not journal.l10n_ec_entity or not journal.l10n_ec_emission:
                continue
            duplicated_journals = self.search([
                ('id','!=',journal.id), #other journals
                ('company_id','=',journal.company_id.id),
                ('type','=',journal.type),
                ('l10n_ec_withhold_type','=',journal.l10n_ec_withhold_type),
                ('l10n_ec_is_purchase_liquidation','=',journal.l10n_ec_is_purchase_liquidation),
                ('l10n_ec_entity','=',journal.l10n_ec_entity),
                ('l10n_ec_emission','=',journal.l10n_ec_emission),
                ]) 
            if duplicated_journals:
                raise ValidationError(_('Duplicated journal entity and emission detected. You probably encoded twice the same journal:\n%s') % "\n".join(
                    duplicated_journals.mapped(lambda j: "%(l10n_ec_entity)s-%(l10n_ec_emission)s" % {
                        'l10n_ec_entity': j.l10n_ec_entity,
                        'l10n_ec_emission': j.l10n_ec_emission,
                    })
                ))
    
    def _l10n_ec_requiere_emission(self):
        #TODO: Make it a required field to ease the xml file for the form views
        if self.country_code == 'EC' and self.l10n_latam_use_documents:
            if self.type == 'sale':
                return True
            elif self.type == 'purchase' and self.l10n_ec_is_purchase_liquidation:
                return True
            elif self.l10n_ec_withhold_type == 'in_withhold':
                return True
        return False
        
    l10n_ec_withhold_type = fields.Selection(
        [('out_withhold', 'Sales Withhold'),
         ('in_withhold', 'Purchase Withhold')],
        string='Withhold Type'
        )

    l10n_ec_is_purchase_liquidation = fields.Boolean(
        string='Purchase Liquidations',
        store=True, readonly=False, default=False,
        compute='_compute_is_purchase_liquidation',
        help='Whether this journal is for purchase liquidations')

    @api.depends('type')
    def _compute_is_purchase_liquidation(self):
        for record in self:
            if record.env.company.country_id.code != 'EC' or record.type != 'purchase':
                record.l10n_ec_is_purchase_liquidation = False

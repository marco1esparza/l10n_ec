from odoo import api, fields, models, _
from odoo.exceptions import ValidationError



class AccountJournal(models.Model):

    _inherit = "account.journal"

    @api.constrains('l10n_ec_entity', 'l10n_ec_emission')
    def l10n_ec_check_moves_entity_emmision(self):
        for journal in self:
            if self.env['account.move'].search([('journal_id', '=', journal.id), ('posted_before', '=', True)], limit=1):
                raise ValidationError(_(
                    'You can not modify the field "Emission Entity or Emission Point" if there are validated invoices in this journal!'))

    @api.constrains('l10n_ec_withhold_type')
    def _l10n_ec_check_moves_withhold_type(self):
        for rec in self:
            if rec.env['account.move'].search([('journal_id', '=', rec.id), ('posted_before', '=', True)], limit=1):
                raise ValidationError(_(
                    'You can not modify the "Withhold Type" if there are validated withholds in this journal!'))

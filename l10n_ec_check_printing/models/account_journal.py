# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    _BANK_CHECK_FORMAT_EC = [
        ('ckec_page_bolivariano', 'Bolivariano'),
        ('ckec_page_guayaquil', 'Guayaquil'),
        ('ckec_page_internacional', 'Internacional'),
        ('ckec_page_machala', 'Machala'),
        ('ckec_page_pacifico', 'Pacifico'),
        ('ckec_page_pichincha', 'Pichincha'),
        ('ckec_page_produbanco', 'Produbanco'),
        ('ckec_page_ruminaui', 'Rumiñahui'),
    ]
    
    @api.model
    def default_l10n_ec_check_css(self):
        return ''
    
    @api.constrains('check_manual_sequencing')
    def _constrains_check_manual_sequencing(self):
        #In Ecuador never set to true the field check_manual_sequencing
        if self.check_manual_sequencing:
            raise ValidationError(_('Ecuador check numbers are pre-printed, you should uncheck the manual numbering checkbox'))

    l10n_ec_bank_check_format = fields.Selection(
        _BANK_CHECK_FORMAT_EC,
        string='Bank Check Format',
    )
    l10n_ec_check_margin_top = fields.Float(
        string='Check Top Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
        )
    l10n_ec_check_margin_left = fields.Float(
        string='Check Left Margin',
        default=0.25,
        help="Adjust the margins of generated checks to make it fit your printer's settings.",
        )
    l10n_ec_check_css = fields.Text(
        string='Check Format',
        default=default_l10n_ec_check_css,
        help="CSS to customize check layout printing",
        )
    
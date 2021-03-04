# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'
        
    @api.model
    def default_l10n_ec_check_css(self):
        s = (
            ".paguese_a {"
            "    padding-top: 30px;"
            "    left: 0px;"
            "}"
            ".valor_en_numeros {"
            "    top: 20px !important;"
            "    right: 30px;"
            "    position: fixed;"
            "}"
            ".valor_en_letras {"
            "    top: 50px;"
            "    left: 0px;"
            "    /*line-height: 100%;*/"
            "    position: fixed;"
            "}"
            ".ciudad_y_fecha {"
            "    top: 90px;"
            "    left: 10px;"
            "    position: fixed;"
            "}"
            )
        return s
    
    @api.constrains('check_manual_sequencing')
    def _constrains_check_manual_sequencing(self):
        #In Ecuador never set to true the field check_manual_sequencing
        if self.check_manual_sequencing:
            raise ValidationError(_('Ecuador check numbers are pre-printed, you should uncheck the manual numbering checkbox'))
    
    l10n_ec_check_css = fields.Text(
        string='Check Format',
        default=default_l10n_ec_check_css,
        help="CSS to customize check layout printing",
        )
    
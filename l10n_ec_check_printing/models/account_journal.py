# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'
        
    @api.model
    def default_l10n_ec_check_css(self):
        s = (
            "/* INDIQUE LAS CORDENADAS \n"
            "DE LOS ELEMENTOS DEL CHEQUE */\n"
            ".paguese_a {\n"
            "    top: 30px;\n"
            "    left: 0px;\n"
            "}\n"
            ".valor_en_numeros {\n"
            "    top: 20px !important;\n"
            "    right: 30px;\n"
            "}\n"
            ".valor_en_letras_linea1 {\n"
            "    top: 50px;\n"
            "    left: 0px;\n"
            "}\n"
            ".valor_en_letras_linea2 {\n"
            "    top: 50px;\n"
            "    left: 0px;\n"
            "}\n"
            ".ciudad_y_fecha {\n"
            "    top: 90px;\n"
            "    left: 10px;\n"
            "}\n"
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
    
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
            "    top: 1.7cm;\n"
            "    left: 2.3cm;\n"
            "}\n"
            ".paguese_a_blanco {\n"
            "    top: 1.7cm;\n"
            "    left: 2.3cm;\n"
            "    color: #FFF;\n"
            "}\n"
            ".valor_en_numeros {\n"
            "    top: 1.7cm;\n"
            "    right: 1.0cm;\n"
            "}\n"
            ".valor_en_letras_linea1 {\n"
            "    top: 2.6cm;\n"
            "    left: 2.3cm;\n"
            "}\n"
            ".valor_en_letras_linea2 {\n"
            "    top: 3.3cm;\n"
            "    left: 1.0cm;\n"
            "}\n"
            ".ciudad_y_fecha {\n"
            "    top: 3.9cm;\n"
            "    left: 1.0cm;\n"
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
    
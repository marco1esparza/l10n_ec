# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.constrains('check_manual_sequencing')
    def _constrains_check_manual_sequencing(self):
        #In Ecuador never set to true the field check_manual_sequencing
        if self.check_manual_sequencing:
            raise ValidationError(_('Ecuador check numbers are pre-printed, you should uncheck the manual numbering checkbox'))
    
    l10n_ec_check_printing_layout_id = fields.Many2one(
        'ir.actions.report',
        string='Name Report',
        domain="[('model','=','account.payment')]",
        help='Report to use when printing checks.'
        )
    l10n_ec_check_margin_top = fields.Float(
        related='l10n_ec_check_printing_layout_id.paperformat_id.margin_top',
        readonly=False,
        track_visibility='onchange',
        help='Este campo permite modificar el margen superior del reporte, ingrese valores positivos en milimetros.'
        )
    l10n_ec_check_margin_left = fields.Float(
        related='l10n_ec_check_printing_layout_id.paperformat_id.margin_left',
        readonly=False,
        track_visibility='onchange',
        help='Este campo permite modificar el margen izquierdo del reporte, ingrese valores positivos en milimetros.'
        )
    
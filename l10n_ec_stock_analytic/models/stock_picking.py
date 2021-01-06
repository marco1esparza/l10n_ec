# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('analytic_trigger_id')
    def onchange_analytic_trigger_id(self):
        '''
        Copiamos la cuenta analitica de la cabecera a las lineas y luego vaciamos la cabecera
        '''
        if self.analytic_trigger_id:
            analytic_account_id = self.analytic_trigger_id
            for line in self.move_ids_without_package:
                line.analytic_account_id = analytic_account_id
            self.analytic_trigger_id = False

    #Columns
    analytic_trigger_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta analítica'
    )

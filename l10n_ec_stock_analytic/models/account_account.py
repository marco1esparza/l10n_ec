# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'
    
    @api.onchange('code')
    def onchange_code(self):
        '''
        Si la cuenta comienza con 4, 5 o 6 la politica de analitica se cambiara a siempre
        '''
        self.analytic_policy = 'optional'
        if self.code and self.code.startswith(('4', '5', '6')):
            self.analytic_policy = 'always'
            
    _ANALYTIC_POLICY = [
        ('optional', 'Opcional'),
        ('always', 'Siempre'),
        ('posted', 'Movimientos publicados'),
        ('never', 'Nunca')
    ]
    
    #Columns
    analytic_policy = fields.Selection(
        _ANALYTIC_POLICY,
        string='Política para las cuentas analíticas',
        required=True,
        default='optional',
        help='Establecer la política para cuentas analíticas:\n'
        '* Si selecciona "Opcional", el contable tendrá la libertad de poner una cuenta analítica en un apunte contable de esta cuenta.\n'
        '* Si selecciona "Siempre", el contable recibirá un mensaje de error si no hay cuenta analítica.\n'
        '* Si selecciona "Movimientos publicados", el contable recibirá un mensaje error si no se ha definido una cuenta analítica al publicarse el movimiento.\n'
        '* Si selecciona "Nunca", el contable recibirá un mensaje de error si existe una cuenta analítica.'
    )   
    
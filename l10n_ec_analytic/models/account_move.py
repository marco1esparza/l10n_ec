# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        '''
        Invocamos el metodo _post para evaluar las politicas analiticas
        '''
        posted = super()._post(soft=soft)
        self.mapped('line_ids')._check_analytic_required()
        return posted


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _check_analytic_required_msg(self):
        '''
        Este metodo evalua las politicas analiticas
        '''
        for move_line in self:
            prec = move_line.company_currency_id.rounding
            if (float_is_zero(move_line.debit, precision_rounding=prec) and float_is_zero(move_line.credit, precision_rounding=prec)):
                continue
            analytic_policy = move_line.account_id.analytic_policy
            if (analytic_policy == 'always' and not move_line.analytic_account_id):
                return 'La política analítica está establecida a "Siempre" para la cuenta "%s" pero falta la ' \
                       'cuenta analítica en el apunte contable con etiqueta "%s".' % (move_line.account_id.name_get()[0][1], move_line.name)
            elif (analytic_policy == 'never' and move_line.analytic_account_id):
                return 'La política analítica está establecida a "Nunca" para la cuenta "%s" pero el apunte contable ' \
                       'con la etiqueta "%s" tiene la cuenta analítica "%s".' % (move_line.account_id.name_get()[0][1], move_line.name,
                                                                                 move_line.analytic_account_id.name_get()[0][1])
            elif (analytic_policy == 'posted' and not move_line.analytic_account_id and move_line.move_id.state == 'posted'):
                return 'La política analítica está establecida a "Movimientos publicados" para la cuenta "%s" pero falta ' \
                       'la cuenta analítica en el apunte contable con etiqueta "%s".' % (move_line.account_id.name_get()[0][1], move_line.name)

    @api.constrains('analytic_account_id', 'account_id', 'debit', 'credit')
    def _check_analytic_required(self):
        '''
        Restriccion para evaluar politicas analiticas 
        '''
        for line in self:
            message = line._check_analytic_required_msg()
            if message:
                raise ValidationError(message)

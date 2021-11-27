# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        '''
        Invocamos el reconcile para cuando la creacion y conciliacion de asientos vengan del punto de venta
        enviar un contexto a modo bypass para que permita conciliar asientos de distintos partners
        '''
        if self.env.context.get('active_model') == 'pos.config':
            return super(AccountMoveLine, self.with_context(allow_different_partner_entries=True)).reconcile()
        return super(AccountMoveLine, self).reconcile()

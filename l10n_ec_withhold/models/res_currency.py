# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Currency(models.Model):
    _inherit = 'res.currency'

    def is_zero(self, amount):
        '''
        Invocamos el metodo is_zero para hacer que se creen apuntes en cero en la localizacion ecuatoriana,
        se necesitan para la generacion de retenciones en compras pues algunos impuestos tienen %0 y no se
        estaban generando estas lineas en los apuntes contables de la factura
        '''
        if self.env.context.get('generate_zero_entry'):
            return False
        return super(Currency, self).is_zero(amount)

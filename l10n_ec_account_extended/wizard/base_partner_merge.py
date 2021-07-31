# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import ValidationError


class MergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def action_merge(self):
        '''
        Se realiza super a action_merge para no permitir fusionar partners con diferente numero de documento.
        '''
        if self.partner_ids:
            vat = self.partner_ids[0].vat
            for partner in self.partner_ids:
                if vat != partner.vat:
                    raise ValidationError('Para evitar daños en su sistema hemos colocado una restricción, las empresas a fusionar deben tener el mismo número de identificación')

        return super().action_merge()

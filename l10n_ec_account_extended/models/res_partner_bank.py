# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    # @api.model
    # def create(self, vals):
    #     '''
    #     Se realiza super al create para evaluar si se esta creando cuenta bancaria a Partner de Data Demo,
    #     para poder asignar el campo l10n_ec_account_type y no cause error.
    #     '''
    #     partner = self.env['res.partner'].browse(vals.get('partner_id', False))
    #     partners_demo = self.env['res.partner']
    #     partners_demo += self.env.ref('base.partner_demo', raise_if_not_found=False)
    #     partners_demo += self.env.ref('base.res_partner_2', raise_if_not_found=False)
    #     partners_demo += self.env.ref('base.res_partner_3', raise_if_not_found=False)
    #     partners_demo += self.env.ref('base.res_partner_4', raise_if_not_found=False)
    #     if partner and partner in partners_demo:
    #         vals.update({'l10n_ec_account_type': 'savings'})
    #     return super().create(vals)

    l10n_ec_account_type = fields.Selection(
        required=True,
    )

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'
        
#     def update_withhold_agent_type(self):
#         '''
#         Este método se encarga de lanzar el wizard para actualizar el tipo de agente de retención
#         '''
#         res = self.env.ref('ecua_fiscal_positions_core.withhold_agent_wizard_form')
#         return {
#             'name': _(u'Actualizar tipo de agente de retención'),
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': res.id if res else False,
#             'res_model': 'withhold.agent.wizard',
#             'type': 'ir.actions.act_window',
#             'nodestroy': True,
#             'target': 'new'
#         }
#
#    withhold_agent_type_id = fields.Many2one('withhold.agent', string='Withhold Agent Type',
#                                             track_visibility='onchange',
#                                             help='Este campo define el tipo de agente de retención.')

    l10n_ec_fallback_profit_withhold_goods = fields.Many2one(
        'account.tax',
        string='Withhold consumibles',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax')],
        oldname='default_profit_withhold_tax_goods',
        help='When no profit withhold is found in partner or product, if product is a stockable or consumible'
        'the withhold fallbacks to this tax code'
        )
    l10n_ec_fallback_profit_withhold_services = fields.Many2one(
        'account.tax',
        string='Withhold services',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax')],
        oldname='default_profit_withhold_tax_services',
        help='When no profit withhold is found in partner or product, if product is a service or not set'
        'the withhold fallbacks to this tax code'
        )    
    l10n_ec_profit_withhold_tax_credit_card = fields.Many2one(
        'account.tax',
        string='Withhold Credit Card',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax')],
        help='When payment method will be credit card apply this withhold',
        )
    l10n_ec_profit_withhold_tax_debit_card = fields.Many2one(
        'account.tax',
        string='Withhold Debit Card',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax')],
        help='When payment method will be debit card apply this withhold',
        )

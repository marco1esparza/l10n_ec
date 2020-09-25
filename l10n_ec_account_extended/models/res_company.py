# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    @api.model
    def default_get(self, fields):
        #Usefull to automate field filling on pre-existing companies
        #For new companies in multicompany implement AccountChartTemplate._load()
        
        #TODO ANDRES: No esta funcionando los valores por defecto al instalar el modulo
        #en  una bdd existente... talvez moverlo a un init()?
        vals = super(ResCompany, self).default_get(fields)
        l10n_ec_fallback_profit_withhold_goods = self.env['account.tax'].search([
            ('l10n_ec_code_ats','=','312'),
            ('l10n_ec_type','=','withhold_income_tax'),
            ('type_tax_use','=','purchase')
            ], limit = 1)
        l10n_ec_fallback_profit_withhold_services = self.env['account.tax'].search([
            ('l10n_ec_code_ats','=','3440'),
            ('l10n_ec_type','=','withhold_income_tax'),
            ('type_tax_use','=','purchase')
            ], limit = 1)
        l10n_ec_profit_withhold_tax_credit_card = self.env['account.tax'].search([
            ('l10n_ec_code_ats','=','332G'),
            ('l10n_ec_type','=','withhold_income_tax'),
            ('type_tax_use','=','purchase')
            ], limit = 1)
        vals['l10n_ec_fallback_profit_withhold_goods'] = l10n_ec_fallback_profit_withhold_goods
        vals['l10n_ec_fallback_profit_withhold_services'] = l10n_ec_fallback_profit_withhold_services
        vals['l10n_ec_profit_withhold_tax_credit_card'] = l10n_ec_profit_withhold_tax_credit_card
        return vals    
    
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

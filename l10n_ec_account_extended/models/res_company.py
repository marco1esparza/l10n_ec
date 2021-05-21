# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # @api.model
    # def default_get(self, fields):
    #     #Usefull to automate field filling on pre-existing companies
    #     #For new companies in multicompany implement AccountChartTemplate._load()
    #
    #     #TODO ANDRES: No esta funcionando los valores por defecto al instalar el modulo
    #     #en  una bdd existente... talvez moverlo a un init()?
    #     vals = super(ResCompany, self).default_get(fields)
    #     l10n_ec_fallback_profit_withhold_goods = self.env['account.tax'].search([
    #         ('l10n_ec_code_ats','=','312'),
    #         ('l10n_ec_type','=','withhold_income_tax'),
    #         ('type_tax_use','=','purchase')
    #         ], limit = 1)
    #     l10n_ec_fallback_profit_withhold_services = self.env['account.tax'].search([
    #         ('l10n_ec_code_ats','=','3440'),
    #         ('l10n_ec_type','=','withhold_income_tax'),
    #         ('type_tax_use','=','purchase')
    #         ], limit = 1)
    #     l10n_ec_profit_withhold_tax_credit_card = self.env['account.tax'].search([
    #         ('l10n_ec_code_ats','=','332G'),
    #         ('l10n_ec_type','=','withhold_income_tax'),
    #         ('type_tax_use','=','purchase')
    #         ], limit = 1)
    #     vals['l10n_ec_fallback_profit_withhold_goods'] = l10n_ec_fallback_profit_withhold_goods
    #     vals['l10n_ec_fallback_profit_withhold_services'] = l10n_ec_fallback_profit_withhold_services
    #     vals['l10n_ec_profit_withhold_tax_credit_card'] = l10n_ec_profit_withhold_tax_credit_card
    #     return vals
    
    _SOURCE = [
        ('proyectox', 'Proyectox Versión 8'),
        ('trescloud_v7', 'Trescloud Versión 7'),
        ('trescloud_v10', 'Trescloud Versión 10'),
        ('trescloud_v13', 'Trescloud Versión 13'),
        ('trescloud_v14', 'Trescloud Versión 14'),
        ('trescloud_v15', 'Trescloud Versión 15'),
        ('trescloud_v16', 'Trescloud Versión 16'),
        ('other', 'Otros proveedores')
    ]

    _REFUND_VS_INVOICE_CONTROL = [
        ('local_refund', 'Notas de crédito locales'),
        ('without_control', 'Sin control')
    ]

    l10n_ec_issue_withholds = fields.Boolean(
        string='Issue Withhols',
        default=True,
        help='If set Odoo will automatically compute purchase withholds for relevant vendor bills'
        )
    l10n_ec_fallback_profit_withhold_goods = fields.Many2one(
        'account.tax',
        string='Withhold consumibles',
        help='When no profit withhold is found in partner or product, if product is a stockable or consumible'
        'the withhold fallbacks to this tax code'
        )
    l10n_ec_fallback_profit_withhold_services = fields.Many2one(
        'account.tax',
        string='Withhold services',
        help='When no profit withhold is found in partner or product, if product is a service or not set'
        'the withhold fallbacks to this tax code'
        )    
    l10n_ec_profit_withhold_tax_credit_card = fields.Many2one(
        'account.tax',
        string='Withhold Credit Card',
        help='When payment method will be credit card apply this withhold',
        )
    db_source = fields.Selection(
        _SOURCE,
        string='Origen',
        default='trescloud_v14',
        help='Campo informativo del origen de la base de datos del cual se migro la información, permite ejecutar ciertos script de migración.'
    ) #TODO V15, moverlo a la tabla de parametros
    l10n_ec_refund_value_control = fields.Selection(
        _REFUND_VS_INVOICE_CONTROL,
        string='Control del valor de las notas de crédito',
        default='local_refund',
        help='En el caso de que la opción Notas de crédito locales este marcado, validará que la suma de las notas de crédito emitidas no sobrepase el valor de la factura.'
    )

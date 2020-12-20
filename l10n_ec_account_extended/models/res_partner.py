# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    property_l10n_ec_profit_withhold_tax_id = fields.Many2one(
        'account.tax',
        company_dependent=True,
        string='Force profit withhold',
        domain=[('tax_group_id.l10n_ec_type', '=', 'withhold_income_tax'),('type_tax_use', '=', 'purchase')],
        help='If set forces the vat withhold tax on applicable purchases (also a withhold is required on document type). '
        'The profit withhold prevalence order is payment method (credit cards retains 0%), then partner, then product'
        )

    @api.model
    def default_get(self, default_fields):
        """Se hereda el metodo default_get para setear el campo vat, cuando el default_name es numerico"""
        values = super().default_get(default_fields)
        if 'default_name' in self._context:
            default_name = self._context['default_name']
            try:
                vat = int(default_name)
                if vat:
                    values['name'] = False
                    values['vat'] = vat
            except:
                pass
        return values

    @api.onchange('vat', 'company_id')
    def _onchange_vat(self):
        '''
        Onchange para identificar y enviar mensaje de Alerta cuando existe un Partner
        con el mismo Nro de Identificacion.
        '''
        if self.same_vat_partner_id:
            return {
                'warning': {'title': _('Warning'), 'message': _(
                    'A partner with the same Tax ID already exists'), },
            }
    
    def l10n_ec_change_to_microenterprise(self):
        """
        Cambia los impuestos del cliente de retencion de servicios y bienes 
        al 346 impuesto cuando son microempresas
        """
        self.ensure_one()
        tax_id = self.env['account.tax'].search([('l10n_ec_code_ats','=','346')])
        if not tax_id:
            raise UserError(
                "No se encuentra un impuesto con código 346, por favor configure correctamente el impuesto"
                )
        self.property_l10n_ec_profit_withhold_tax_id = tax_id


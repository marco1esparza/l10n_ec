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
    bypass_vat_validation = fields.Boolean(
        string='Bypass vat validation',
        help=u'Algunas cédulas antiguas no cumplen el formato, éste campo'
             u' permite ignorar la validación hecha al campo CI/RUC/Pass.'
        )
    country_id = fields.Many2one(
        default=lambda self: self.env.company_id.country_id.id
        )
    
    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['property_l10n_ec_profit_withhold_tax_id','bypass_vat_validation',]
    
    @api.constrains('vat', 'country_id','l10n_latam_identification_type_id','bypass_vat_validation')
    def check_vat(self):
        #just include bypass_vat_validation field in the constraint
        return super(ResPartner, self).check_vat()
    
    def check_vat_ec(self, vat):
        if self._context.get('bypass_check_vat',False):
            #usefull for migrations from previous versions or integrations
            return True
        if self.bypass_vat_validation:
            return True
        return super(ResPartner, self).check_vat_ec(vat)
    
    def l10n_ec_ecommerce_autoselect_vat_type(self):
        #smart detect vat type, usefull for ecommerce
        if not self.env.user.company_id.country_code == 'EC':
            return True #do nothing
        #TODO evaluar caso de un contacto... no se debe hacer nada
        #TODO BYPASS POR DEFECTO para ecommerce
        new_vat = vals.get('vat')
        new_identification_type = vals.get('l10n_latam_identification_type')
        if new_vat and not new_identification_type:
            #when identification_type not provided attempt to guess the type
            partner_country = vals.get('country_id') or self.country_id
            new_identification_type = it_fid #cédula extranjera
            if partner_country == False or partner_country.country_code == 'EC': 
                if len(new_vat) == 10:
                    new_identification_type = ec_dni
                if len(new_vat) == 13:
                    new_identification_type = ec_ruc
            vals.update({
                'l10n_latam_identification_type': new_identification_type
                })
        return vals
    
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

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def create(self, vals):
        #automate l10n_latam_identification_type_id when creating partners from website
        if self._context.get('website_id',False): #si la creacion/edicion es desde el sitio web
            vals.update({
                'l10n_latam_identification_type_id': self._l10n_ec_ecommerce_autoselect_vat_type(vals),
                 })
        return super().create(vals)
     
    def write(self, vals):
        #automate l10n_latam_identification_type_id when editing partners from website
        if self._context.get('website_id',False): #si la creacion/edicion es desde el sitio web
            vals.update({
                'l10n_latam_identification_type_id': self._l10n_ec_ecommerce_autoselect_vat_type(vals),
                })
        return super().write(vals)
     
    def _l10n_ec_ecommerce_autoselect_vat_type(self, vals):
        #smart detect vat type, usefull for ecommerce
        if not self.env.company.country_code == 'EC':
            return True #when company is not ecuadorian then do nothing, 
        new_vat = vals.get('vat',self.vat) 
        #when identification_type not provided attempt to guess the type
        if new_vat:
            country_code = self.country_id.code or 'EC'
            if len(new_vat) == 10 and country_code == 'EC':
                it_dni = self.env.ref('l10n_ec.ec_dni') #Cedula 
                new_identification_type = it_dni
            elif len(new_vat) == 13 and country_code == 'EC':
                it_ruc = self.env.ref('l10n_ec.ec_ruc') #RUC
                new_identification_type = it_ruc
            else:
                it_fid = self.env.ref('l10n_latam_base.it_fid') #cedula exterior
                new_identification_type = it_fid #cédula extranjera
            return new_identification_type.id
    

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    @api.onchange('company_type')
    def onchange_company_type(self):
        '''
        En caso que sea una persona natural limpiamos el campo nombre del comercial
        '''
        res = super(ResPartner, self).onchange_company_type()
        if self.company_type == 'person':
            self.l10n_commercial_name = ''
        return res
    
    def get_invoice_ident_type(self):
        '''
        '''
        type_vat = self.l10n_latam_identification_type_id.name
        if type_vat == 'RUC':
            return '04'
        elif type_vat == 'CEDULA':
            return '05'
        elif type_vat == 'PERS. NATURAL EXTRANJERA':
            return '06'
        elif type_vat == 'CONSUMIDOR FINAL': 
            return '07'
        elif type_vat == 'PERS. JURIDICA EXTRANJERA': 
            return '08'
        return False

    def get_invoice_partner_data(self):
        '''
        '''
        if self.commercial_partner_id:
            self = self.commercial_partner_id
        return {
            'invoice_name': self.name,
            'invoice_vat': self.vat,
            'invoice_address': ' '.join([value for value in [self.street, self.street2] if value]),
            'invoice_phone': self.phone or self.mobile,
            'invoice_email': self.email,
        }

    #Columns
    l10n_commercial_name = fields.Char(
        string='Commercial Name',
        help=''
        )

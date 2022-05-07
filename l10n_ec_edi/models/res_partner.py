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
            self.l10n_ec_commercial_name = ''
        return res
    
    def get_invoice_ident_type(self):
        '''
        '''
        code = False
        if self.vat == '9999999999999': #CONSUMIDOR FINAL
            code = '07'
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_dni').id: #CEDULA
            code = '05'
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_ruc').id: #RUC
            code = '04'
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_latam_base.it_pass').id: #PERS. NATURAL EXTRANJERA
            code = '06' 
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_latam_base.it_fid').id: #PERS. JURIDICA EXTRANJERA
            code = '08'
        return code
    
    def _get_complete_name(self):
        for partner in self:
            if partner.commercial_partner_id:
                partner = partner.commercial_partner_id
            return partner.commercial_company_name or partner.name

    def get_invoice_partner_data(self):
        '''
        '''
        if self.commercial_partner_id:
            self = self.commercial_partner_id
        return {
            'invoice_name': self._get_complete_name(),
            'invoice_vat': self.vat,
            'invoice_address': ' '.join([value for value in [self.street, self.street2] if value]),
            'invoice_phone': self.phone or self.mobile,
            'invoice_email': self.email,
        }
        
    def _get_complete_address(self):
        self.ensure_one()
        partner_id = self
        address = ""
        if partner_id.street:
            address += partner_id.street + ", "
        if partner_id.street2:
            address += partner_id.street2 + ", "
        if partner_id.city:
            address += partner_id.city + ", "
        if partner_id.state_id:
            address += partner_id.state_id.name + ", "
        if partner_id.zip:
            address += "(" + partner_id.zip + ") "
        if partner_id.country_id:
            address += partner_id.country_id.name
        return address
        
    def _compute_l10n_ec_code(self):
        #Este método asigna un código a cada tipo de identificación
        for partner in self:
            code = 'O'
            if partner.vat == '9999999999999': #CONSUMIDOR FINAL
                code = 'F'
            elif partner.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_dni').id: #CEDULA
                code = 'C'
            elif partner.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_ruc').id: #RUC
                code = 'R'
            elif partner.l10n_latam_identification_type_id.id == self.env.ref('l10n_latam_base.it_pass').id: #PERS. NATURAL EXTRANJERA
                code = 'P' 
            elif partner.l10n_latam_identification_type_id.id == self.env.ref('l10n_latam_base.it_fid').id: #PERS. JURIDICA EXTRANJERA
                code = 'P'
            partner.l10n_ec_code = code
    
    #Columns
    l10n_ec_commercial_name = fields.Char(
        string='Commercial Name',
        help=''
        )
    l10n_ec_code = fields.Char(
        string='Ecuadorian Identification Type',
        compute='_compute_l10n_ec_code', 
        tracking=True,
        store=False,  
        help='Indicates the type of identification of the partner, is used for the ATS'
        )

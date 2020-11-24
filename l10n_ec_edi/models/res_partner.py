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
        
    def _l10n_ec_get_code(self):
        '''
        Este método asigna un código a cada tipo de identificación
        '''
        for partner in self:
            partner.l10n_ec_code = self._l10n_ec_get_code_by_vat()

    @api.model
    def _l10n_ec_get_code_by_vat(self):
        """
        Calcula el codigo del partner basado en el vat y el type_vat. Permite
        hacer el calculo para un vat y type_vat que no esten ligados a un
        partner
        """
        # Variable type_vat:
        # Existe un problema con la tilde en esta version, en una parte
        # se entrega un str y en otra se entrega un unicode, para solucionarlo
        # se quita la tilde en todo lugar que se ocupe
        code = 'O'
        if self.vat == '9999999999999': #CONSUMIDOR FINAL
            code = 'F'
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_dni').id: #CEDULA
            code = 'C'
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_ec.ec_ruc').id: #RUC
            code = 'R'
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_latam_base.it_pass').id: #PERS. NATURAL EXTRANJERA
            code = 'P' 
        elif self.l10n_latam_identification_type_id.id == self.env.ref('l10n_latam_base.it_fid').id: #PERS. JURIDICA EXTRANJERA
            code = 'P'
        return code

    #Columns
    l10n_ec_commercial_name = fields.Char(
        string='Commercial Name',
        help=''
        )
    l10n_ec_code = fields.Char(
        string='Ecuadorian Identification Type',
        compute='_l10n_ec_get_code', 
        method=True,
        store=False,  
        help='Indicates the type of identification of the partner, is used for the ATS'
        )

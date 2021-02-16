# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class L10nEcWaybillCarrier(models.Model):
    _name = 'l10n_ec.waybill.carrier'
    _inherit = ['mail.thread']
    _description = "Waybill Carrier"

    def get_ident_type(self):
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
    
    def _get_available_l10n_latam_identification_types(self):
        #computes the possible identification types for carriers (cedula, ruc y pasaporte)
        cedula = self.env.ref('l10n_ec.ec_dni')
        ruc =  self.env.ref('l10n_ec.ec_ruc')
        pasaporte = self.env.ref('l10n_latam_base.it_pass')
        return  [cedula.id,ruc.id,pasaporte.id]
    
    @api.depends()
    def _compute_allowed_identification_type_ids(self):
        cedula = self.env.ref('l10n_ec.ec_dni')
        ruc =  self.env.ref('l10n_ec.ec_ruc')
        pasaporte = self.env.ref('l10n_latam_base.it_pass')
        for carrier in self:
            carrier.allowed_identification_type_ids = cedula + ruc + pasaporte
    
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True
        )
    l10n_latam_identification_type_id = fields.Many2one(
        'l10n_latam.identification.type',
        string="Identification Type",
        default=lambda self: self.env.ref('l10n_ec.ec_dni',raise_if_not_found=False),
        tracking=True,
        required=True,
        domain=[('id','in',_get_available_l10n_latam_identification_types)],
        help="The type of identification"
        )    
    allowed_identification_type_ids = fields.Many2many(
        'l10n_latam.identification.type',
        compute='_compute_allowed_identification_type_ids'
        )
    vat = fields.Char(
        string='Identification Number',
        help="Identification Number for selected type",
        required=True,
        tracking=True,
        )
    active = fields.Boolean(
        default=True,
        help="Set active to false to hide the SRI Printer Point without removing it.",
        tracking=True
        )
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)


    @api.constrains('l10n_latam_identification_type_id','vat')
    def _check_vat(self):
        cedula = self.env.ref('l10n_ec.ec_dni')
        ruc =  self.env.ref('l10n_ec.ec_ruc')
        pasaporte = self.env.ref('l10n_latam_base.it_pass')
        if self.l10n_latam_identification_type_id == cedula:
            if len(self.vat) != 10:
                raise ValidationError('El numero de cedula debe ser de 10 digitos')
        elif self.l10n_latam_identification_type_id == ruc:
            if len(self.vat) != 13:
                raise ValidationError('El numero de RUC debe ser de 13 digitos')
        if self.l10n_latam_identification_type_id in (cedula,ruc):
            #temporal fix as stdnum.ec is allowing old format with a dash in between the number                    
            if not self.vat.isnumeric():
                raise ValidationError(_('Ecuadorian VAT number must contain only numeric characters'))


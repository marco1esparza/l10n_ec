# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

#pache temporal hasta que odoo fusione https://github.com/TRESCLOUD/odoo/pull/529/files
_ref_vat = {
    'al': 'ALJ91402501L',
    'ar': 'AR200-5536168-2 or 20055361682',
    'at': 'ATU12345675',
    'au': '83 914 571 673',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'ch': 'CHE-123.456.788 TVA or CHE-123.456.788 MWST or CHE-123.456.788 IVA',  # Swiss by Yannick Vaucher @ Camptocamp
    'cl': 'CL76086428-5',
    'co': 'CO213123432-1 or CO213.123.432-1',
    'cy': 'CY10259033P',
    'cz': 'CZ12345679',
    'de': 'DE123456788',
    'dk': 'DK12345674',
    'do': 'DO1-01-85004-3 or 101850043',
    'ec': '1792366836001 or 0103647616 or 9999999999999', #Ecuador by Andres Calle @ Trescloud
    'ee': 'EE123456780',
    'el': 'EL12345670',
    'es': 'ESA12345674',
    'fi': 'FI12345671',
    'fr': 'FR23334175221',
    'gb': 'GB123456782',
    'gr': 'GR12345670',
    'hu': 'HU12345676',
    'hr': 'HR01234567896',  # Croatia, contributed by Milan Tribuson
    'ie': 'IE1234567FA',
    'in': "12AAAAA1234AAZA",
    'is': 'IS062199',
    'it': 'IT12345670017',
    'lt': 'LT123456715',
    'lu': 'LU12345613',
    'lv': 'LV41234567891',
    'mc': 'FR53000004605',
    'mt': 'MT12345634',
    'mx': 'MXGODE561231GR8 or GODE561231GR8',
    'nl': 'NL123456782B90',
    'no': 'NO123456785',
    'pe': '10XXXXXXXXY or 20XXXXXXXXY or 15XXXXXXXXY or 16XXXXXXXXY or 17XXXXXXXXY',
    'pl': 'PL1234567883',
    'pt': 'PT123456789',
    'ro': 'RO1234567897',
    'rs': 'RS101134702',
    'ru': 'RU123456789047',
    'se': 'SE123456789701',
    'si': 'SI12345679',
    'sk': 'SK2022749619',
    'sm': 'SM24165',
    'tr': 'TR1234567890 (VERGINO) or TR17291716060 (TCKIMLIKNO)'  # Levent Karakas @ Eska Yazilim A.S.
}

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    bypass_vat_validation = fields.Boolean(
        string='Omitir validacion RUC/Ced',
        help=u'Algunas cédulas antiguas no cumplen el formato del registro civil, éste campo'
             u' permite ignorar la validación Ecuatoriana para el campo CI/RUC/Pass.'
        )
    country_id = fields.Many2one(
        default=lambda self: self.env.company.country_id.id
        )
    #adds tracking to know when user changes configuration
    vat = fields.Char(tracking=True)
    l10n_latam_identification_type_id = fields.Many2one(tracking=True)
    
    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
            ['property_l10n_ec_profit_withhold_tax_id','bypass_vat_validation',]
    
    @api.constrains('vat', 'country_id','l10n_latam_identification_type_id','bypass_vat_validation')
    def check_vat(self):
        # just include bypass_vat_validation field in the constraint
        # bugfix #17584: Validate only main partner, exclude contacts, to avoid expected singleton error, seems like a bug in v14
        main_partner = self.mapped('commercial_partner_id')
        return super(ResPartner, main_partner).check_vat()
    
    def check_vat_ec(self, vat):
        if self._context.get('bypass_check_vat',False):
            #usefull for migrations from previous versions or integrations
            return True
        if self.bypass_vat_validation:
            return True
        return super(ResPartner, self).check_vat_ec(vat)
    
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
        al impuesto 343
        """
        self.ensure_one()
        tax_id = self.env['account.tax'].search([('l10n_ec_code_ats','=','343')])
        if not tax_id:
            raise UserError(
                "No se encuentra un impuesto con código 343, por favor configure correctamente el impuesto"
                )
        self.property_l10n_ec_profit_withhold_tax_id = tax_id

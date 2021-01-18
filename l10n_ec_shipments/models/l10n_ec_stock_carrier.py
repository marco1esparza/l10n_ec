# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class L10nEcStockCarrier(models.Model):
    _name = 'l10n_ec.stock.carrier'
    _inherit = ['mail.thread']
    _description = "Stock Carrier"

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

    name = fields.Char(string='Name', required=True)
    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
                                                        string="Identification Type",
                                                        default=lambda self: self.env.ref('l10n_latam_base.it_vat',
                                                                                          raise_if_not_found=False),
                                                        help="The type of identification", required=True)
    vat = fields.Char(string='Identification Number', help="Identification Number for selected type", required=True)
    license_plate = fields.Char(string='Vehicle Plate', size=15, required=True)

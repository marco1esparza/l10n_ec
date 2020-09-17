# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'
    
    l10n_ec_apply_withhold = fields.Boolean(
        compute='_compute_l10n_ec_apply_withhold')
    
    @api.depends('code','l10n_ec_type',)
    def _compute_l10n_ec_apply_withhold(self):
        #Indicates if the document type requires a withhold or not
        for document in self:
            result = False
            if document.l10n_ec_type == 'in_invoice':
                if document.code in ['01', # factura compra
                                     '03', # liquidacion compra
                                     '08', # Entradas a espectaculos
                                     '09', # Tiquetes
                                     '11', # Pasajes
                                     '12', # Inst FInancieras
                                     '20', # Estado
                                     '21', # Carta porte aereo
                                     ]:
                    result = True
            document.l10n_ec_apply_withhold = result

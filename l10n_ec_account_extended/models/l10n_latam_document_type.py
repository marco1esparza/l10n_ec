# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields
from odoo.osv import expression


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        '''
        Se modifica el name_search para que se buscar el Codigo del document type
        '''
        args = args or []
        if self.env.company.country_id != self.env.ref('base.ec'):
            return super().name_search(name, args, operator, limit)
        else:
            domain = [('active', 'ilike', True), '|', ('code', 'ilike', name), ('name', operator, name)]
        doc_types = self.search(expression.AND([domain, args]), limit=limit)
        return doc_types.name_get()

    #TODO Andres preguntar si esto es necesario en V14    
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

    l10n_ec_apply_withhold = fields.Boolean(compute='_compute_l10n_ec_apply_withhold')

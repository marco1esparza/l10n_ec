# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
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


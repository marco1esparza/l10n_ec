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

    def l10n_ec_map_document_type_code_to_electronic_code(self):
        # Retorna el codigo de documento electronico para la clave de acceso
        # TODO V15, usar este metodo en _l10n_ec_set_access_key()
        # Inventario:
        if self == self.env.ref('l10n_ec.ec_07'): #guia de remisión
            return '06' #el mismo codigo del documento
        # Ventas
        if self == self.env.ref('l10n_ec.ec_04'): #factura de venta
            return '01'
        if self == self.env.ref('l10n_ec.ec_59'): #factura de venta por reembolso
            return '01'
        if self == self.env.ref('l10n_ec.ec_54'): #notade debito en ventas
            return '05' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_10'): #nota de credito en ventas
            return '04' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_03'): #retención en venta
            return '07' #el mismo codigo del documento
        # Compras
        if self == self.env.ref('l10n_ec.ec_06'): #factura de compra
            return '01' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_58'): #factura de compra por reembolso
            return '01' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_08'): #liquidacion de compra
            return '03' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_57'): #liquidacion de compra por reembolso
            return '03'
        if self == self.env.ref('l10n_ec.ec_09'): #nota de credito en compras
            return '04' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_47'): #nota de credito en compras por reembolso
            return '04' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_53'): #nota de debito en compras
            return '05' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_48'): #nota de debito en compras por reembolso
            return '05' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_11'): #retencion en compras
            return '07' #el mismo codigo del documento

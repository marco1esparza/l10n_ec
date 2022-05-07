# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'
    
    def l10n_ec_map_document_type_code_to_electronic_code(self):
        # Retorna el codigo de documento electronico para la clave de acceso
        # TODO V15, usar este metodo en _l10n_ec_set_access_key()
        # Inventario:
        if self == self.env.ref('l10n_ec.ec_dt_06'): #guia de remisión
            return '06' #el mismo codigo del documento
        # Ventas
        if self == self.env.ref('l10n_ec.ec_dt_18'): #factura de venta
            return '01'
            return '01'
        if self == self.env.ref('l10n_ec.ec_dt_sale_05'): #nota de debito en ventas
            return '05' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_sale_04'): #nota de credito en ventas
            return '04' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_sale_07'): #retención en venta
            return '07' #el mismo codigo del documento
        # Compras
        if self == self.env.ref('l10n_ec.ec_dt_01'): #factura de compra
            return '01' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_purchase_41'): #factura de compra por reembolso
            return '01' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_03'): #liquidacion de compra
            return '03' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_liqco_41'): #liquidacion de compra por reembolso
            return '03'
        if self == self.env.ref('l10n_ec.ec_dt_purchase_04'): #nota de credito en compras
            return '04' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_47'): #nota de credito en compras por reembolso
            return '04' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_purchase_05'): #nota de debito en compras
            return '05' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_48'): #nota de debito en compras por reembolso
            return '05' #el mismo codigo del documento
        if self == self.env.ref('l10n_ec.ec_dt_purchase_07'): #retencion en compras
            return '07' #el mismo codigo del documento

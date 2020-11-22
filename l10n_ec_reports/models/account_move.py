# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit='account.move'
     
    @api.onchange('partner_id', 'l10n_latam_document_type_id', 'l10n_ec_available_sri_tax_support_ids')
    def _onchange_l10n_ec_available_sri_tax_support_ids(self):
        '''
        '''
        if self.l10n_latam_country_code == 'EC':
            #Solamente las compras tienen sustento tributario...
            if self.type in ['in_invoice', 'in_refund']:
                l10n_ec_sri_tax_support_id = False
                if self.l10n_latam_document_type_id:
                    if self.l10n_ec_available_sri_tax_support_ids:
                        #Usamos _origin para obtener el id del registro y evitar algo como lo sig: NewId: <NewId origin=2>
                        l10n_ec_sri_tax_support_id = self.l10n_ec_available_sri_tax_support_ids[0]._origin.id
                self.l10n_ec_sri_tax_support_id = l10n_ec_sri_tax_support_id

    @api.depends('l10n_latam_document_type_id')
    def _compute_l10n_ec_available_sri_tax_supports(self):
        '''
        '''
        for invoice in self:
            l10n_ec_available_sri_tax_support_ids = False
            if invoice.l10n_latam_document_type_id:
                l10n_ec_available_sri_tax_support_ids = invoice.l10n_latam_document_type_id.l10n_ec_sri_tax_support_ids
            invoice.l10n_ec_available_sri_tax_support_ids = l10n_ec_available_sri_tax_support_ids

    def _compute_l10n_ec_transaction_type(self):
        ''' 
        Este campo agrega un código de tipo de transación en base al partner y el tipo de operacion(compras, ventas)
        '''
        partner_obj = self.env['res.partner']
        for invoice in self:
            #TODO jm: evaluar con andres la logica del sig metodo "_get_type_vat_by_vat", en caso que se requiere implementarlo
            #y descomentar las siguientes 5 lineas de codigo, temporalmente voy a poner a la variable code_error en vacia para
            #que que no explote.
            code_error = ''
#             type_vat, code_error = partner_obj._get_type_vat_by_vat(
#                 invoice.invoice_country_id,
#                 invoice.invoice_vat,
#                 invoice.fiscal_position_id.transaction_type,
#             )
            invoice_type = invoice.type
            code = invoice.partner_id._l10n_ec_get_code_by_vat()
            # Determinamos el pais, para segun el código del país
            # hacer uno o otro procedimiento
            if not invoice.l10n_latam_country_code:
                invoice.l10n_ec_transaction_type = 'Debe definir el país de la factura.'
                invoice.l10n_ec_transaction_type += ' Documento ' + str(invoice.l10n_latam_document_number or '')
                invoice.l10n_ec_transaction_type += ' Empresa ' + (invoice.partner_id.name or '')
            elif invoice_type in ['in_invoice', 'in_refund']: #COMPRAS
                # RUC
                if code == 'R':
                    invoice.l10n_ec_transaction_type = '01'
                # CEDULA
                elif code == 'C':
                    invoice.l10n_ec_transaction_type = '02'
                # PERS. JURÍDICA EXTRANJERA, PERS. NATURAL EXTRANJERA
                elif code == 'P':
                    invoice.l10n_ec_transaction_type = '03'
                # Este caso es especial, es un proveedor con tipo de compania detectada 
                # como nacional por la posicion fiscal pero el pais es extranjero
                elif code_error == 'ERROR_POSICION_FISCAL_Y_PAIS':
                    invoice.l10n_ec_transaction_type = 'Debe revisar la posicion fiscal del proveedor y el pais seleccionado para que guarden coherencia entre si.'                    
                    invoice.l10n_ec_transaction_type += ' Documento de Compra ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Proveedor ' + (invoice.partner_id.name or '')
                else:
                    #cubre el caso de code == 'O': #OTROS
                    #cubre otros casos no determinados
                    #no se usa tildes por problema de unicode al ats
                    invoice.l10n_ec_transaction_type = 'Proveedor no tiene asignado una identificacion (CEDULA/RUC/PASAPORTE) correcta.'
                    invoice.l10n_ec_transaction_type += ' Documento de Compra ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Proveedor ' + (invoice.partner_id.name or '')
            elif invoice_type in ['out_invoice', 'out_refund']: #VENTAS
                # RUC
                if code == 'R':
                    invoice.l10n_ec_transaction_type = '04'
                # CEDULA
                elif code == 'C':
                    invoice.l10n_ec_transaction_type = '05'
                # PERS. JURÍDICA EXTRANJERA, PERS. NATURAL EXTRANJERA
                elif code == 'P':
                    invoice.l10n_ec_transaction_type = '06'
                # CONSUMIDOR FINAL
                elif code == 'F':
                    invoice.l10n_ec_transaction_type = '07'
                # Este caso es especial, es un cliente con tipo de compania detectada 
                # como nacional por la posicion fiscal pero el pais es extranjero
                elif code_error == 'ERROR_POSICION_FISCAL_Y_PAIS':
                    invoice.l10n_ec_transaction_type = 'Debe revisar la posicion fiscal del cliente y el pais seleccionado para que guarden coherencia entre si.'
                    invoice.l10n_ec_transaction_type += ' Documento de Venta ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Cliente ' + (invoice.partner_id.name or '')
                else:
                    #cubre el caso de code == 'O': #OTROS
                    #cubre otros casos no determinados
                    #no se usa tildes por problema de unicode al ats
                    invoice.l10n_ec_transaction_type = 'Cliente no tiene asignado una identificacion (CEDULA/RUC/PASAPORTE) correcta.'
                    invoice.l10n_ec_transaction_type += ' Documento de Venta ' + str(invoice.l10n_latam_document_number or '')
                    invoice.l10n_ec_transaction_type += ' Cliente ' + (invoice.partner_id.name or '')
            else:
                invoice.l10n_ec_transaction_type = 'La factura no tiene tipo... contacte a soporte tecnico.'
                invoice.l10n_ec_transaction_type += ' Documento ' + str(invoice.l10n_latam_document_number or '')
                invoice.l10n_ec_transaction_type += ' Empresa ' + (invoice.partner_id.name or '')

    def _compute_l10n_ec_invoice_country(self):
        '''
        '''
        for invoice in self:
            l10n_ec_invoice_country_id = invoice.env.ref('base.ec').id #Ecuador por defecto
            if invoice.partner_id.country_id:
                l10n_ec_invoice_country_id = invoice.partner_id.country_id.id
            invoice.l10n_ec_invoice_country_id = l10n_ec_invoice_country_id

    l10n_ec_available_sri_tax_support_ids = fields.Many2many(
        'l10n_ec.sri.tax.support', 
        compute='_compute_l10n_ec_available_sri_tax_supports'
        )
    l10n_ec_sri_tax_support_id = fields.Many2one(
        'l10n_ec.sri.tax.support',
        string='Tax Support',
        help='Indicates the tax support for this document'
        )
    l10n_ec_transaction_type = fields.Char(
        compute='_compute_l10n_ec_transaction_type',
        string='Transaction Type',
        method=True,
        store=False,
        help='Indicate the transaction type that performer the partner. Supplier Invoice '
             '[01-RUC,02-CEDULA,03-PASAPORTE],Customer Invoice [04-RUC,05-CEDULA,06-PASAPORTE, '
             '07-CONSUMIDOR FINAL, 0-OTROS].'
        )
    l10n_ec_invoice_country_id = fields.Many2one(
        'res.country',
        compute='_compute_l10n_ec_invoice_country',
        string='Invoice Country',
        method=True,
        store=False,
        help=''
        )

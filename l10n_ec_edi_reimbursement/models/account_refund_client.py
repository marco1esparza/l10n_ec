# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import time


class AccountRefundClient(models.Model):
    '''
    This class allow to store the purchase invoice related with refunds in client scenario
    '''
    _name = 'account.refund.client'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''
        When the partner changed need recalculate the transaction type.
        '''
        res = {'value': {},'warning': {},'domain': {}}
        if self.move_id.country_code == 'EC':
            res['value']['l10n_latam_document_type_id'] = False
            res['value']['authorization'] = False
            if not self.partner_id:
                return res
            commercial_partner = self.partner_id.commercial_partner_id
            refund_type = self.move_id.move_type
            code = commercial_partner._l10n_ec_get_code_by_vat()
            if refund_type in ['in_invoice', 'in_refund']: #COMPRAS
                if code == 'R': #RUC
                    res['value']['transaction_type'] = '01'
                elif code == 'C': #CEDULA
                    res['value']['transaction_type'] = '02'
                elif code == 'P': #PERS. JURÍDICA EXTRANJERA, PERS. NATURAL EXTRANJERA
                    res['value']['transaction_type'] = '03' 
                else: 
                    #cubre el caso de code == 'O': #OTROS
                    #cubre otros casos no determinados
                    res['value']['transaction_type'] = 'Proveedor en reembolso no tiene asignado una identificacion correcta (CEDULA/RUC/PASAPORTE).'
                    res['value']['transaction_type'] += ' Documento ' + str(self.move_id.l10n_latam_document_number or '')
                    res['value']['transaction_type'] += ' Proveedor ' + commercial_partner.name
            else: #VENTAS
                res['value']['transaction_type'] = 'No Aplica Para Ventas'
            if self.move_id.move_type == 'out_invoice':
                #rellenamos los datos de la factura de compra
                vals = self._fill_purchase_invoice()
                res['value'].update(vals)
        return res

    @api.onchange('l10n_latam_document_type_id')
    def onchange_l10n_latam_document_type_id(self):
        '''
        When the partner changed need recalculate the transaction type.
        '''
        res = {'value': {},'warning': {},'domain': {}}
        if self.move_id.country_code == 'EC':
            if self.move_id.move_type == 'out_invoice':
                #rellenamos los datos de la factura de compra
                vals = self._fill_purchase_invoice()
                res['value'].update(vals)
        return res

    @api.onchange('number')
    def onchange_number(self):
        '''
        Use the format internal number in case the user change this number
        '''
        res = {'value': {}, 'warning': {}, 'domain': {}}
        if self.move_id.country_code == 'EC':
            if self.number:
                number_split = self.number.split('-')
                if len(number_split) == 3 and number_split[2] != '':
                    if len(number_split[2]) < 17:
                        #Require auto complete
                        pos = 0
                        fill = 9 - len(number_split[2])
                        for car in number_split[2]:
                            if car != '0':
                                break
                            pos = pos + 1
                        number_split[2] = number_split[2][:pos] + '0' * fill + number_split[2][pos:]
                        self.number = number_split[0] + '-' + number_split[1] + '-' + number_split[2]
            if self.move_id.move_type == 'out_invoice':
                #rellenamos los datos de la factura de compra
                vals = self._fill_purchase_invoice()
                res['value'].update(vals)
        return res

    @api.onchange('authorization')
    def onchange_authorization(self):
        '''
        When the authorization change, show the number for the document
        '''
        #caso facturas de venta por reembolso
        if self.move_id.move_type == 'out_invoice':
            #para ventas por reembolso de gastos, en primera instancia no se implementa, pues
            #en el formulario se ha colocado primero el nro de factura y despues el nro de 
            #autorizacion, y se llena de izq a derecha
            return
        #caso facturas de compra por reembolso, este caso requiere refactoring a la nueva API
        res = {'value': {},'warning': {},'domain': {}}
        if not self.authorization:
            res['value']['number'] = '001-001-'
        return res

    @api.onchange('base_tax_free', 'no_vat_amount', 'base_vat_0', 'base_vat_no0', 'vat_amount_no0', 'ice_amount')
    def onchange_total(self):
        '''
        Calculate the total and the vat value depending the field using
        calc_vat = True -> show the value of vat using the base
        '''
        if self._context.get('calc_vat'):
            self.vat_amount_no0 = self.base_vat_no0 * 12.0 / 100.0
            if self.creation_date >= datetime.strptime('2016-06-01', '%Y-%m-%d').date() and self.creation_date <= datetime.strptime('2017-05-31', '%Y-%m-%d').date():
                self.vat_amount_no0 = self.base_vat_no0 * 14.0 / 100.0
        self.total = self.base_tax_free + self.no_vat_amount + self.base_vat_0 + self.base_vat_no0 + self.vat_amount_no0 + self.ice_amount

    def _fill_purchase_invoice(self):
        '''
        En las facturas de venta, completa los datos de la factura de compra si esta existe
        De esta forma se automatiza cuando el cliente digita toda la info en el sistema, y
        se permite el proceso totalmente manual si el cliente no desea registrar las 
        facturas de compras en el sistema.
         
        Un documento se identifica univocamente por:
        - partner_id
        - l10n_latam_document_type_id
        - number
        -type
        '''
        vals = {
            'authorization': '',
            'creation_date': fields.Date.context_today(self),
            'base_tax_free': 0.0,
            'no_vat_amount': 0.0,
            'base_vat_0': 0.0,
            'base_vat_no0': 0.0,
            'vat_amount_no0': 0.0,
            'ice_amount': 0.0,
            'total': 0.0
            }
        has_number = False
        if self.number and len(self.number) == 17:
            has_number = True
        if self.partner_id and self.l10n_latam_document_type_id and has_number:
            #Se usa sql pues un search falla en el campo l10n_latam_document_number
            self.env.cr.execute('''
                select 
                    id 
                from account_move
                where commercial_partner_id=%s and l10n_latam_document_type_id=%s and name ilike %s and type='in_invoice'
            ''', (self.partner_id.commercial_partner_id.id, self.l10n_latam_document_type_id.id, '%' + self.number + '%'))
            purchases = self.env.cr.fetchall()
            if purchases:
                if len(purchases) == 1:
                    #TODO: en el futuro, debido a que el sustento tributario esta en la cabecera
                    #se podria permitir distintas lineas para el sustento
                    purchase = self.env['account.move'].browse(purchases[0])
                    vals = {
                        'authorization': purchase.l10n_ec_authorization,
                        'creation_date': purchase.invoice_date,
                        'base_tax_free': purchase.l10n_ec_base_tax_free,
                        'no_vat_amount': purchase.l10n_ec_base_not_subject_to_vat,
                        'base_vat_0': purchase.l10n_ec_base_cero_iva,
                        'base_vat_no0': purchase.l10n_ec_base_doce_iva,
                        'vat_amount_no0': purchase.l10n_ec_vat_doce_subtotal,
                        'ice_amount': 0.0,
                        'total': purchase.amount_total
                        }
        return vals

    def _get_transaction_type(self):
        '''
        Este campo agrega un código de tipo de transación en base al partner y el tipo de operacion(compras)
        que sera usado en la generacion del ATS
        '''
        for refund in self:
            commercial_partner = refund.partner_id.commercial_partner_id
            refund_type = refund.move_id.move_type
            code = commercial_partner._l10n_ec_get_code_by_vat()
            if refund_type in ['in_invoice', 'in_refund']: #COMPRAS
                if code == 'R': #RUC
                    refund.transaction_type = '01'
                elif code == 'C': #CEDULA
                    refund.transaction_type = '02'
                elif code == 'P': #PERS. JURÍDICA EXTRANJERA, PERS. NATURAL EXTRANJERA
                    refund.transaction_type = '03' 
                else: 
                    #cubre el caso de code == 'O': #OTROS
                    #cubre otros casos no determinados
                    refund.transaction_type = 'Proveedor en reembolso no tiene asignado una identificacion correcta (CEDULA/RUC/PASAPORTE).'
                    refund.transaction_type += ' Documento ' + str(refund.move_id.l10n_latam_document_number or '')
                    refund.transaction_type += ' Proveedor ' + commercial_partner.name
            else: #caso de ventas
                refund.transaction_type = 'No Aplica Para Ventas'

    # Columns
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='Select the partner asociated to the invoices'
        )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Tipo de Documento', 
        help='Select the type of document for this line'
        ) #TODO ANDRES: Poner un domain, solo docs de compra?
    number = fields.Char(
        string='Number of document',
        size=17,
        default='001-001-',
        )
    authorization = fields.Char(
        string='Autorización',
        help='Authorization number for issuing the tributary document, assigned by SRI, can be 10 numbers long, 41, or 49.'
        )
    creation_date = fields.Date(
        string='Fecha',
        help='Set the date of document generation'
        )
    transaction_type = fields.Char(
        compute='_get_transaction_type',
        string='Transaction type',
        method=True,
        store=False,
        help='Technical field to compute the performed transaction type'
        )
    base_tax_free = fields.Float(
        string='Base Exenta IVA',
        help='La base imponible exenta de IVA, la puede encontrar en el subtotal del documento de compra'
        )
    no_vat_amount = fields.Float(
        string='Base No Objeto IVA',
        help='La base imponible "no objeto de IVA", la puede encontrar en el subtotal del documento de compra'
        )
    base_vat_0 = fields.Float(
        string='Base IVA 0%', 
        help='La base imponible que grava IVA 0%, la puede encontrar en el subtotal del documento de compra'
        )
    base_vat_no0 = fields.Float(
        string='Base Grava IVA',
        help='La base imponible que grava IVA (ya sea IVA 12%, IVA 14% u otros porcentajes), la puede encontrar en el subtotal del documento de compra'
        )
    vat_amount_no0 = fields.Float(
        string='Valor IVA',
        help='El valor del IVA (usualmente el total de la factura multiplicado por 0.12), la puede encontrar en el subtotal del documento de compra'
        )
    ice_amount = fields.Float(
        string='Valor ICE',
        help='El valor del ICE, lo puede encontrar en el subtotal del documento de compra'
        )
    total = fields.Float(
        string='Total',
        help='El valor total del documento de compra'
        )
    move_id = fields.Many2one(
        'account.move',
        required=True,
        string='Factura Reembolso',
        ondelete='cascade',
        default=lambda self: 'active_id' in self._context and self._context['active_id'] or False        
        )
    state = fields.Selection(
        string='State',
        related='move_id.state'
        )

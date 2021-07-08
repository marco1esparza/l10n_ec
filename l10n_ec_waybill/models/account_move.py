# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import datetime
import re

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('invoice_date')
    def onchange_invoice_date_edi_waybill(self):
        #usamos la fecha de vencimiento contable como la fecha de fin de la transferencia de inventario
        if self.is_waybill() and self.invoice_date and self.company_id.days_for_valid_waybill:
            self.invoice_date_due = self.invoice_date + datetime.timedelta(days=self.company_id.days_for_valid_waybill)
        
    def copy_data(self, default=None):
        #avoid duplicating waybills, it has not been tested
        res = super(AccountMove, self).copy_data(default=default)
        if self.is_waybill():
            raise ValidationError(u'No se permite duplicar las guias de remisiones, si necesita crear una debe hacerlo desde la entrega de cliente correspondiente.')
        return res

    def is_waybill(self):
        is_waybill = False
        if self.country_code == 'EC' and \
           self.move_type in ('entry') and \
           self.l10n_ec_is_waybill and \
           self.l10n_latam_document_type_id.code in ['06']:
            is_waybill = True
        return is_waybill

    def _get_invoiced_lot_values(self):
        self.ensure_one()

        lot_values = super(AccountMove, self)._get_invoiced_lot_values()

        if self.state == 'draft' or self.country_code != 'EC' or not self.is_waybill():
            return lot_values

        lot_values = []
        for line in self.l10n_ec_waybill_line_ids.filtered(lambda l: l.lot_id):
            lot_values.append({
                'barcode': line.product_id.barcode or '',
                'product_name': line.product_id.display_name,
                'quantity': line.qty_done,
                'uom_name': line.product_uom_id.name,
                'lot_name': line.lot_id.name,
                'lot_id': line.lot_id.id
            })
        return lot_values



    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.is_waybill():
            return 'l10n_ec_waybill.report_invoice_document'
        return super()._get_name_invoice_report()

    def _post(self, soft=True):
        #Hacemos un asiento contable en cero para que no se rompa el flujo de Odoo
        self.l10n_ec_make_waybill_entry()
        posted = super()._post(soft=soft)
        return posted
    
    def l10n_ec_make_waybill_entry(self):
        account_move_line_obj =  self.env['account.move.line'] 
        for waybill in self:
            if waybill.country_code == 'EC':
                if waybill.is_waybill():
                    electronic = False
                    if waybill.l10n_ec_printer_id and waybill.l10n_ec_printer_id.allow_electronic_document:
                        electronic = True
                    if not waybill.l10n_ec_stock_picking_id:
                        raise ValidationError(u'La Guía de Remisión debe tener una movimiento de inventario vinculado.')
                    if not waybill.l10n_ec_waybill_line_ids:
                        raise ValidationError(u'En el movimiento de inventario debió ingresar al menos un detalle de movimiento.')
                    # En v14 queremos permitir multiples guias de remisión para el mismo despacho 
                    # other_posted_waybills = self.env['account.move'].search([
                    #     ('l10n_ec_stock_picking_id','=',waybill.l10n_ec_stock_picking_id.id),
                    #     ('state','=','posted'),
                    #     ('id','!=',waybill.id), #exclude myself
                    #     ])
                    # if other_posted_waybills:
                    #     raise ValidationError(u'Solamente se puede tener una Guía de Remisión aprobada por despacho.')
                    #delete account.move.lines for re-posting scenario in sale withholds and purchase withholds
                    waybill.line_ids.unlink()
                    partner = waybill.partner_id.commercial_partner_id
                    vals = {
                        'name': waybill.name,
                        'move_id': waybill.id,
                        'partner_id': partner.id,
                        'account_id': waybill.company_id.l10n_ec_edi_waybill_account_id.id,
                        'date_maturity': False,
                        'quantity': 0.0,
                        'amount_currency': 0.0, #Withholds are always in company currency
                        'price_unit': 0.0,
                        'debit': 0.0,
                        'credit': 0.0,
                        'tax_base_amount': 0.0,
                        'is_rounding_line': False
                    }
                    account_move_line_obj.with_context(check_move_validity=False).create(vals)
    
    def _get_l10n_latam_documents_domain(self):
        #Filter document types according to ecuadorian type
        domain = super(AccountMove, self)._get_l10n_latam_documents_domain()
        if self.l10n_ec_is_waybill:
            domain.extend([('l10n_ec_type', '=', 'out_waybill')])
        return domain

    def l10n_ec_action_view_picking(self):
        '''
        Se muestra el picking asociado a la Guia de Remision.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

        pickings = self.mapped('l10n_ec_stock_picking_id')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        return action

    @api.depends('l10n_ec_stock_picking_id')
    def _compute_l10n_ec_picking_count(self):
        for move in self:
            count = len(self.l10n_ec_stock_picking_id)
            move.l10n_ec_picking_count = count
    
    #Columns
    l10n_ec_is_waybill = fields.Boolean(string='Is Waybill', copy=False) #para facilitar la creación de las vistas
    l10n_ec_picking_count = fields.Integer(
        compute='_compute_l10n_ec_picking_count',
        string='Number of Picking',
        )
    l10n_ec_stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Pickings',
        copy=False,
        help='Link to stock picking related to this shipment'
        )
    l10n_ec_waybill_line_ids = fields.One2many(related='l10n_ec_stock_picking_id.move_line_ids_without_package')
    l10n_ec_waybill_carrier_id = fields.Many2one(
        'l10n_ec.waybill.carrier',
        string='Carrier',
        states = {'draft': [('readonly', False)]},
        ondelete='restrict',
        check_company=True,
        tracking=True,
        copy=False,
        readonly = True,
        )
    l10n_ec_waybill_loc_dest_address = fields.Char(
        string='Destination waybill address',
        readonly = True,
        states = {'draft': [('readonly', False)]},
        copy=False,
        help='Destination waybill address as in VAT document, saved in picking orders only not in partner'
        )
    l10n_ec_waybill_move_reason = fields.Char(string='Move reason', size=300, help='', copy=False, readonly = True,
        states = {'draft': [('readonly', False)]}
        )
    l10n_ec_license_plate = fields.Char(
        string='Vehicle Plate',
        size=8,
        tracking=True,
        readonly = True,
        states = {'draft': [('readonly', False)]}
        )
    
    @api.constrains('l10n_ec_license_plate')
    def _check_l10n_ec_license_plate(self):
        if self.l10n_ec_license_plate:
            valid = re.search("([A-Z]{3,}-[0-9]{4,})", self.l10n_ec_license_plate)
            # Nota 1: En Ecuador también se soporta dos letras, pero es para uso diplomatico, no para guías de remisión
            # Nota 2: Parece ser que las placas de moto son dos letras, raya, tres numeros y una letra. Ej. AA-000A
            if not valid:
                raise ValidationError('La placa debe tener 3 letras, una rayita, y 4 numeros (Ej. PDA-0123)')
                


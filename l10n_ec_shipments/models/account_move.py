# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import datetime

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('invoice_date')
    def onchange_invoice_date_edi_shipments(self):
        if self.is_shipment() and self.invoice_date and self.company_id.days_for_valid_waybill:
            self.invoice_date_due = self.invoice_date + datetime.timedelta(days=self.company_id.days_for_valid_waybill)
        
    def copy_data(self, default=None):
        #avoid duplicating withholds, it has not been tested
        res = super(AccountMove, self).copy_data(default=default)
        if self.is_shipment():
            raise ValidationError(u'No se permite duplicar las guias de remisiones, si necesita crear una debe hacerlo desde la entrega de cliente correspondiente.')
        return res

    def is_shipment(self):
        is_shipment = False
        if self.country_code == 'EC' and self.move_type in ('entry') and self.l10n_ec_is_shipment and self.l10n_latam_document_type_id.code in ['06']:
            is_shipment = True
        return is_shipment

    def is_invoice(self, include_receipts=False):
        #Hack, permite enviar por mail documentos distintos de facturas
        is_invoice = super(AccountMove, self).is_invoice(include_receipts)
        if self._context.get('l10n_ec_send_email_others_docs', False):
            if self.is_shipment():
                is_invoice = True
        return is_invoice

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.is_shipment():
            return 'l10n_ec_shipments.report_invoice_document'
        return super()._get_name_invoice_report()

    #Columns
    l10n_ec_is_shipment = fields.Boolean(string='Is Shipment', copy=False)
    l10n_ec_stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Pickings',
        copy=False,
        help='Link to stock picking related to this shipment'
        )
    l10n_ec_move_line_ids = fields.One2many(related='l10n_ec_stock_picking_id.move_line_ids_without_package')
    l10n_ec_stock_carrier_id = fields.Many2one('l10n_ec.stock.carrier', copy=False, readonly = True,
        states = {'draft': [('readonly', False)]})
    l10n_ec_waybill_loc_dest_address = fields.Char(string='Destination waybill address', readonly = True,
        states = {'draft': [('readonly', False)]}, help='Destination waybill address as in VAT document, saved in picking orders only not in partner', copy=False)
    l10n_ec_move_reason = fields.Char(string='Move reason', size=300, help='', copy=False, readonly = True,
        states = {'draft': [('readonly', False)]})

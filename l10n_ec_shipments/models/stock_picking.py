# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_ec_allow_edi_shipments(self):
        #shows/hide "ADD EDI SHIPMENT" button on picking
        for picking in self:
            result = False
            if picking.company_id.country_code == 'EC' and picking.state == 'done':
                if picking.location_id.usage == 'internal':
                    result = True
            picking.l10n_ec_allow_edi_shipments = result

    @api.depends('l10n_ec_edi_shipment_ids')
    def _compute_l10n_ec_edi_shipment_count(self):
        for picking in self:
            count = len(self.l10n_ec_edi_shipment_ids)
            picking.l10n_ec_edi_shipment_count = count

    def _l10n_ec_prepare_shipment_default_values(self):
        # Compras
        if not self.company_id.l10n_ec_edi_shipments_account_id:
            raise ValidationError(_('Debe asignar una cuenta para Guías de Remisión en la compañía.'))
        move_type = 'entry'
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
            [('country_id.code', '=', 'EC'),
             ('code', '=', '06'),
             ('l10n_ec_type', '=', 'out_waybill'),
             ], order="sequence asc", limit=1)
        journal_id = False
        journals = self.env['account.journal'].search([('code', '=', 'GURMN')])
        if journals:
            journal_id = journals[0].id
        if self.picking_type_code == 'outgoing':
            l10n_ec_move_reason = 'Entrega de Mercaderia'
        elif self.picking_type_code == 'internal':
            l10n_ec_move_reason = 'Transferencia Interna'
        default_values = {
            'invoice_date': fields.Date.today(),
            'journal_id': journal_id,
            'invoice_payment_term_id': None,
            'move_type': move_type,
            'line_ids': [(5, 0, 0)],
            'invoice_origin': self.origin + ' ; ' + self.name,
            'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
            'l10n_ec_invoice_payment_method_ids': [(5, 0, 0)],
            'l10n_ec_waybill_loc_dest_address': ' '.join([value for value in [self.partner_id.street, self.partner_id.street2] if value]),
            'l10n_ec_authorization': False,
            'l10n_ec_stock_picking_id': self.id,
            'l10n_ec_is_shipment': True,
            'partner_id': self.partner_id.id,
            'l10n_ec_move_reason': l10n_ec_move_reason,
            'invoice_line_ids': [(0, 0, {
                'name': self.name,
                'price_unit': 0.0,
                'quantity': 1,
                'tax_ids': [],
                'account_id': self.company_id.l10n_ec_edi_shipments_account_id.id,
                })]
        }

        return default_values

    def l10n_ec_add_edi_shipment(self):
        for picking in self:
            if not picking.company_id.country_code == 'EC':
                raise ValidationError(_('Shipment documents are only aplicable for Ecuador'))

        default_values = self._l10n_ec_prepare_shipment_default_values()
        new_move = self.env['account.move'].with_context(default_shipment_type='edi_shipment').create(default_values)
        new_move.onchange_invoice_date_edi_shipments()
        return self.l10n_ec_action_view_shipments()

    def l10n_ec_action_view_shipments(self):
        '''
        '''
        action = 'account.action_move_journal_line'
        view = 'l10n_ec_shipments.view_move_form_shipment'
        action = self.env.ref(action)
        result = action.read()[0]
        result['name'] = _('Shipments')
        l10n_ec_edi_shipment_ids = self.l10n_ec_edi_shipment_ids.ids
        if len(l10n_ec_edi_shipment_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(l10n_ec_edi_shipment_ids) + ")]"
        else:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = l10n_ec_edi_shipment_ids and l10n_ec_edi_shipment_ids[0] or False
        return result

    #Columns
    l10n_ec_edi_shipment_ids = fields.One2many(
        'account.move',
        'l10n_ec_stock_picking_id',
        string='Account Move',
        copy=False,
        help='Link to account move edi related to this shipment'
        )
    l10n_ec_allow_edi_shipments = fields.Boolean(
        compute='_l10n_ec_allow_edi_shipments',
        string='Allow EDI Shipments',
        method=True,
        help='Technical field to show/hide "ADD EDI SHIPMENTS" button'
    )
    l10n_ec_edi_shipment_count = fields.Integer(
        compute='_compute_l10n_ec_edi_shipment_count',
        string='Number of EDI Shipments',
    )

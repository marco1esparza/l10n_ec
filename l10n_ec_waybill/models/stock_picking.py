# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _l10n_ec_allow_edi_waybill(self):
        #shows/hide "ADD EDI SHIPMENT" button on picking
        for picking in self:
            result = False
            if picking.company_id.country_code == 'EC' and picking.state == 'done':
                if picking.location_id.usage == 'internal':
                    result = True
            picking.l10n_ec_allow_edi_waybill = result

    @api.depends('l10n_ec_edi_waybill_ids')
    def _compute_l10n_ec_edi_waybill_count(self):
        for picking in self:
            count = len(self.l10n_ec_edi_waybill_ids)
            picking.l10n_ec_edi_waybill_count = count

    def _l10n_ec_prepare_shipment_default_values(self):
        # Compras
        if not self.company_id.l10n_ec_edi_waybill_account_id:
            raise ValidationError(_('Debe asignar una cuenta para Guías de Remisión en la compañía.'))
        move_type = 'entry'
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search(
            [('country_id.code', '=', 'EC'),
             ('code', '=', '06'),
             ('l10n_ec_type', '=', 'out_waybill'),
             ], order="sequence asc", limit=1)
        waybill_journal = self.env['account.journal'].search([('code', '=', 'GRMSN')])
        #computamos la razón de movimiento
        destination_usage = self.location_dest_id.usage
        if destination_usage in ['customer']:
            l10n_ec_waybill_move_reason = 'Despacho de Mercaderia'
        elif destination_usage in ['supplier']:
            l10n_ec_waybill_move_reason = 'Devolución de Mercaderia'
        elif destination_usage == 'internal':
            l10n_ec_waybill_move_reason = 'Transferencia Interna'
        else:
            l10n_ec_waybill_move_reason = 'Otros'
        origin = []
        self.origin and origin.append(self.origin)
        self.name and origin.append(self.name)
        origin = ";".join(origin)
        default_values = {
            'invoice_date': fields.Date.today(),
            'journal_id': waybill_journal.id,
            'invoice_payment_term_id': None,
            'move_type': move_type,
            'line_ids': [(5, 0, 0)],
            'invoice_origin': origin,
            'l10n_latam_document_type_id': l10n_latam_document_type_id.id,
            'l10n_ec_invoice_payment_method_ids': [(5, 0, 0)],
            'l10n_ec_waybill_loc_dest_address': ' '.join([value for value in [self.partner_id.street, self.partner_id.street2] if value]),
            'l10n_ec_authorization': False,
            'l10n_ec_stock_picking_id': self.id,
            'l10n_ec_is_waybill': True,
            'partner_id': self.partner_id.id,
            'l10n_ec_waybill_move_reason': l10n_ec_waybill_move_reason,
        }
        return default_values

    def l10n_ec_add_edi_waybill(self):
        for picking in self:
            if not picking.company_id.country_code == 'EC':
                raise ValidationError(_('Shipment documents are only aplicable for Ecuador'))
        default_values = self._l10n_ec_prepare_shipment_default_values()
        new_move = self.env['account.move'].with_context(default_waybill_type='out_waybill').create(default_values)
        new_move.onchange_invoice_date_edi_waybill()
        return self.l10n_ec_action_view_waybills()

    def l10n_ec_action_view_waybills(self):
        action = 'account.action_move_journal_line'
        view = 'l10n_ec_waybill.view_move_form_shipment'
        action = self.env.ref(action)
        result = action.sudo().read()[0]
        result['name'] = _('Waybills')
        l10n_ec_edi_waybill_ids = self.l10n_ec_edi_waybill_ids.ids
        if len(l10n_ec_edi_waybill_ids) > 1:
            result['domain'] = "[('id', 'in', " + str(l10n_ec_edi_waybill_ids) + ")]"
        else:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = l10n_ec_edi_waybill_ids and l10n_ec_edi_waybill_ids[0] or False
        return result
    
    l10n_ec_edi_waybill_ids = fields.One2many(
        'account.move',
        'l10n_ec_stock_picking_id',
        string='Account Move',
        copy=False,
        help='Link to account move edi related to this shipment'
        )
    l10n_ec_allow_edi_waybill = fields.Boolean(
        compute='_l10n_ec_allow_edi_waybill',
        string='Allow EDI Waybill',
        tracking=True,
        compute_sudo=True,
        help='Technical field to show/hide "ADD EDI WAYBILL" button'
        )
    l10n_ec_edi_waybill_count = fields.Integer(
        compute='_compute_l10n_ec_edi_waybill_count',
        compute_sudo=True,
        string='Technical field to compute number of EDI Waybills',
        )

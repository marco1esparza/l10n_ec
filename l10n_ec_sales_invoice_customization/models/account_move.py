# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict
from odoo.tools.misc import formatLang


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.onchange('l10n_ec_invoice_custom')
    def _onchange_l10n_ec_invoice_custom(self):
        '''
        Onchange para copiar los valores de las lineas de la factura a las lineas personalizadas
        '''
        in_draft_mode = self != self._origin
        if self.l10n_ec_invoice_custom and not self.l10n_ec_custom_line_ids:
            create_method = in_draft_mode and self.env['l10n_ec.custom.move.line'].new or self.env['l10n_ec.custom.move.line'].create
            for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
                custom_line = create_method({'name': line.name,
                                             'quantity': line.quantity,
                                             'price_unit': line.price_unit,
                                             'discount': line.discount,
                                             'tax_ids': line.tax_ids,
                                             'move_id': line.move_id,
                                             'partner_id': line.partner_id,
                                             'currency_id': line.currency_id})
                custom_line._onchange_price_subtotal()

    def _post(self, soft=True):
        '''
        Invocamos el metodo post para mandar a validar que el grupo de impuesto nativo y los personalizados sean iguales
        '''
        res = super(AccountMove, self)._post(soft)
        for invoice in self.filtered(lambda x: x.country_code == 'EC' and x.l10n_latam_use_documents):
            invoice._l10n_ec_validate_custom_invoice()
        return res
    
    def _l10n_ec_validate_custom_invoice(self):
        # Validamos para las facturas personalizadas
        # que el grupo de impuestos sea igual al grupo de impuestos de las lineas personalizadas.
        if self.l10n_ec_invoice_custom and self.amount_custom_by_group != self.amount_by_group:
            raise UserError('Los valores de las líneas personalizadas deben conincidir con los totales de las líneas originales.')    
    
    @api.depends('l10n_ec_custom_line_ids.price_subtotal', 'partner_id', 'currency_id')
    def _compute_invoice_custom_taxes_by_group(self):
        for move in self.filtered('l10n_latam_document_type_id'):
            if not move.is_invoice(include_receipts=True) or move.move_type not in ('out_invoice', 'out_refund') \
                    or not move.l10n_ec_invoice_custom:
                move.amount_custom_by_group = {}
                continue

            is_refund = False
            handle_price_include = False
            if move.is_invoice(include_receipts=True):
                is_refund = move.move_type in ('out_refund', 'in_refund')
                handle_price_include = True

            lang_env = move.with_context(lang=move.partner_id.lang).env
            tax_balance_multiplicator = 1 if move.is_inbound(True) else -1
            res = {}
            for line in move.l10n_ec_custom_line_ids:
                for tax in line.tax_ids.flatten_taxes_hierarchy():
                    if tax.tax_group_id not in res:
                        res.setdefault(tax.tax_group_id, {'base': 0.0, 'amount': 0.0})

                    base_amount = tax_balance_multiplicator * (line.price_subtotal)
                    res[tax.tax_group_id]['base'] += base_amount
                    tax_amount = tax.with_context(
                        force_sign=move._get_tax_force_sign()).compute_all(
                        base_amount,
                        currency=line.currency_id,
                        quantity=1.0,
                        product=False,
                        partner=line.partner_id,
                        is_refund=is_refund,
                        handle_price_include=handle_price_include,
                    )
                    res[tax.tax_group_id]['amount'] += tax_amount['taxes'][0]['amount']

            res = sorted(res.items(), key=lambda l: l[0].sequence)
            move.amount_custom_by_group = [(
                group.name,
                #TODO: estos round buscarle una solucion en el original no estan 
                round(amounts['amount'], 2),
                round(amounts['base'], 2),
                formatLang(lang_env, amounts['amount'], currency_obj=move.currency_id),
                formatLang(lang_env, amounts['base'], currency_obj=move.currency_id),
                len(res),
                group.id
            ) for group, amounts in res]

    #Columns
    amount_custom_by_group = fields.Binary(
        string='Tax amount by group',
        compute='_compute_invoice_custom_taxes_by_group',
        help='Edit Tax amounts if you encounter rounding issues.'
        )
    l10n_ec_invoice_custom = fields.Boolean(
        string='Factura Personalizada',
        tracking=True
        )
    l10n_ec_custom_line_ids = fields.One2many(
        'l10n_ec.custom.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]}
        )    
    
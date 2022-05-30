# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import compile as re_compile

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
L10N_EC_VAT_RATES = {
    2: 12.0,
    3: 14.0,
    0: 0.0,
    6: 0.0,
    7: 0.0,
}
_L10N_EC_CODES = {
    2: ('vat12', 'vat14', 'zero_vat', 'not_charged_vat', 'exempt_vat'),  # IVA
    3: ('ice',),  # ICE
    5: ('irbpnr',),  # IRBPNR
}

class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ec_authorization_number = fields.Char(
        "Authorization number", size=49, copy=False, index=True, readonly=True,
        help="Set once the government confirms reception of the document",
    )
    l10n_ec_authorization_date = fields.Datetime(
        "Authorization date", copy=False, readonly=True,
        help="Set once the government authorizes the document",
    )
    l10n_latam_internal_type = fields.Selection(
        related='l10n_latam_document_type_id.internal_type',
        string='Internal Type'
    )
    l10n_ec_withhold_type = fields.Selection(
        related='journal_id.l10n_ec_withhold_type',
    )
    l10n_ec_allow_withhold = fields.Boolean(
        compute='_l10n_ec_allow_withhold',
        string='Allow Withhold',
        help='Technical field to show/hide "ADD WITHHOLD" button'
    )
    l10n_ec_withhold_line_ids = fields.One2many(
        'account.move.line',
        string='Withhold Lines',
        compute='_compute_l10n_ec_withhold_ids',
        readonly=True
    )
    l10n_ec_withhold_ids = fields.Many2many(
        'account.move',
        compute='_compute_l10n_ec_withhold_ids',
        string='Withholds',
        help='Link to withholds related to this invoice'
    )
    l10n_ec_withhold_count = fields.Integer(
        compute='_compute_l10n_ec_withhold_ids',
        string='Withholds Count',
        help='Technical field to count linked withhold for the smart button'
    )
    l10n_ec_withhold_origin_ids = fields.Many2many(
        'account.move',
        compute='_compute_l10n_ec_withhold_ids',
        string='Invoices',
        copy=False,
        help='Technical field to limit elegible invoices related to this withhold'
    )
    # subtotals
    l10n_ec_withhold_vat_amount = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='Total IVA',
        store=False,
        readonly=True,
        help='Total IVA value of withhold'
    )
    l10n_ec_withhold_profit_amount = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='Total RENTA',
        store=False,
        readonly=True,
        help='Total renta value of withhold'
    )
    l10n_ec_withhold_vat_base = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='Total Base IVA',
        store=False,
        readonly=True,
        help='Total base IVA of withhold'
    )
    l10n_ec_withhold_profit_base = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='Total Base RENTA',
        store=False,
        readonly=True,
        help='Total base renta of withhold'
    )
    l10n_ec_withhold_total_amount = fields.Monetary(
        string='Total Withhold',
        compute='_l10n_ec_compute_withhold_totals',
        store=False,
        readonly=True,
        help='Total value of withhold'
    )

    # ===== OTHER METHODS =====
    #TODO Trescloud&Odoo, decide where should this methods be located inside the file
    
    def l10n_ec_add_withhold(self):
        # Launches the withholds wizard linked to selected invoices
        ctx = self._context.copy()
        ctx.update({
            'active_ids': self.ids,
            'active_model': 'account.move',
            })
        # First create the wizard then show on popup, so a real temporary ID is created (instead of a newID)
        # doing this way so the "suggested" wihhold line filters by context the taxes and invoices  
        new_withhold_wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(ctx).create({})
        return {
            'name': u'Withholding',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'l10n_ec.wizard.account.withhold',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'context': self.env.context,
            'res_id': new_withhold_wizard.id,
        }
    
    def l10n_ec_action_view_withholds(self):
        # Navigate from the invoice to its withholds
        l10n_ec_withhold_ids = self.env.context.get('withhold', []) or self.l10n_ec_withhold_ids.ids
        if len(l10n_ec_withhold_ids) == 1:
            return {
                'name': u'Withholding',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'res_id': l10n_ec_withhold_ids[0],
            }
        else:
            action = 'account.action_move_journal_line'
            action = self.env.ref(action)
            result = action.sudo().read()[0]
            result['name'] = _('Withholds')
            result['domain'] = "[('id', 'in', " + str(l10n_ec_withhold_ids) + ")]"            
            return result

    # ===== OVERRIDES & ONCHANGES =====

    def unlink(self):
        # OVERRIDE
        ecuadorian_moves = self.filtered(
            lambda x: x.country_code == "EC"
            and x.journal_id.type not in ("sale", "purchase", "general")
        )
        if ecuadorian_moves:
            super(
                AccountMove, ecuadorian_moves.with_context(force_delete=True)
            ).unlink()
        return super(AccountMove, self - ecuadorian_moves).unlink()
    
    def copy_data(self, default=None):
        # avoid duplicating withholds, should be created always from the withhold wizard
        # it also correctly blocks user from reversing the withhold
        res = super(AccountMove, self).copy_data(default=default)
        if self.is_withholding():
            raise ValidationError(u'You can not duplicate a withhold, instead create a new one from the invoice.')
        return res

    def is_invoice(self, include_receipts=False):
        # OVERRIDE: For Ecuador we consider is_invoice for all edis (invoices and wihtholds, in the future maybe waybills, etc)
        # It enables the send email button, the edi process, the customer portal, printing the qweb report, and other stuff.
        if self.country_code == 'EC':
            if self.is_withholding():
                return True
        return super(AccountMove, self).is_invoice(include_receipts)
        
    def _creation_message(self):
        # OVERRIDE, withholds should have a dedicated message equivalent to invoices, otherwise a simple "Journal Entry created" was shown
        if self.is_withholding():
            return _('Withhold Created')
        return super()._creation_message()
        
    def _is_manual_document_number(self):
        # OVERRIDE
        if self.journal_id.company_id.country_id.code == 'EC':
            purchase_liquidation = self.env.context.get('internal_type',
                                                        self.l10n_latam_document_type_id.internal_type) == 'purchase_liquidation'
            return self.journal_id.type == 'purchase' and not purchase_liquidation
        return super()._is_manual_document_number()

    def _get_l10n_ec_identification_type(self):
        # OVERRIDE
        # TODO fix l10n_ec function ? Why is there a difference ?
        # https://github.com/odoo/odoo/blob/15.0/addons/l10n_ec/models/account_move.py#L137
        code = super()._get_l10n_ec_identification_type()
        return "08" if code in ("09", "20", "21") else code
    
    #TODO Trescloud&Odoo: Evaluate if it is still necesary as now there is a Qweb report, maybe remove the method after Stan finishes the invoice RIDE
    # def _get_name_invoice_report(self):
    #     self.ensure_one()
    #     if self.is_withholding():
    #         return 'l10n_ec_edi.report_invoice_document'
    #     return super()._get_name_invoice_report()
    
    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        # Override to allow duplicated numbers in sales withhold as those are issued by different customers 
        moves = self.filtered(lambda move: move.state == 'posted')
        if not moves:
            return
        self.flush()
        out_withhold = self.filtered(lambda move: move.l10n_ec_withhold_type == 'out_withhold')
        if out_withhold:
            # /!\ Computed stored fields are not yet inside the database.
            self._cr.execute('''
                    SELECT move2.id
                    FROM account_move move
                    INNER JOIN account_move move2 ON
                        move2.name = move.name
                        AND move2.journal_id = move.journal_id
                        AND move2.move_type = move.move_type
                        AND move2.id != move.id
                    WHERE move.id IN %s AND move2.partner_id IN %s AND move2.state = 'posted'
                ''', [tuple(moves.ids), tuple(moves.mapped('partner_id').ids)])
            res = self._cr.fetchone()
            if res:
                raise ValidationError(_('Posted journal entry must have an unique sequence number per company.'))
            return
        return super(AccountMove, self)._check_unique_sequence_number()

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # only shows previously selected invoices in the withhold wizard lines
        if self.env.context.get('l10n_ec_related_invoices_ctx'):
            return super(AccountMove, self)._name_search(name, args=[
                ('id', 'in', self.env.context.get('l10n_ec_related_invoices_ctx'))], operator=operator, limit=limit,
                                                         name_get_uid=name_get_uid)
        return super(AccountMove, self)._name_search(name, args=args, operator=operator, limit=limit,
                                                     name_get_uid=name_get_uid)
    
    # ===== GETTERS =====

    def l10n_ec_get_invoice_type(self):
        self.ensure_one()

        invoice_type = self.move_type
        internal_type = self.env.context.get("internal_type") \
            or self.l10n_latam_document_type_id.internal_type \
            or "invoice"
        document_type = ""
        if invoice_type == "in_invoice" and internal_type == "invoice":
            document_type = "in_invoice"
        elif invoice_type == "out_invoice" and internal_type == "invoice":
            document_type = "out_invoice"
        elif invoice_type == "out_refund":
            document_type = "out_refund"
        elif invoice_type == "in_refund":
            document_type = "in_refund"
        elif invoice_type == "in_invoice" and internal_type == "purchase_liquidation":
            document_type = "purchase_liquidation"
        elif invoice_type == "in_invoice" and internal_type == "debit_note":
            document_type = "debit_note_in"
        elif invoice_type == "out_invoice" and internal_type == "debit_note":
            document_type = "debit_note_out"
        return document_type

    def l10n_ec_get_document_code_sri(self):
        invoice_type = self.l10n_ec_get_invoice_type()
        if invoice_type == "out_invoice":
            document_code_sri = "01"
        else:
            document_code_sri = self.l10n_latam_document_type_id.code
        return document_code_sri

    def l10n_ec_compute_amount_discount(self):
        self.ensure_one()
        return sum(
            (((line.discount * line.price_unit) * line.quantity) / 100.0)
            for line in self.invoice_line_ids
        )

    def l10n_ec_get_invoice_edi_data(self):
        self.ensure_one()
        data = {
            "taxes_data": self._l10n_ec_get_taxes_grouped_by_tax_group(),
            "additional_info": {
                "pedido": self.name,
                "vendedor": self.invoice_user_id.name,
                "email": self.invoice_user_id.email,
                "narracion": self._l10n_ec_remove_forbidden_chars(str(self.narration)),
            },
        }
        if self.move_type == "out_refund":  # TODO handled in MVP ?
            data.update({
                "modified_doc": self.reversed_entry_id,
            })
        if self.l10n_latam_document_type_id.internal_type == "debit_note":
            data.update({
                "modified_doc": self.debit_origin_id,
                "invoice_lines": [line for line in self.invoice_line_ids.filtered(lambda x: not x.display_type)],
            })
        return data

    def is_withholding(self):
        #TODO Discuss with Odoo, the method can be simplified to compute based on journal type, but in the proposed way is more "secure"
        #TODO Discuss with Odoo, method name doesn't have l10n_ec prefix to look alike the is_invoice() method.  
        is_withholding = False
        if self.country_code == 'EC' and self.move_type in ('entry') \
           and self.l10n_ec_withhold_type and self.l10n_ec_withhold_type in ('in_withhold', 'out_withhold') \
           and self.l10n_latam_document_type_id.code in ['07']:
            is_withholding = True
        return is_withholding

    # ===== PRIVATE =====

    def _l10n_ec_get_taxes_grouped_by_tax_group(self, exclude_withholding=True):
        self.ensure_one()

        def group_by_tax_group(tax_values):
            code_percentage = self._l10n_ec_map_vat_subtaxes(tax_values["tax_id"])
            return {
                "tax_group_id": tax_values["tax_id"].tax_group_id.id,
                "code": self._l10n_ec_map_tax_groups(tax_values["tax_id"]),
                "code_percentage": code_percentage,
                "rate": L10N_EC_VAT_RATES[code_percentage],
            }

        def filter_withholding_taxes(tax_values):
            tax_group_withhold_vat_sale = self.env.ref("l10n_ec.tax_group_withhold_vat_sale")
            tax_group_withhold_vat_purchase = self.env.ref("l10n_ec.tax_group_withhold_vat_purchase")
            tax_group_withhold_income_sale = self.env.ref("l10n_ec.tax_group_withhold_income_sale")
            tax_group_withhold_income_purchase = self.env.ref("l10n_ec.tax_group_withhold_income_purchase")
            withhold_group_ids = (tax_group_withhold_vat_sale + tax_group_withhold_vat_sale + tax_group_withhold_income_sale + tax_group_withhold_income_purchase).ids
            return tax_values["tax_id"].tax_group_id.id not in withhold_group_ids

        taxes_data = self._prepare_edi_tax_details(
            filter_to_apply=exclude_withholding and filter_withholding_taxes or None,
            grouping_key_generator=group_by_tax_group,
        )
        return taxes_data

    def _l10n_ec_map_vat_subtaxes(self, tax_id):
        # Maps specific vat types to codes for electronic invoicing
        if tax_id.tax_group_id.l10n_ec_type == 'vat12':
            return 2
        elif tax_id.tax_group_id.l10n_ec_type == 'vat14':
            return 3
        elif tax_id.tax_group_id.l10n_ec_type == 'zero_vat':
            return 0
        elif tax_id.tax_group_id.l10n_ec_type == 'not_charged_vat':
            return 6
        elif tax_id.tax_group_id.l10n_ec_type == 'exempt_vat':
            return 7
        else:
            # TODO: Implement all other cases that aren't for IVA (eg. ICE, IRBPNR)
            raise NotImplementedError(f"Tax type not managed: {tax_id.tax_group_id.l10n_ec_type}")

    def _l10n_ec_map_tax_groups(self, tax_id):
        # Maps different tax types (aka groups) to codes for electronic invoicing
        for code, types in _L10N_EC_CODES.items():
            if tax_id.tax_group_id.l10n_ec_type in types:
                return code
        raise NotImplementedError(u'No se ha implementado ningún código en los documentos '
                                  u'electrónicos para este tipo de impuestos.')

    def _l10n_ec_get_credit_days(self, move_line):
        self.ensure_one()
        return max(((move_line.date_maturity - self.invoice_date).days), 0)

    def _l10n_ec_get_payment_data(self):
        pay_term_line_ids = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ("receivable", "payable")  # TODO is payable necessary ?
        )
        l10n_ec_sri_payment = self.l10n_ec_sri_payment_id
        payment_data = []
        for line in pay_term_line_ids:
            payment_vals = {
                "payment_code": l10n_ec_sri_payment.code,
                "payment_total": abs(line.price_total),
            }
            if self.invoice_payment_term_id:
                payment_vals.update({
                    "payment_term": self._l10n_ec_get_credit_days(line),
                    "time_unit": "dias",
                })
            payment_data.append(payment_vals)
        return payment_data

    @api.depends('l10n_ec_withhold_line_ids')
    def _l10n_ec_compute_withhold_totals(self):
        # Used for aesthetics, to view withhold subtotal at the bottom of the withhold account.move
        for invoice in self:
            l10n_ec_withhold_vat_amount = 0.0
            l10n_ec_withhold_profit_amount = 0.0
            l10n_ec_withhold_vat_base = 0.0
            l10n_ec_withhold_profit_base = 0.0
            l10n_ec_withhold_total_amount = 0.0
            for line in invoice.l10n_ec_withhold_line_ids:
                if line.tax_line_id.tax_group_id:
                    if line.tax_line_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
                        l10n_ec_withhold_vat_amount += line.credit if invoice.l10n_ec_withhold_type == 'in_withhold' else line.debit
                        l10n_ec_withhold_vat_base += line.tax_base_amount
                    if line.tax_line_id.tax_group_id.l10n_ec_type in ['withhold_income_sale',
                                                                      'withhold_income_purchase']:
                        l10n_ec_withhold_profit_amount += line.credit if invoice.l10n_ec_withhold_type == 'in_withhold' else line.debit
                        l10n_ec_withhold_profit_base += line.tax_base_amount
            invoice.l10n_ec_withhold_vat_amount = l10n_ec_withhold_vat_amount
            invoice.l10n_ec_withhold_profit_amount = l10n_ec_withhold_profit_amount
            invoice.l10n_ec_withhold_vat_base = l10n_ec_withhold_vat_base
            invoice.l10n_ec_withhold_profit_base = l10n_ec_withhold_profit_base
            invoice.l10n_ec_withhold_total_amount = l10n_ec_withhold_vat_amount + l10n_ec_withhold_profit_amount

    def _l10n_ec_allow_withhold(self):
        # shows/hide "ADD WITHHOLD" button on invoices
        for invoice in self:
            result = False
            if invoice.country_code == 'EC' and invoice.state == 'posted':
                if invoice.l10n_latam_document_type_id.code in ['01', '02', '03', '18']:
                    result = True
            invoice.l10n_ec_allow_withhold = result
    
    @api.depends('line_ids')
    def _compute_l10n_ec_withhold_ids(self):
        for move in self:
            move.l10n_ec_withhold_line_ids = move.line_ids.filtered(lambda l: l.tax_line_id)
            move.l10n_ec_withhold_ids = self.env['account.move.line'].search(
                [('l10n_ec_withhold_invoice_id', '=', move.id)]).mapped('move_id')
            move.l10n_ec_withhold_origin_ids = move.line_ids.mapped('l10n_ec_withhold_invoice_id')
            move.l10n_ec_withhold_count = len(move.l10n_ec_withhold_ids)

    # ===== PRIVATE (static) =====

    @api.model
    def _l10n_ec_remove_forbidden_chars(self, s, max_len=300):
        return "".join("".join(x) for x in re_compile(r'([A-Z]|[a-z]|[0-9]|ñ|Ñ)+([\w]|[\S]|[^\n])*').findall(s))[:max_len]


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ec_withhold_invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        ondelete='restrict',
        help='Link the withholding line to its invoice'
    )

    def _l10n_ec_get_computed_taxes(self):
        #TODO JOSE: Mover este metodo a la linea del wizard
        '''
        For purchases adds prevalence for tax mapping to ease withholds in Ecuador, in the following order:
        For profit withholding tax:
        - If payment type == credit card then withhold code 332G, if not then
        - partner_id.l10n_ec_force_profit_withhold, if not set then
        - product_id profit withhold, if not set then
        - company fallback profit withhold for goods or for services
        For vat withhold tax:
        - If product is consumable then vat_goods_withhold_tax_id
        - If product is services or not set then vat_services_withhold_tax_id
        If withholds doesn't apply to the document type then remove the withholds
        '''
        if self.move_id.country_code == 'EC':
            super_tax_ids = self.env['account.tax']
            vat_withhold_tax = False
            profit_withhold_tax = False
            if self.move_id.is_purchase_document(include_receipts=True):
                if not self.exclude_from_invoice_tab:  # just regular invoice lines
                    #if self.move_id.l10n_ec_require_withhold_tax:  # compute withholds #TODO ANDRES refactorizar
                    if True:
                        company_id = self.move_id.company_id
                        contributor_type = self.partner_id.contributor_type_id
                        tax_groups = super_tax_ids.mapped('tax_group_id').mapped('l10n_ec_type')
                        # compute vat withhold
                        if 'vat12' in tax_groups or 'vat14' in tax_groups:
                            if not self.product_id or self.product_id.type in ['consu', 'product']:
                                vat_withhold_tax = contributor_type.vat_goods_withhold_tax_id
                            else:  # services
                                vat_withhold_tax = contributor_type.vat_services_withhold_tax_id
                                # compute profit withhold
                        if self.move_id.l10n_ec_sri_payment_id.code in ['16', '18', '19']:
                            # payment with debit card, credit card or gift card retains 0%
                            profit_withhold_tax = company_id.l10n_ec_profit_withhold_tax_credit_card
                        elif contributor_type.profit_withhold_tax_id:
                            profit_withhold_tax = contributor_type.profit_withhold_tax_id
                        elif self.product_id.withhold_tax_id:
                            profit_withhold_tax = self.product_id.withhold_tax_id
                        elif 'withhold_income_sale' in tax_groups or 'withhold_income_purchase' in tax_groups:
                            pass  # keep the taxes coming from product.product... for now
                        else:  # if not any withhold tax then fallback
                            if self.product_id and self.product_id.type == 'service':
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_services
                            else:
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_goods
                    else:  # remove withholds
                        super_tax_ids = super_tax_ids.filtered(
                            lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat_sale',
                                                                              'withhold_vat_purchase',
                                                                              'withhold_income_sale',
                                                                              'withhold_income_purchase'])
            if vat_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(
                    lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat_sale', 'withhold_vat_purchase'])
                super_tax_ids += vat_withhold_tax
            if profit_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(
                    lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_income_sale',
                                                                      'withhold_income_purchase'])
                super_tax_ids += profit_withhold_tax
        return super_tax_ids

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import compile as re_compile

from odoo import _, api, fields, models
from odoo.tools.misc import format_date
from odoo.exceptions import ValidationError, UserError
from odoo.addons.l10n_ec.models.res_partner import verify_final_consumer

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
L10N_EC_WITHHOLD_CODES = {
    'withhold_vat_purchase': 2,
    'withhold_income_purchase': 1,
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
    l10n_ec_show_add_withhold = fields.Boolean(
        compute='_l10n_ec_show_add_withhold',
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
    l10n_ec_withhold_origin_count = fields.Integer(
        compute='_compute_l10n_ec_withhold_ids',
        string='Invoices Count',
        help='Technical field to count linked invoice for the smart button'
    )
    # subtotals
    l10n_ec_withhold_vat_amount = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='VAT Withhold',
        store=False,
        readonly=True,
        help='The total amount of withhold over VAT'
    )
    l10n_ec_withhold_profit_amount = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='Profit Withhold',
        store=False,
        readonly=True,
        help='The total amount of withhold over profits'
    )
    l10n_ec_withhold_vat_base = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='VAT Withhold Base',
        store=False,
        readonly=True,
        help='The total vat base amount affected by the taxes in this withhold'
    )
    l10n_ec_withhold_profit_base = fields.Monetary(
        compute='_l10n_ec_compute_withhold_totals',
        string='Profit Withhold Base',
        store=False,
        readonly=True,
        help='The total profit base amount affected by the taxes in this withhold'
    )
    l10n_ec_withhold_total_amount = fields.Monetary(
        string='Withhold Total',
        compute='_l10n_ec_compute_withhold_totals',
        store=False,
        readonly=True,
        help='The total value of the withhold, sent to the payable or receivable journal line'
    )

    # ===== OTHER METHODS =====
    #TODO Trescloud&Odoo, decide where should this methods be located inside the file

    def write(self, vals):
        PROTECTED_FIELDS_TAX_LOCK_DATE = ['l10n_ec_sri_payment_id']
        # Check the tax lock date.
        if any(self.env['account.move']._field_will_change(self, vals, field_name) for field_name in PROTECTED_FIELDS_TAX_LOCK_DATE):
            self._l10n_ec_check_tax_lock_date()
        return super().write(vals)

    def _l10n_ec_check_tax_lock_date(self):
        for move in self.filtered(lambda x: x.state == 'posted'):
            if move.company_id.tax_lock_date and move.date <= move.company_id.tax_lock_date:
                raise UserError(_("The operation is refused as it would impact an already issued tax statement. "
                                  "Please change the journal entry date or the tax lock date set in the settings (%s) to proceed.")
                                % format_date(self.env, move.company_id.tax_lock_date))
    
    def l10n_ec_add_withhold(self):
        # Launches the withholds wizard linked to selected invoices
        ctx = self._context.copy()
        ctx.update({
            'active_ids': self.ids,
            'active_model': 'account.move',
            })
        # First create the wizard then show on popup, so a real temporary ID is created (instead of a newID)
        # doing this way so the "suggested" wihhold line filters the taxes and invoices by a context  
        new_withhold_wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(ctx).create({})
        return {
            'name': _("Withhold"),
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
                'name': _('Withholding'),
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
            
    def l10n_ec_action_view_invoices(self):
        # Navigate from the withhold to its invoices
        l10n_ec_withhold_origin_ids = self.l10n_ec_withhold_origin_ids.ids
        if len(l10n_ec_withhold_origin_ids) == 1:
            return {
                'name': _('Invoices'),
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': False,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'res_id': l10n_ec_withhold_origin_ids[0],
            }
        else:
            action = 'account.action_move_out_invoice_type'
            if self.l10n_ec_withhold_type == 'in_withhold':                
                action = 'account.action_move_in_invoice_type'
            action = self.env.ref(action)
            result = action.sudo().read()[0]
            result['name'] = _('Invoices')
            result['domain'] = "[('id', 'in', " + str(l10n_ec_withhold_origin_ids) + ")]"            
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
        if self._l10n_ec_is_withholding():
            raise ValidationError(_("You can not duplicate a withhold, instead create a new one from the invoice"))
        return res

    def is_invoice(self, include_receipts=False):
        # OVERRIDE: For Ecuador we consider is_invoice for all edis (invoices and wihtholds, in the future maybe waybills, etc)
        # It enables the send email button, the edi process, the customer portal, printing the qweb report, and other stuff.
        country_code = self.country_code or self.company_id.country_code
        if country_code == 'EC':
            if self._l10n_ec_is_withholding():
                return True
        return super(AccountMove, self).is_invoice(include_receipts)
    
    # def _is_edi_invoice(self, include_receipts=False):
    #     # OVERRIDE: For Ecuador we consider _is_edi_invoice for all edis (invoices and wihtholds, in the future maybe waybills, etc)
    #     # It enables the send email button, the edi process, the customer portal, printing the qweb report, and other stuff.
    #     country_code = self.country_code or self.company_id.country_code
    #     if country_code == 'EC':
    #         if self._l10n_ec_is_withholding():
    #             return True
    #     return super(AccountMove, self)._is_edi_invoice(include_receipts)
    
    def _is_manual_document_number(self):
        # OVERRIDE
        if self.journal_id.company_id.country_id.code == 'EC':
            purchase_liquidation = self.env.context.get('internal_type',
                                                        self.l10n_latam_document_type_id.internal_type) == 'purchase_liquidation'
            return self.journal_id.type == 'purchase' and not purchase_liquidation
        return super()._is_manual_document_number()

    def _get_l10n_ec_identification_type(self):
        # OVERRIDE
        code = super()._get_l10n_ec_identification_type()
        if self._l10n_ec_is_withholding():
            #Codes are the same as for a regular out_invoice, but the is_withholding method don't exist in l10n_ec module
            it_ruc = self.env.ref("l10n_ec.ec_ruc", False)
            it_dni = self.env.ref("l10n_ec.ec_dni", False)
            it_passport = self.env.ref("l10n_ec.ec_passport", False)
            is_final_consumer = verify_final_consumer(self.partner_id.commercial_partner_id.vat)
            is_ruc = self.partner_id.commercial_partner_id.l10n_latam_identification_type_id.id == it_ruc.id
            is_dni = self.partner_id.commercial_partner_id.l10n_latam_identification_type_id.id == it_dni.id
            is_passport = self.partner_id.commercial_partner_id.l10n_latam_identification_type_id.id == it_passport.id
            if is_final_consumer:
                code = "07"
            elif is_ruc:
                code = "04"
            elif is_dni:
                code = "05"
            elif is_passport:
                code = "06"
        # TODO fix l10n_ec function ? Why is there a difference ?
        # https://github.com/odoo/odoo/blob/15.0/addons/l10n_ec/models/account_move.py#L137
        return "08" if code in ("09", "20", "21") else code

    def _get_name_invoice_report(self):
        # EXTENDS account_move
        self.ensure_one()
        if self.l10n_latam_use_documents and self.country_code == 'EC':
            if (self.move_type in ('out_invoice', 'out_refund') and self.l10n_latam_document_type_id.code in ['04', '18', '05', '41']) \
                or (self.move_type in ('in_invoice') and self.l10n_latam_document_type_id.code in ['03', '41']
                    and self.l10n_latam_document_type_id.l10n_ec_authorization == 'own'):
                return 'l10n_ec_edi.report_invoice_document'
        return super(AccountMove, self)._get_name_invoice_report()

    @api.constrains('name', 'journal_id', 'state')
    def _check_unique_sequence_number(self):
        # Exclude sales withhold number as it is issued by the customer
        sale_withhold = self.filtered(lambda x: x.l10n_ec_withhold_type == 'out_withhold' and x.l10n_latam_use_documents)
        return super(AccountMove, self - sale_withhold)._check_unique_sequence_number()
    
    @api.constrains('name', 'partner_id', 'company_id', 'posted_before')
    def _check_unique_vendor_number(self):
        super(AccountMove, self.with_context(l10n_ec_withhold_type=self.l10n_ec_withhold_type))._check_unique_vendor_number() 
    
    def is_purchase_document(self, include_receipts=False):
        # Used in _check_unique_vendor_number: In the context of validating sales withhold number for same partner make it behave like a purchase
        if self._context.get('l10n_ec_withhold_type',False) == 'out_withhold':
            return True
        return super().is_purchase_document(include_receipts = include_receipts)
    
    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount(self):
        #Improves the the computation of purchase withhold to have coherent amounts, these are shown in tree view
        res = super()._compute_amount()
        for move in self.filtered(lambda x: x._l10n_ec_is_withholding()):
            # amount_tax, amount_total, amount_residual should be positive just like in any invoice or refund
            # move.amount_untaxed doesn't need fixing as is always zero for withholds
            move.amount_tax = abs(move.amount_tax)
            move.amount_total = abs(move.amount_total)
            move.amount_residual = abs(move.amount_residual)
            # negative for sale withhold (like an out_refund), positive for purchase withhold (like an in_refund)
            withhold_sign = -1.0 if move.l10n_ec_withhold_type == 'out_withhold' else 1
            move.amount_tax_signed = move.amount_tax * withhold_sign
            move.amount_total_signed = move.amount_total_signed * withhold_sign
            move.amount_residual_signed = move.amount_residual_signed * withhold_sign
            move.amount_total_in_currency_signed = move.amount_total_in_currency_signed * withhold_sign
        return res

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
        if not self._l10n_ec_is_withholding():
            data = {
                "taxes_data": self._l10n_ec_get_taxes_grouped_by_tax_group(),
                "additional_info": {
                    "ref": self.name,
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
        else:
            data = {
                "taxes_data": self._l10n_ec_get_taxes_withhold_grouped(),
                "fiscalperiod": str(self.invoice_date.month).zfill(2) + '/' + str(self.invoice_date.year),
                "additional_info": {
                    "direccion": ' '.join(
                        [value for value in [self.commercial_partner_id.street, self.commercial_partner_id.street2] if
                         value]),
                },
            }
            if self.commercial_partner_id.email:
                data['additional_info']['email'] = self.commercial_partner_id.email
            if self.commercial_partner_id.phone:
                data['additional_info']['telefono'] = self.commercial_partner_id.phone
        return data

    def _l10n_ec_is_withholding(self):  
        is_withholding = False
        country_code = self.country_code or self.company_id.country_code
        if country_code == 'EC' and self.l10n_ec_withhold_type in ('in_withhold', 'out_withhold'):
            is_withholding = True
        return is_withholding

    # ===== PRIVATE =====

    def _l10n_ec_get_taxes_withhold_grouped(self):

        def get_electronic_tax_code(withhold_line):
            """
            Analiza si un codigo de impuesto es de tipo IVA y lo devuelve segun los
            parametros del SRI.
            :return: Devuelve un numero entero del codigo del impuesto.
            """
            code = False
            l10n_ec_type = withhold_line.tax_group_id.l10n_ec_type
            percentage = abs(line.tax_line_id.amount)
            if l10n_ec_type == 'withhold_income_purchase':
                code = withhold_line.tax_line_id.l10n_ec_code_ats
            elif l10n_ec_type == 'withhold_vat_purchase':
                if percentage == 0.0:  # retencion iva 0%
                    code = 7
                elif percentage == 10.0:
                    code = 9
                elif percentage == 20.0:
                    code = 10
                elif percentage == 30.0:
                    code = 1
                elif percentage == 70.0:
                    code = 2
                elif percentage == 100.0:
                    code = 3
            if not code:
                raise ValidationError('Not vat code.' % line.tax_line_id.name)
            return code

        self.ensure_one()
        taxes_data = []
        for line in self.l10n_ec_withhold_line_ids:
            tax_type_code = L10N_EC_WITHHOLD_CODES.get(line.tax_group_id.l10n_ec_type, 6)
            tax_code = get_electronic_tax_code(line)
            taxes_data += [{'codigo': tax_type_code,
                            'codigoretencion': tax_code,
                            'baseimponible': line.tax_base_amount,
                            'porcentajeretener': line.tax_line_id.amount,
                            'valorretenido': line.balance,
                            'coddocsustento': line.l10n_ec_withhold_invoice_id.l10n_latam_document_type_id_code,
                            'numdocsustento': line.l10n_ec_withhold_invoice_id.l10n_latam_document_number.replace('-', ''),
                            'fechaemisiondocsustento': line.l10n_ec_withhold_invoice_id.invoice_date.strftime("%d/%m/%Y")}]
        return taxes_data

    def _l10n_ec_get_taxes_grouped_by_tax_group(self, exclude_withholding=True):
        self.ensure_one()

        def filter_withholding_taxes(tax_values):
            group_iva_withhold = self.env.ref("l10n_ec.tax_group_withhold_vat")
            group_rent_withhold = self.env.ref("l10n_ec.tax_group_withhold_income")
            withhold_group_ids = (group_iva_withhold + group_rent_withhold).ids
            return tax_values["tax_id"].tax_group_id.id not in withhold_group_ids

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
            filter_to_apply=filter_withholding_taxes,
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
    
    def _l10n_ec_show_add_withhold(self):
        # shows/hide "ADD WITHHOLD" button on invoices
        # TODO: Trescloud finish polishing the scenarios for showing the withhold button
        for invoice in self:
            result = False
            codes_to_withhold = [
                '01', # factura compra
                '02', # Nota de venta
                '03', # liquidacion compra
                '08', # Entradas a espectaculos
                '09', # Tiquetes
                '18', # Factura de Venta
                '11', # Pasajes
                '12', # Inst FInancieras
                '20', # Estado
                '21', # Carta porte aereo
                '47', # Nota de crédito de reembolso
                '48', # Nota de débito de reembolso
                ]
            invoice.l10n_ec_show_add_withhold = invoice.country_code == 'EC' and invoice.state == 'posted' and invoice.l10n_latam_document_type_id.code in codes_to_withhold
    
    @api.depends('line_ids')
    def _compute_l10n_ec_withhold_ids(self):
        for move in self:
            if move._l10n_ec_is_withholding(): #fields related to a withhold entry
                move.l10n_ec_withhold_line_ids = move.line_ids.filtered(lambda l: l.tax_line_id)
                move.l10n_ec_withhold_origin_ids = move.line_ids.mapped('l10n_ec_withhold_invoice_id') #also removes duplicates
                move.l10n_ec_withhold_origin_count = len(move.l10n_ec_withhold_origin_ids)
            elif move.is_invoice(): #fields related to an invoice entry
                move.l10n_ec_withhold_ids = self.env['account.move.line'].search([('l10n_ec_withhold_invoice_id', '=', move.id)]).mapped('move_id')
                move.l10n_ec_withhold_count = len(move.l10n_ec_withhold_ids)

    # ===== PRIVATE (static) =====

    @api.model
    def _l10n_ec_remove_forbidden_chars(self, s, max_len=300):
        return "".join("".join(x) for x in re_compile(r'([A-Z]|[a-z]|[0-9]|ñ|Ñ)+([\w]|[\S]|[^\n])*').findall(s))[:max_len]

    def _l10n_ec_get_invoice_total_for_reports(self):
        self.ensure_one()
        tax_types = ('vat12', 'vat14', 'zero_vat', 'irbpnr')
        tax_group_lines = self.line_ids.filtered(lambda line: line.tax_group_id and line.tax_group_id.l10n_ec_type in tax_types)
        return self.amount_untaxed + sum(line.price_subtotal for line in tax_group_lines)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ec_withhold_invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        ondelete='restrict',
        help='Link the withholding line to its invoice'
    )


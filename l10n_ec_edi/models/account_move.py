# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import compile as re_compile

from odoo import _, api, fields, models

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
            group_iva_withhold = self.env.ref("l10n_ec.tax_group_withhold_vat")
            group_rent_withhold = self.env.ref("l10n_ec.tax_group_withhold_income")
            withhold_group_ids = (group_iva_withhold + group_rent_withhold).ids
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

    # ===== PRIVATE (static) =====

    @api.model
    def _l10n_ec_remove_forbidden_chars(self, s, max_len=300):
        return "".join("".join(x) for x in re_compile(r'([A-Z]|[a-z]|[0-9]|ñ|Ñ)+([\w]|[\S]|[^\n])*').findall(s))[:max_len]

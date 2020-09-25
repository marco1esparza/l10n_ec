# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare


class AccountMove(models.Model):
    _inherit='account.move'

    @api.onchange("partner_id","fiscal_position_id","l10n_latam_document_type_id",
                  "l10n_ec_fiscal","l10n_ec_payment_method_id")
    def _l10n_ec_onchange_tax_dependecies(self):
        #triger recompute of profit withhold for purchase invoice
        #TODO: Recompute separately profit withhold and vat withhold
        self.ensure_one()
        res = {}
        if not self.state == 'draft' or not self.type == 'in_invoice':
            return res
        for line in self.invoice_line_ids:
            taxes = line._get_computed_taxes()
            #line.tax_ids = [(6, 0, taxes.ids)]
            line.tax_ids = taxes
        return res

class AccountMoveLine(models.Model):
    _inherit='account.move.line'

    def _get_computed_taxes(self):
        '''
        For purchases adds prevalence for tax mapping to ease withholds in Ecuador, in the following order:
        For profit withholding tax:
        - If payment type == credit card then withhold code 332G, if not then
        - partner_id.l10n_ec_force_profit_withhold, if not set then
        - product_id profit withhold, if not set then
        - company fallback profit withhold for goods or for services
        For vat withhold tax:
        - If product is consumable then l10n_ec_vat_withhold_goods
        - If product is services or not set then l10n_ec_vat_withhold_services
        If withholds doesn't apply to the document type then remove the withholds  
        '''
        super_tax_ids = super(AccountMoveLine, self)._get_computed_taxes()
                
        vat_withhold_tax = False
        profit_withhold_tax = False
        if self.move_id.l10n_latam_country_code == 'EC':
            if self.move_id.is_purchase_document(include_receipts=True):
                if not self.exclude_from_invoice_tab: #just regular invoice lines
                    if self.move_id.l10n_latam_document_type_id.l10n_ec_apply_withhold: #compute withholds

                        company_id = self.move_id.company_id
                        fiscal_postition_id = self.move_id.fiscal_position_id
                        tax_groups = super_tax_ids.mapped('tax_group_id').mapped('l10n_ec_type')

                        #compute vat withhold
                        if 'vat12' in tax_groups or 'vat14' in tax_groups:
                            if not self.product_id or self.product_id.type in ['consu']:
                                vat_withhold_tax = fiscal_postition_id.l10n_ec_vat_withhold_goods
                            else: #services
                                vat_withhold_tax = fiscal_postition_id.l10n_ec_vat_withhold_services
                        #compute profit withhold
                        if self.move_id.l10n_ec_payment_method_id.code in ['16','18','19']:
                            #payment with debit card, credit card or gift card retains 0%
                            profit_withhold_tax = company_id.l10n_ec_profit_withhold_tax_credit_card
                        elif self.partner_id.property_l10n_ec_profit_withhold_tax_id:
                            profit_withhold_tax = self.partner_id.property_l10n_ec_profit_withhold_tax_id
                        elif 'withhold_income_tax' in tax_groups:
                            pass #keep the taxes coming from product.product... for now
                        else: #if not any withhold tax then fallback
                            if self.product_id and self.product_id.type == 'service':
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_services
                            else:
                                profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_goods
                    else: #remove withholds
                        super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat','withhold_income_tax'])
            if vat_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_vat'])
                super_tax_ids += vat_withhold_tax
            if profit_withhold_tax:
                super_tax_ids = super_tax_ids.filtered(lambda tax: tax.tax_group_id.l10n_ec_type not in ['withhold_income_tax'])
                super_tax_ids += profit_withhold_tax
        return super_tax_ids
    

    
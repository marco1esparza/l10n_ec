# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round
from datetime import date
import calendar


class L10nEcWizardAccountWithhold(models.TransientModel):
    _name = 'l10n_ec.wizard.account.withhold'
    _check_company_auto = True

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        check_company=True
    )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Document Type'
    )
    l10n_latam_document_number = fields.Char(
        string='Document Number',
    )
    l10n_latam_manual_document_number = fields.Boolean(
        compute='_compute_l10n_latam_manual_document_number',
        string='Manual Number'
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        help=''
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        help='Technical field used to filter the available journals'
    )
    available_taxes = fields.Many2many(
        'account.tax',
        'l10n_ec_account_invoice_taxes_rel',
        'tax_id',
        'invoice_id',
        string='Taxes',
        help='Technical field to limit elegible taxes related to this withhold'
    )
    related_invoices = fields.Many2many(
        'account.move',
        'l10n_ec_account_invoice_withhold_rel',
        'withhold_id',
        'invoice_id',
        string='Invoices',
        help='Technical field to limit elegible invoices related to this withhold'
    )
    withhold_type = fields.Selection(
        [('out_withhold', 'Sales Withhold'),
         ('in_withhold', 'Purchase Withhold')],
        string='Withhold Type',
        help='Technical field to limit elegible journals and taxes'
    )
    withhold_line_ids = fields.One2many(
        'l10n_ec.wizard.account.withhold.line',
        'wizard_id',
        string='Withhold Lines'
    )
    # Subtotals
    currency_id = fields.Many2one(
        string='Company Currency',
        readonly=True,
        related='company_id.currency_id'
    )
    l10n_ec_withhold_vat_amount = fields.Monetary(
        compute='_compute_withhold_totals',
        string='VAT Withhold',
        readonly=True,
        help='The total amount of withhold over VAT'
    )
    l10n_ec_withhold_profit_amount = fields.Monetary(
        compute='_compute_withhold_totals',
        string='Profit Withhold',
        readonly=True,
        help='The total amount of withhold over profits'
    )
    l10n_ec_withhold_vat_base = fields.Monetary(
        compute='_compute_withhold_totals',
        string='VAT Withhold Base',
        readonly=True,
        help='The total vat base amount affected by the taxes in this withhold'
    )
    l10n_ec_withhold_profit_base = fields.Monetary(
        compute='_compute_withhold_totals',
        string='Profit Withhold Base',
        readonly=True,
        help='The total profit base amount affected by the taxes in this withhold'
    )
    l10n_ec_withhold_total_amount = fields.Monetary(
        string='Withhold Total',
        compute='_compute_withhold_totals',
        readonly=True,
        help='The total value of the withhold, this value will be reconciled with the older invoice'
    )
    l10n_ec_related_invoices_count = fields.Integer(
        string='Related Invoice Count',
        compute='_compute_related_invoices_count',
        readonly=True,
        help='Number of invoices related to withholding'
    )
    
    @api.model
    def default_get(self, data_fields):
        res = {}
        invoice_ids = self.env.context.get('active_ids', False)
        if not invoice_ids or not self.env.context.get('active_model') == 'account.move':
            return res
        invoices = self.env['account.move'].search([('id', 'in', invoice_ids)])
        self._validate_invoices_data(invoices)
        default_values = self._prepare_withhold_wizard_default_values(invoices)
        res.update(default_values)
        return res
    
    def _prepare_withhold_wizard_default_values(self, invoices):
        #Computes new withhold data for provided invoices
        if invoices[0].move_type == 'in_invoice':
            withhold_type = 'in_withhold'
        elif invoices[0].move_type == 'out_invoice':
            withhold_type = 'out_withhold'
        withhold_journal = self.env['account.journal'].search([
            ('l10n_ec_withhold_type', '=', withhold_type),
            ('company_id', '=', invoices[0].company_id.id),
            ], order="sequence asc", limit=1)
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([
            ('country_id.code', '=', 'EC'),
            ('internal_type', '=', 'withhold'),
            ], order="sequence asc", limit=1)
        taxes = self.env['account.tax']
        if withhold_type == 'in_withhold':
            taxes = self.env['account.tax'].search([('company_id', '=', invoices[0].company_id.id),('tax_group_id.l10n_ec_type', 'in', ['withhold_vat_purchase', 'withhold_income_purchase'])])
        elif withhold_type == 'out_withhold':
            taxes = self.env['account.tax'].search([('company_id', '=', invoices[0].company_id.id),('tax_group_id.l10n_ec_type', 'in', ['withhold_vat_sale', 'withhold_income_sale'])])
        default_values = {
            'journal_id': withhold_journal and withhold_journal.id,
            'l10n_latam_document_type_id': l10n_latam_document_type_id and l10n_latam_document_type_id.id,
            'date': fields.Date.context_today(self),
            'withhold_type': withhold_type,
            'available_taxes': [(6, 0, taxes.ids)],
            'related_invoices': [(6, 0, invoices.ids)],
            'company_id': invoices[0].company_id.id,
            }
        if withhold_type == 'in_withhold':
            withhold_line_ids = []
            group_taxes = {}
            for invoice in invoices:
                for line in invoice.invoice_line_ids.filtered(lambda line: not line.display_type):
                    withhold_taxes = self._get_suggested_supplier_withhold_taxes(line)
                    for tax in withhold_taxes:
                        tax_line = tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
                        group_taxes.setdefault(tax.id, [{}, 0, 0])
                        if tax.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase']:
                            group_taxes[tax.id][0].update({
                                'account_id': tax_line.account_id.id,
                                'invoice_id': invoice.id
                            })
                            group_taxes[tax.id][1] += line.debit
                            group_taxes[tax.id][2] += abs(line.debit * tax.amount / 100)
                        if tax.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
                            group_taxes[tax.id][0].update({
                                'account_id': tax_line.account_id.id,
                                'invoice_id': invoice.id
                            })
                            group_taxes[tax.id][1] += line.price_total - line.price_subtotal
                            group_taxes[tax.id][2] += abs((line.price_total - line.price_subtotal) * tax.amount / 100)
            prec = invoices[0].company_id.currency_id.decimal_places
            for tax_id, detail in group_taxes.items():
                withhold_line_ids.append((0, 0, {
                    'tax_id': tax_id,
                    'account_id': detail[0].get('account_id'),
                    'invoice_id': detail[0].get('invoice_id'),
                    'base': float_round(detail[1], precision_digits=prec),
                    'amount': float_round(detail[2], precision_digits=prec)
                }))
            default_values.update({
                'withhold_line_ids': withhold_line_ids
                })
        elif withhold_type == 'out_withhold':
            withhold_line_ids = []
            for invoice in invoices:
                withhold_line_ids.append((0, 0, {
                    'tax_id': False,
                    'account_id': False,
                    'invoice_id': invoice.id,
                    'base': 0.0,
                    'amount': 0.0
                }))
            default_values.update({
                'withhold_line_ids': withhold_line_ids
                })
        return default_values
    
    @api.model
    def _get_suggested_supplier_withhold_taxes(self, line):
        '''
        For purchases adds prevalence for tax mapping to ease withholds in Ecuador, in the following order:
        - If payment type == credit card then only use withhold code 332G, else:
        For profit withholding tax:
        - partner_id.l10n_ec_force_profit_withhold, if not set then
        - product_id profit withhold, if not set then
        - company fallback profit withhold for goods or for services
        For vat withhold tax:
        - If product is consumable then vat_goods_withhold_tax_id
        - If product is services or not set then vat_services_withhold_tax_id
        '''
        vat_withhold_tax = self.env['account.tax'] #empty recordset
        profit_withhold_tax = self.env['account.tax'] #empty recordset
        company_id = line.move_id.company_id
        contributor_type = line.move_id.commercial_partner_id.l10n_ec_contributor_type_id
        product_type = 'services' #it includes service, event, course and others
        if line.product_id.type in ['consu', 'product']:
            produt_type = 'goods'
        # override all withholds on payments with credit card, debit card or gift card
        if line.move_id.l10n_ec_sri_payment_id.code in ['16', '18', '19']:
            profit_withhold_tax = company_id.l10n_ec_profit_withhold_tax_credit_card
            return profit_withhold_tax
        # compute profit withhold
        if contributor_type.profit_withhold_tax_id:
            profit_withhold_tax = contributor_type.profit_withhold_tax_id
        elif line.product_id.l10n_ec_withhold_tax_id:
            profit_withhold_tax = line.product_id.l10n_ec_withhold_tax_id
        elif product_type == 'services':
            profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_services
        elif product_type == 'goods':
            profit_withhold_tax = company_id.l10n_ec_fallback_profit_withhold_goods
        # compute vat withhold
        tax_groups = line.tax_ids.mapped('tax_group_id').mapped('l10n_ec_type') 
        if 'vat08' in tax_groups or 'vat12' in tax_groups or 'vat14' in tax_groups:
            if product_type == 'services':
                vat_withhold_tax = contributor_type.vat_services_withhold_tax_id
            else: #goods
                vat_withhold_tax = contributor_type.vat_goods_withhold_tax_id
        return vat_withhold_tax + profit_withhold_tax
    
    def action_create_and_post_withhold(self):
        self._validate_invoices_data(self.related_invoices)
        self._validate_withhold_data_on_post()
        withhold = self._create_move_header()
        self._create_move_lines(withhold)
        withhold._post(soft=False)
        self._reconcile_withhold_vs_invoices(withhold, self.related_invoices)
        #TODO Review with Odoo, maybe no need to return the move form as it is already linked in payment widget (similar to payments)
        return self.related_invoices.with_context(withhold=withhold.ids).l10n_ec_action_view_withholds()
    
    def _create_move_header(self):
        origins = []
        invoices = self.withhold_line_ids.mapped('invoice_id')
        for invoice in invoices:
            origin = invoice.name
            if invoice.invoice_origin:
                origin += ';' + invoice.invoice_origin
            origins.append(origin)
        withhold_origin = ','.join(origins)
        to_withhold_name = ", ".join(invoices.mapped('name'))
        withhold_ref = _('Withhold on: %s') % to_withhold_name
        partner_id = invoices[-1].partner_id #the contact from latest invoice
        accounting_date = self.date
        invoice_date = invoices[0].invoice_date
        last_day_of_month = calendar.monthrange(invoice_date.year, invoice_date.month)[1]
        last_date_in_withhold = date(invoice_date.year, invoice_date.month, last_day_of_month)
        if accounting_date > last_date_in_withhold:
            accounting_date = last_date_in_withhold
        vals = {
            'date': accounting_date,
            'invoice_date': self.date,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'partner_id': partner_id,
            'invoice_payment_term_id': None, #to avoid accidents
            'move_type': 'entry',
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': self.l10n_latam_document_number,
            'l10n_ec_withhold_type': self.withhold_type,
            'invoice_origin': withhold_origin,
            'ref': withhold_ref, #TODO: review with Odoo, seems the Odoo way but might take too much space on the screen
        }
        withhold = self.env['account.move'].create(vals)
        return withhold
    
    def _create_move_lines(self, withhold):
        lines = self.env['account.move.line'] #empty recordset
        total = 0.0
        for line in self.withhold_line_ids:
            # 1. Create the withhold line
            nice_tax_label_elements = []
            if line.tax_id.l10n_ec_code_applied:
                nice_tax_label_elements.append(line.tax_id.l10n_ec_code_applied)
            nice_tax_label_elements.append("{:.2f}".format(abs(line.tax_id.amount))+"%")
            nice_tax_label_elements.append(line.invoice_id.name)
            nice_tax_label = ", ".join(nice_tax_label_elements)
            
            tax_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda x:x.repartition_type == 'tax')
            vals_tax_line = {
                'name': 'Ret: ' + nice_tax_label,
                'move_id': withhold.id,
                'partner_id': withhold.partner_id.commercial_partner_id.id,
                'account_id': line.account_id.id,
                'quantity': 1.0,
                'price_unit': line.amount,
                'debit': line.amount if withhold.l10n_ec_withhold_type == 'out_withhold' else 0.0,
                'credit': line.amount if withhold.l10n_ec_withhold_type == 'in_withhold' else 0.0,
                'tax_base_amount': line.base,
                'tax_line_id': line.tax_id.id, #originator tax
                'tax_repartition_line_id': tax_line.id,
                'tax_tag_ids': [(6, 0, tax_line.tag_ids.ids)],
                'tax_tag_invert': withhold.l10n_ec_withhold_type == 'in_withhold',
                'exclude_from_invoice_tab': True,
                'is_rounding_line': False,
                'date_maturity': False,
                'l10n_ec_withhold_invoice_id': line.invoice_id.id,
            }
            move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals_tax_line)
            total += line.amount
            
            # 2. Create the tax base line and its counterpart
            # For profit withhold on purchases we need to add the base in a separate line for tax report 103
            # We do the same for other taxes for homogeneity
            nice_base_label_elements = []
            if line.tax_id.l10n_ec_code_base:
                nice_base_label_elements.append(line.tax_id.l10n_ec_code_base)
            nice_base_label_elements.append("{:.2f}".format(abs(line.tax_id.amount))+"%")
            nice_base_label_elements.append(line.invoice_id.name)
            nice_base_label = ", ".join(nice_base_label_elements)
            
            base_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda x:x.repartition_type == 'base')
            vals_base_line = {
                'name': 'Base Ret: ' + nice_base_label,
                'move_id': withhold.id,
                'partner_id': withhold.partner_id.commercial_partner_id.id,
                'account_id': line.account_id.id,
                'quantity': 1.0,
                'price_unit': line.base,
                'debit': line.base if withhold.l10n_ec_withhold_type == 'out_withhold' else 0.0,
                'credit': line.base if withhold.l10n_ec_withhold_type == 'in_withhold' else 0.0,
                'tax_base_amount': 0.0,
                'tax_ids': [(6, 0, line.tax_id.ids)],
                'tax_tag_ids': [(6, 0, base_line.tag_ids.ids)],
                'tax_tag_invert': withhold.l10n_ec_withhold_type == 'in_withhold',
                'exclude_from_invoice_tab': True,
                'is_rounding_line': False,
                'date_maturity': False,
                'l10n_ec_withhold_invoice_id': line.invoice_id.id,
            }
            move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals_base_line)
            vals_base_line_counterpart = { # Pretty much the same but inverted and with no tax
                'name': 'Base Ret Cont: ' + nice_base_label,
                'move_id': withhold.id,
                'partner_id': withhold.partner_id.commercial_partner_id.id,
                'account_id': line.account_id.id,
                'quantity': 1.0,
                'price_unit': line.base,
                'debit': line.base if withhold.l10n_ec_withhold_type == 'in_withhold' else 0.0,
                'credit': line.base if withhold.l10n_ec_withhold_type == 'out_withhold' else 0.0,
                'tax_base_amount': 0.0, 
                'exclude_from_invoice_tab': True,
                'is_rounding_line': False,
                'date_maturity': False,
                'l10n_ec_withhold_invoice_id': line.invoice_id.id,
            }
            move_line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals_base_line_counterpart)
        
        # 3. Payable/Receivable line
        # TODO: Discuss with Odoo, perhaps make one payable entry per linked invoice?
        vals = {
            'name': '',
            'move_id': withhold._origin.id,
            'partner_id': withhold.partner_id.commercial_partner_id.id,
            'account_id': self._get_partner_account(withhold.partner_id, withhold.l10n_ec_withhold_type).id,
            'quantity': 1.0,
            'price_unit': total,
            'debit': total if withhold.l10n_ec_withhold_type == 'in_withhold' else 0.0,
            'credit': total if withhold.l10n_ec_withhold_type == 'out_withhold' else 0.0,
            'tax_base_amount': 0.0,
            'is_rounding_line': False,
            'date_maturity': False,
            'exclude_from_invoice_tab': True,
        }
        line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals)
    
    @api.model
    def _validate_invoices_data(self, invoices):
        # Let's test the source invoices for missuse before showing the withhold wizard
        MAP_INVOICE_TYPE_PARTNER_TYPE = {
            'out_invoice': 'customer',
            'out_refund': 'customer',
            'in_invoice': 'supplier',
            'in_refund': 'supplier',
        }
        for invoice in invoices:
            if invoice.state not in ['posted']:
                raise ValidationError(_("Can not create a withhold, the document %s is not yet posted", invoice.name))
            if invoice.commercial_partner_id != invoices[0].commercial_partner_id:
                raise ValidationError(
                    _("Some documents belong to different partners, please correct the document %s", invoice.name))
            if MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type]:
                raise ValidationError(
                    _("Can't mix supplier and customer documents in the same withhold, please correct the document %s.", invoice.name))
            if invoice.currency_id != invoice.company_id.currency_id:
                raise ValidationError(
                    _("The withhold currency and the invoices currencies should be the same, review invoice %s", invoice.name))
            if len(invoices) > 1 and invoice.move_type == 'in_invoice':
                # Current MVP allows supplier withhold over one single supplier invoice
                # Future versions might allow several withholds per purchase invoice and on several purchase invoces at a time (similar to sales) 
                raise ValidationError(
                    _("At the moment withholds over multiple invoices are only supported in customer withholds"))
            if not invoice.l10n_ec_show_add_withhold:
                raise ValidationError(
                    _("The selected document type does not support withholds, please check the document %s", invoice.name))
                
    def _validate_withhold_data_on_post(self):
        # Validations that apply only on withhold post, other validations should be method _validate_invoices_data()
        if not self.withhold_line_ids:
            raise ValidationError(_("You must input at least one withhold line"))
        related_withholds = self.related_invoices.l10n_ec_withhold_ids.filtered(lambda x: x.state == 'posted' and x.id != self.id)
        if related_withholds and self.withhold_type == 'in_withhold':
            # Current MVP allows just one withhold (no matter vat or profit) per supplier invoice
            # Future versions might allow several withholds per purchase invoice and on several purchase invoces at a time (similar to sales) 
            raise ValidationError(_("Another withhold already exists, you can have only one posted withhold per purchase document"))
        # Validate there where not other withholds for same invoice for same concept (concept might be vat withhold or income withhold)
        current_categories = self.withhold_line_ids.tax_id.tax_group_id.mapped('l10n_ec_type')
        for previous_withhold_line in related_withholds.l10n_ec_withhold_line_ids:
            previous_category = previous_withhold_line.tax_line_id.tax_group_id.l10n_ec_type
            if previous_category in current_categories:
                raise ValidationError(_("Error, another withhold already exists for %s, withhold number %s" % (previous_category, previous_withhold_line.move_id.name)))
        error = ''
        invoice_list = []
        amount_total = 0.0
        for invoice in self.related_invoices:
            total_base_vat = 0.0
            vat_lines = self.withhold_line_ids.filtered(lambda withhold_line: withhold_line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase'] and withhold_line.invoice_id == invoice)
            for vat_line in vat_lines:
                total_base_vat += vat_line.base
            precision = invoice.company_id.currency_id.decimal_places
            (vat_base, vat_amount) = self.env['l10n_ec.wizard.account.withhold.line']._get_invoice_vat_base_and_amount(invoice)
            diff_base_vat = float_compare(total_base_vat, vat_amount, precision_digits=precision)
            if diff_base_vat > 0:
                raise ValidationError(_("The VAT base amount on the withhold should not be higher to the VAT value on the invoice %s", invoice.l10n_latam_document_number))
            total_base_profit = 0.0
            profit_lines = self.withhold_line_ids.filtered(lambda withhold_line: withhold_line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase'] and withhold_line.invoice_id == invoice)
            for profit_line in profit_lines:
                total_base_profit += profit_line.base
            diff_base_profit = float_compare(total_base_profit, invoice.amount_untaxed, precision_digits=precision)
            if diff_base_profit > 0:
                raise ValidationError(_("The profit base amount on the withhold should not be higher to the subtotal on the invoice %s", invoice.l10n_latam_document_number))
            if self.date < invoice.invoice_date:
                invoice_list.append(invoice.name)
            amount_total += invoice.amount_total
        if invoice_list:
            joined_vals = '\n'.join('* ' + l for l in invoice_list)
            error += _("Following invoices has a later date than the withhold, fix the dates:\n%s\n", joined_vals)        
        if self.l10n_ec_withhold_total_amount > amount_total:
            error += _("The withhold amount is bigger than the total amount of the invoices")
        if error:
            raise ValidationError(error)
    
    @api.model
    def _reconcile_withhold_vs_invoices(self, withhold, related_invoices):
        #reconciles the withhold against the invoice, pays older open invoice first
        partner_id = related_invoices[0].partner_id.commercial_partner_id
        if withhold.l10n_ec_withhold_type in ['out_withhold']:
            (withhold + related_invoices).line_ids.filtered(lambda line: not line.reconciled and line.account_id == self._get_partner_account(partner_id, withhold.l10n_ec_withhold_type)).reconcile()
        elif withhold.l10n_ec_withhold_type in ['in_withhold']:
            (withhold + related_invoices).line_ids.filtered(lambda line: not line.reconciled and line.account_id == self._get_partner_account(partner_id, withhold.l10n_ec_withhold_type)).reconcile()
            
    def _get_partner_account(self, partner, withhold_type):
        partner = partner.with_company(self.company_id)
        account = self.env['account.account']
        if withhold_type in ['out_withhold']:
            account = partner.property_account_receivable_id
        elif withhold_type in ['in_withhold']:
            account = partner.property_account_payable_id
        return account
    
    @api.depends('journal_id', 'l10n_latam_document_type_id')
    def _compute_l10n_latam_manual_document_number(self):
        self.l10n_latam_manual_document_number = False
        if self.journal_id and self.journal_id.l10n_latam_use_documents and self.l10n_latam_document_type_id:
            if self.journal_id.l10n_ec_withhold_type == 'out_withhold':
                # customer withhold number is provided by the customer
                self.l10n_latam_manual_document_number = True
            elif self.journal_id.l10n_ec_withhold_type == 'in_withhold':
                # manual when there are not any posted entry with journal
                count = self.env['account.move'].search_count([
                    ('journal_id', '=', self.journal_id.id),
                    ('l10n_latam_document_type_id', '=', self.l10n_latam_document_type_id.id),
                    ('state', 'in', ['posted','cancel'])
                    ])
                self.l10n_latam_manual_document_number = True if not bool(count) else False
                
    @api.depends('withhold_line_ids')
    def _compute_withhold_totals(self):
        for wizard in self:
            l10n_ec_withhold_vat_amount = 0.0
            l10n_ec_withhold_profit_amount = 0.0
            l10n_ec_withhold_vat_base = 0.0
            l10n_ec_withhold_profit_base = 0.0
            for line in wizard.withhold_line_ids:
                if line.tax_id.tax_group_id:
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
                        l10n_ec_withhold_vat_amount += line.amount
                        l10n_ec_withhold_vat_base += line.base
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase']:
                        l10n_ec_withhold_profit_amount += line.amount
                        l10n_ec_withhold_profit_base += line.base
            wizard.l10n_ec_withhold_vat_amount = l10n_ec_withhold_vat_amount
            wizard.l10n_ec_withhold_profit_amount = l10n_ec_withhold_profit_amount
            wizard.l10n_ec_withhold_vat_base = l10n_ec_withhold_vat_base
            wizard.l10n_ec_withhold_profit_base = l10n_ec_withhold_profit_base
            wizard.l10n_ec_withhold_total_amount = l10n_ec_withhold_vat_amount + l10n_ec_withhold_profit_amount
            
    @api.depends('related_invoices')
    def _compute_related_invoices_count(self):
        for wizard in self:
            wizard.l10n_ec_related_invoices_count = len(wizard.related_invoices.ids)


class L10nEcWizardAccountWithholdLine(models.TransientModel):
    _name = 'l10n_ec.wizard.account.withhold.line'

    tax_id = fields.Many2one(
        'account.tax',
        string='Tax'
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice'
    )

    account_id = fields.Many2one(
        'account.account',
        string='Account'
    )

    account_id = fields.Many2one(
        'account.account',
        string='Account',
        domain="[('deprecated', '=', False), ('company_id', '=', 'company_id'),('is_off_balance', '=', False)]",
        check_company=True
    )
    base = fields.Monetary(
        string='Base'
    )

    amount = fields.Monetary(
        string='Amount'
    )

    company_id = fields.Many2one(
        related='wizard_id.company_id'
    )

    currency_id = fields.Many2one(
        related='company_id.currency_id'
    )

    wizard_id = fields.Many2one(
        'l10n_ec.wizard.account.withhold',
        string='Wizard',
        required=True,
        readonly=True,
        auto_join=True,
        help='The move of this entry line.'
    )
    
    @api.model
    def default_get(self, default_fields):
        #sets the invoice_id when there is only one invoice
        default_invoice_id = self._context.get('default_invoice_id')
        if not default_invoice_id and self._context.get('related_invoices'):
            invoice_ids = self._context.get('related_invoices')[0][2]
            if invoice_ids and len(invoice_ids)==1:
                default_invoice_id = invoice_ids[0]
        contextual_self = self.with_context(default_invoice_id=default_invoice_id)
        return super(L10nEcWizardAccountWithholdLine, contextual_self).default_get(default_fields)

    @api.onchange('invoice_id', 'tax_id')
    def _onchange_invoice_id(self):
        #Suggest a "base amount" according to linked invoice_id and tax type
        base = 0.0
        if self.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
            (vat_base, vat_amount) = self._get_invoice_vat_base_and_amount(self.invoice_id)
            base = vat_amount
        elif self.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase']:
            base = self.invoice_id.amount_untaxed
        self.base = base
    
    @api.onchange('base', 'tax_id')
    def _onchange_base(self):
        # Recomputes amount according to "base amount" and tax percentage
        amount = self.base * abs(self.tax_id.amount) / 100
        accounts = self.tax_id.invoice_repartition_line_ids.mapped('account_id')
        account_id = accounts[0].id if accounts else False
        self.write({
            'account_id': account_id,
            'amount': amount
            })
    
    @api.constrains('base', 'amount')
    def _check_amount(self):
        for line in self:            
            precision = self.currency_id.decimal_places
            if float_compare(line.amount, 0.0, precision_digits=precision) < 0:
                raise ValidationError(_("Negative values ​​are not allowed in amount for withhold lines"))
            if float_compare(line.base, 0.0, precision_digits=precision) < 0:
                raise ValidationError(_("Negative or zero values ​​are not allowed in base for withhold lines"))
    
    @api.model
    def _get_invoice_vat_base_and_amount(self, invoice):
        l10n_ec_vat_base = 0.0
        l10n_ec_vat_amount = 0.0
        for move_line in invoice.line_ids:
            if move_line.tax_group_id:
                if move_line.tax_group_id.l10n_ec_type in ['vat8','vat12', 'vat14']:
                    l10n_ec_vat_base += move_line.tax_base_amount
                    l10n_ec_vat_amount += move_line.price_subtotal
        return l10n_ec_vat_base, l10n_ec_vat_amount
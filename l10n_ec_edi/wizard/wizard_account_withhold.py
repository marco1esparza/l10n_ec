# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round


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
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        help=''
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help=''
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
    l10n_ec_vat_withhold = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total IVA',
        tracking=True,
        store=False,
        readonly=True,
        help='Total IVA value of withhold'
    )
    l10n_ec_profit_withhold = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total RENTA',
        tracking=True,
        store=False,
        readonly=True,
        help='Total renta value of withhold'
    )
    l10n_ec_total_base_vat = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total Base IVA',
        tracking=True,
        store=False,
        readonly=True,
        help='Total base IVA of withhold'
    )
    l10n_ec_total_base_profit = fields.Monetary(
        compute='_l10n_ec_compute_move_totals',
        string='Total Base RENTA',
        tracking=True,
        store=False,
        readonly=True,
        help='Total base renta of withhold'
    )
    l10n_ec_total = fields.Monetary(
        string='Total Withhold',
        compute='_l10n_ec_compute_move_totals',
        tracking=True,
        store=False,
        readonly=True,
        help='Total value of withhold'
    )
    
    @api.model
    def default_get(self, data_fields):
        res = {}
        invoice_ids = self.env.context.get('active_ids', False)
        if not invoice_ids or not self.env.context.get('active_model') == 'account.move':
            return res
        self._validate_invoices_data()
        invoices = self.env['account.move'].search([('id', 'in', invoice_ids)])
        default_values = self._prepare_withold_wizard_default_values(invoices)
        res.update(default_values)
        return res
    
    def _prepare_withold_wizard_default_values(self, invoices):
        #Computes new withhold data for provided invoices
        if invoices[0].move_type == 'in_invoice':
            withhold_type = 'in_withhold'
        elif invoices[0].move_type == 'out_invoice':
            withhold_type = 'out_withhold'
        #TODO V15.2, luego de fusionar con Odoo, para compras, debemos preferir el punto de emision que coincida con la factura
        withhold_journal = self.env['account.journal'].search([
            ('l10n_ec_withhold_type', '=', withhold_type),
            ], order="sequence asc", limit=1)
        l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([
            ('country_id.code', '=', 'EC'),
            ('l10n_ec_type', '=', withhold_type),
            ], order="sequence asc", limit=1)
        default_values = {
            'journal_id': withhold_journal and withhold_journal.id,
            'l10n_latam_document_type_id': l10n_latam_document_type_id and l10n_latam_document_type_id.id,
            'date': fields.Date.context_today(self),
            'withhold_type': withhold_type,
            'related_invoices': [(6, 0, invoices.ids)],
            'company_id': invoices[0].company_id.id,
            }
        if withhold_type == 'in_withhold':
            withhold_line_ids = []
            group_taxes = {}
            for invoice in invoices:
                for line in invoice.line_ids:
                    tax = line._l10n_ec_get_computed_taxes()
                    if tax:
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
    
    def action_create_and_post_withhold(self):
        self._validate_invoices_data()
        self._validate_withhold_data_on_post()
        origins = []
        for invoice in self.related_invoices:
            origin = invoice.name #Usamos name en lugar del l10n_latam_document_number para aprovechar el prefijo del tipo de doc
            if invoice.invoice_origin:
                origin += ';' + invoice.invoice_origin
            origins.append(origin)
        origin = ','.join(origins)
        vals = {
            'invoice_date': self.date,
            'journal_id': self.journal_id.id,
            'invoice_payment_term_id': None, #to avoid accidents
            'move_type': 'entry',
            'line_ids': [(5, 0, 0)],
            'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
            'l10n_latam_document_number': self.l10n_latam_document_number,
            'l10n_ec_withhold_type': self.withhold_type,
            'invoice_origin': origin
        }
        invoice = self.related_invoices[0]
        invoice = invoice.with_context(include_business_fields=False) #don't copy sale/purchase links
        withhold = invoice.copy(default=vals)
        lines = self.env['account.move.line'] #empty recordset
        if withhold.l10n_ec_withhold_type == 'in_withhold' or withhold.l10n_ec_withhold_type == 'out_withhold':
            total = 0.0
            for line in self.withhold_line_ids:
                tax_line = line.tax_id.invoice_repartition_line_ids.filtered(lambda x:x.repartition_type == 'tax')
                vals = {
                    'name': line.tax_id.name + ' ' + line.invoice_id.name,
                    'move_id': withhold.id,
                    'partner_id': withhold.partner_id.id,
                    'account_id': line.account_id.id,
                    'date_maturity': False,
                    'quantity': 1.0,
                    'amount_currency': 0.0, #Withholds are always in company currency
                    'price_unit': line.amount,
                    'price_subtotal': line.amount,
                    'price_total': line.amount,
                    'debit': line.amount if withhold.l10n_ec_withhold_type == 'out_withhold' else 0.0,
                    'credit': line.amount if withhold.l10n_ec_withhold_type == 'in_withhold' else 0.0,
                    'is_rounding_line': False,
                    'l10n_ec_withhold_invoice_id': line.invoice_id.id,
                    'tax_base_amount': line.base,
                    'tax_line_id': line.tax_id.id, #originator tax
                    'tax_repartition_line_id': tax_line.id,
                    'tax_tag_ids': [(6, 0, tax_line.tag_ids.ids)],
                    # 'tax_tag_invert': True, #TODO V15.3 revisar este campo, es el delta
                    'exclude_from_invoice_tab': True,
                }
                total += line.amount
                line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals)
                lines += line
            #Payable/Receivable line
            vals = {
                'name': False,
                'move_id': withhold._origin.id,
                'partner_id': withhold.partner_id.id,
                'account_id': self._l10n_ec_get_partner_account(withhold.partner_id, withhold.l10n_ec_withhold_type).id,
                'date_maturity': False,
                'quantity': 1.0,
                'amount_currency': total, #Withholds are always in company currency
                'price_unit': total,
                'debit': total if withhold.l10n_ec_withhold_type == 'in_withhold' else 0.0,
                'credit': total if withhold.l10n_ec_withhold_type == 'out_withhold' else 0.0,
                'tax_base_amount': 0.0,
                'is_rounding_line': False,
                'exclude_from_invoice_tab': True,
            }
            line = self.env['account.move.line'].with_context(check_move_validity=False).create(vals)
            lines += line
            withhold.line_ids = lines
            withhold._post(soft=False)
            self._reconcile_withhold_vs_invoices(withhold, self.related_invoices)
        return invoice.with_context(withhold=withhold.ids).l10n_ec_action_view_withholds() #TODO V15.2 talvez no retornar pues ya queda en el widget de pago
    
    def _validate_invoices_data(self):
        # Let's test the source invoices for missuse before showing the withhold wizard
        MAP_INVOICE_TYPE_PARTNER_TYPE = {
            'out_invoice': 'customer',
            'out_refund': 'customer',
            'in_invoice': 'supplier',
            'in_refund': 'supplier',
        }
        for invoice in self.related_invoices:
            if not invoice.l10n_ec_allow_withhold:
                raise ValidationError(
                    u'The selected document type does not support withholds, please check the document "%s".' % invoice.name)
            if invoice.state not in ['posted']:
                raise ValidationError(u'Can not create a withhold, the document "%s" not yet posted.' % invoice.name)
            if invoice.commercial_partner_id != self.related_invoices[0].commercial_partner_id:
                raise ValidationError(
                    u'Some documents belong to different partners, please correct the document "%s".' % invoice.name)
            if MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type] != MAP_INVOICE_TYPE_PARTNER_TYPE[self.related_invoices[0].move_type]:
                raise ValidationError(
                    u'Can not mix documents supplier and customer documents in the same withhold, please correct the document "%s".' % invoice.name)
            if invoice.currency_id != invoice.company_id.currency_id:
                raise ValidationError(
                    u'A fin de emitir retenciones sobre múltiples facturas, deben tener la misma moneda, revise la factura "%s".' % invoice.name)
            if len(self.related_invoices) > 1 and invoice.move_type != 'out_invoice':
                raise ValidationError(
                    u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')
                
    def _validate_withhold_data_on_post(self):
        #Validations that apply only on withhold post, other validations should be method _validate_invoices_data()
        if not self.withhold_line_ids:
            raise ValidationError(u'You must input at least one withhold line')
        related_withholds = self.related_invoices.l10n_ec_withhold_ids.filtered(lambda x: x.state == 'posted' and x.id != self.id)
        if related_withholds and self.withhold_type == 'in_withhold':
            #Current MVP allows just one withhold per purchase invoice
            #TODO evaluate allowing 2 withholds per purchase invoice and on several purchase invoces at a time (similar to sales) 
            raise ValidationError(u'Another withhold already exists, you can have only one posted withhold per purchase document')
        #Validate there where not other withholds for same invoice for same concept (concept might be vat withhold or income withhold)
        current_categories = self.withhold_line_ids.tax_id.tax_group_id.mapped('l10n_ec_type')
        for previous_withhold_line in related_withholds.l10n_ec_withhold_line_ids:
            previous_category = previous_withhold_line.tax_line_id.tax_group_id.l10n_ec_type
            if previous_category in current_categories:
                raise ValidationError("Error, another withhold already exists for %s, withhold number %s" % (previous_category, previous_withhold_line.move_id.name))
        error = ''
        invoice_list = []
        amount_total = 0.0
        for invoice in self.related_invoices:
            #Ensure withhold tax base amounts are smaller than base amounts of its invoices
            total_base_vat = 0.0
            vat_lines = self.withhold_line_ids.filtered(lambda withhold_line: withhold_line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase'] and withhold_line.invoice_id == invoice)
            for vat_line in vat_lines:
                total_base_vat += vat_line.base
            precision = invoice.company_id.currency_id.decimal_places
            vat_base, vat_amount = self.env['l10n_ec.wizard.account.withhold.line']._get_invoice_vat_base_and_amount(invoice)
            diff_base_vat = float_compare(total_base_vat, vat_base, precision_digits=precision)
            if diff_base_vat > 0:
                raise ValidationError(u'La base imponible de la retención de iva es mayor a la base imponible de la factura %s.' % invoice.l10n_latam_document_number)
            total_base_profit = 0.0
            profit_lines = self.withhold_line_ids.filtered(lambda withhold_line: withhold_line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase'] and withhold_line.invoice_id == invoice)
            for profit_line in profit_lines:
                total_base_profit += profit_line.base
            diff_base_profit = float_compare(total_base_profit, invoice.amount_untaxed, precision_digits=precision)
            if diff_base_profit > 0:
                raise ValidationError(u'La base imponible de la retención de renta es mayor a la base imponible de la factura %s.' % invoice.l10n_latam_document_number)            
            if self.date < invoice.invoice_date:
                invoice_list.append(invoice.name)
            amount_total += invoice.amount_total
        if invoice_list:
            joined_vals = '\n'.join('* ' + l for l in invoice_list)
            error += u'Las siguientes facturas tienen una fecha posterior a la retención:\n%s\n' % joined_vals        
        if self.l10n_ec_total > amount_total:
            error += u'La cantidad a retener es mayor que el valor de las facturas.\n'
        if error:
            raise ValidationError(error)
    
    @api.model
    def _reconcile_withhold_vs_invoices(self, withhold, related_invoices):
        #reconciles the withhold against the invoce, pays older open invoice first
        partner_id = related_invoices[0].partner_id.commercial_partner_id
        if withhold.l10n_ec_withhold_type in ['out_withhold']:
            (withhold + related_invoices).line_ids.filtered(lambda line: not line.reconciled and line.account_id == self._l10n_ec_get_partner_account(partner_id, withhold.l10n_ec_withhold_type)).reconcile()
        elif withhold.l10n_ec_withhold_type in ['in_withhold']:
            (withhold + related_invoices).line_ids.filtered(lambda line: not line.reconciled and line.account_id == self._l10n_ec_get_partner_account(partner_id, withhold.l10n_ec_withhold_type)).reconcile()
            
    def _l10n_ec_get_partner_account(self, partner, withhold_type):
        account = self.env['account.account']
        if withhold_type in ['out_withhold']:
            account = partner.property_account_receivable_id
        elif withhold_type in ['in_withhold']:
            account = partner.property_account_payable_id
        return account
            
    @api.depends('withhold_line_ids')
    def _l10n_ec_compute_move_totals(self):
        '''
        '''
        for wizard in self:
            l10n_ec_vat_withhold = 0.0
            l10n_ec_profit_withhold = 0.0
            l10n_ec_total_base_vat = 0.0
            l10n_ec_total_base_profit = 0.0
            for line in wizard.withhold_line_ids:
                if line.tax_id.tax_group_id:
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
                        l10n_ec_vat_withhold += line.amount
                        l10n_ec_total_base_vat += line.base
                    if line.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase']:
                        l10n_ec_profit_withhold += line.amount
                        l10n_ec_total_base_profit += line.base
            wizard.l10n_ec_vat_withhold = l10n_ec_vat_withhold
            wizard.l10n_ec_profit_withhold = l10n_ec_profit_withhold
            wizard.l10n_ec_total_base_vat = l10n_ec_total_base_vat
            wizard.l10n_ec_total_base_profit = l10n_ec_total_base_profit
            wizard.l10n_ec_total = l10n_ec_vat_withhold + l10n_ec_profit_withhold


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
    
    # TODO ANDRES: Poner la factura por defecto cuando solo hay una
    # if not self.invoice_id and len(self.wizard_id.related_invoices) == 1:
    #     self.invoice_id = self.wizard_id.related_invoices

    @api.onchange('invoice_id', 'tax_id')
    def onchange_invoice_id(self):
        #Suggest a "base amount" according to linked invoice_id and tax type
        base = 0.0
        if self.tax_id.tax_group_id.l10n_ec_type in ['withhold_vat_sale', 'withhold_vat_purchase']:
            vat_base, vat_amount = self._get_invoice_vat_base_and_amount(self.invoice_id)
            base = vat_amount
        elif self.tax_id.tax_group_id.l10n_ec_type in ['withhold_income_sale', 'withhold_income_purchase']:
            base = self.invoice_id.amount_untaxed
        self.base = base
    
    @api.onchange('base', 'tax_id')
    def onchange_base(self):
        #Recomputes amount according to "base amount" and tax percentage
        percentage = (-1) * self.tax_id.amount / 100 or 0.0
        amount = self.base * percentage
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
                raise ValidationError(_('Negative values ​​are not allowed in amount for withhold lines.'))
            if float_compare(line.base, 0.0, precision_digits=precision) < 0:
                raise ValidationError(_('Negative or zero values ​​are not allowed in base for withhold lines.'))
    
    @api.model
    def _get_invoice_vat_base_and_amount(self, invoice):
        #TODO: Review with Odoo, maybe there is other way to compute it, based on Trescloud method _l10n_ec_compute_move_totals()
        l10n_ec_vat_base = 0.0
        l10n_ec_vat_amount = 0.0
        for move_line in invoice.line_ids:
            if move_line.tax_group_id:
                if move_line.tax_group_id.l10n_ec_type in ['vat8','vat12', 'vat14']:
                    l10n_ec_vat_base += move_line.tax_base_amount
                    l10n_ec_vat_amount += move_line.price_subtotal
        return l10n_ec_vat_base, l10n_ec_vat_amount        
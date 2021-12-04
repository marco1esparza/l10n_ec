# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class L10nEcCustomMoveLine(models.Model):
    _name = 'l10n_ec.custom.move.line'
    _description = 'Custom Account Move Line'
    
    @api.model_create_multi
    def create(self, vals_list):
        # Se hace super al create para poder guardar los datos de subtotal y total
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
                tax_ids = set(taxes.ids)
                taxes = self.env['account.tax'].browse(tax_ids)

                if any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        partner,
                        taxes,
                        move.move_type,
                    ))
        lines = super(L10nEcCustomMoveLine, self).create(vals_list)
        return lines

    def write(self, vals):
        # Se hace super al write para poder guardar los datos de subtotal y total
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        result = False
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue

            result |= super(L10nEcCustomMoveLine, line).write(vals)
            if any(vals.get(field) for field in BUSINESS_FIELDS):
                to_write = line._get_price_total_and_subtotal()
                result |= super(L10nEcCustomMoveLine, line).write(to_write)
        return result
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        # Para rellenar valores de la linea de fact
        for line in self:
            if line.product_id:
                line.code = line.product_id.default_code
                line.name = line.product_id.name
                line.product_uom_id = line.product_id.uom_id
                line.price_unit = line.product_id.list_price
            line.tax_ids = line.move_id.company_id.account_sale_tax_id
    
    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        # Onchange para obtener y actualizar el subtotal y total de las lineas
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.update(line._get_price_total_and_subtotal())

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, partner=None, taxes=None, move_type=None):
        # Computa para obtener el subtotal y total de las lineas
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=quantity or self.quantity,
            discount=discount or self.discount,
            currency=currency or self.currency_id,
            partner=partner or self.partner_id,
            taxes=taxes or self.tax_ids,
            move_type=move_type or self.move_id.move_type,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, partner, taxes, move_type):
        # Computa para obtener el subtotal y total de las lineas
        res = {}
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit
        if taxes:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    @api.depends('price_unit', 'price_subtotal', 'move_id.l10n_latam_document_type_id')
    def compute_l10n_latam_prices_and_taxes(self):
        # Compute para obtener los valores de los campos l10n_latam_price_unit y l10n_latam_price_subtotal,
        # usados en la generacion del xml
        for line in self:
            invoice = line.move_id
            included_taxes = \
                invoice.l10n_latam_document_type_id and invoice.l10n_latam_document_type_id._filter_taxes_included(line.tax_ids)
            # For the unit price, we need the number rounded based on the product price precision.
            # The method compute_all uses the accuracy of the currency so, we multiply and divide for 10^(decimal accuracy of product price) to get the price correctly rounded.
            price_digits = 10 ** self.env['decimal.precision'].precision_get('Product Price')
            if not included_taxes:
                price_unit = \
                line.tax_ids.with_context(round=False, force_sign=invoice._get_tax_force_sign()).compute_all(
                    line.price_unit * price_digits, invoice.currency_id, 1.0, line.product_id, invoice.partner_id)
                l10n_latam_price_unit = price_unit['total_excluded'] / price_digits
                l10n_latam_price_subtotal = line.price_subtotal
            else:
                l10n_latam_price_unit = \
                included_taxes.with_context(force_sign=invoice._get_tax_force_sign()).compute_all(
                    line.price_unit * price_digits, invoice.currency_id, 1.0, line.product_id, invoice.partner_id)['total_included'] / price_digits
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                l10n_latam_price_subtotal = \
                included_taxes.with_context(force_sign=invoice._get_tax_force_sign()).compute_all(
                    price, invoice.currency_id, line.quantity, line.product_id,
                    invoice.partner_id)['total_included']
            line.l10n_latam_price_subtotal = l10n_latam_price_subtotal
            line.l10n_latam_price_unit = l10n_latam_price_unit

    def _compute_total_invoice_line_ec(self):
        # Compute para tener el monto del descuento por linea
        for line in self:
            total_discount = 0.0
            if line.discount:
                if line.tax_ids:
                    taxes_res = line.tax_ids._origin.compute_all(line.l10n_latam_price_unit,
                        quantity=line.quantity, currency=line.currency_id, product=line.product_id, partner=line.partner_id, is_refund=line.move_id.move_type in ('out_refund', 'in_refund'))
                    total_discount = taxes_res['total_excluded'] - line.l10n_latam_price_subtotal
                else:
                    total_discount = (line.quantity * line.l10n_latam_price_unit) - line.l10n_latam_price_subtotal
                if line.currency_id:
                    total_discount = line.currency_id.round(total_discount)
            line.l10n_ec_total_discount = total_discount

    # columns
    move_id = fields.Many2one(
        'account.move', string='Journal Entry',
        index=True, required=True, readonly=True, auto_join=True, ondelete='cascade',
        check_company=True,
        help='The move of this entry line.'
        )
    sequence = fields.Integer(
        default=10
        )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        ondelete='restrict'
        )
    code = fields.Char(
        string='Código',
        tracking=True
        )
    name = fields.Char(
        string='Label',
        tracking=True
        )
    quantity = fields.Float(
        string='Quantity',
        default=1.0, digits='Product Unit of Measure',
        help='The optional quantity expressed by this line, eg: number of product sold. '
            'The quantity is not a legal requirement but is very useful for some reports.'
        )
    product_uom_category_id = fields.Many2one(
        'uom.category', 
        related='product_id.uom_id.category_id'
        )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UdM',
        domain=[('category_id', '=', product_uom_category_id)]
        )
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price'
        )
    price_subtotal = fields.Monetary(
        string='Subtotal', store=True, readonly=True,
        currency_field='currency_id'
        )
    price_total = fields.Monetary(
        string='Total', store=True, readonly=True,
        currency_field='currency_id'
        )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True
        )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        ondelete='restrict'
        )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        ondelete='restrict'
        )
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0
        )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string='Taxes',
        context={'active_test': False},
        check_company=True,
        help='Taxes that apply on the base amount'
        )
    company_id = fields.Many2one(
        related='move_id.company_id', store=True, readonly=True,
        default=lambda self: self.env.company
        )
    l10n_latam_price_unit = fields.Monetary(
        compute='compute_l10n_latam_prices_and_taxes', digits='Product Price'
        )
    l10n_latam_price_subtotal = fields.Monetary(
        compute='compute_l10n_latam_prices_and_taxes'
        )
    l10n_ec_total_discount = fields.Monetary(
        string='Total Discount',
        compute='_compute_total_invoice_line_ec',
        tracking=True,
        store=False,
        readonly=True,
        help='Indicates the monetary discount applied to the total invoice line.'
        )

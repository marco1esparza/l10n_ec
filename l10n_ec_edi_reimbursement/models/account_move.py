# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    '''
    This class determine if show the field for refund like intermediate 
    or refund like client follow this rules:    
        If 'sustento tributario' is '08' and 'invoice_type' is 'in_invoice', is refund intermediate 
        If 'tipo de documento' is '41' and 'invoice_type' is 'out_invoice', is refund intermediate 
        If 'tipo de documento' is '41' and 'invoice_type' is 'in_invoice', is refund client    
    '''    
    _inherit = 'account.move'

    def compute_sale_lines_from_refunds(self):
        '''
        Genera los rubros de la factura de venta por reembolso como intermediario a partir
        de las facturas de compra detalladas en la pestaña "reembolsos"
        - Los textos son de la forma:
        - Genera una linea para lo del iva 12% y otra para lo del iva 0%
        '''
        #primero unas validaciones
        self.ensure_one()
        account_tax_obj = self.env['account.tax']
        account_move_line_obj = self.env['account.move.line']
        if self.state != 'draft':
            raise UserError(_(u'Solo se puede aplicar sobre facturas en estado borrador.'))
        if self.invoice_line_ids:
            raise UserError(_(u'Primero elimina los rubros a vender ya existentes para evitar sobreescritura accidental.'))
        refund_product = self.company_id.refund_product_id
        if not refund_product:
            raise UserError(_(u'No se ha configurado el producto para reembolso de gastos como intermediario en el formulario de la compañia.'))
        if not refund_product.property_account_income_id:
            raise UserError(_(u'No se ha configurado la cta de ingresos por reembolso de gastos como intermediario en el producto de reembolso de gastos seteado en la compañia, usualmente es la cta 101040402 OTROS ANTICIPOS POR INTERMEDIARIO.'))
        if not refund_product.property_account_expense_id:
            raise UserError(_(u'No se ha configurado la cta de egresos por reembolso de gastos como intermediario en el producto de reembolso de gastos seteado en la compañia, usualmente es la cta 101040402 OTROS ANTICIPOS POR INTERMEDIARIO.'))
        tax_zero_refund = account_tax_obj.search([
            ('amount','=',0.0),
            ('tax_group_id.l10n_ec_type','=','zero_vat'),
            ('type_tax_use','=','sale'),
            ('l10n_ec_code_base','=','444'),
            ('l10n_ec_code_applied','=','454'),
            ], limit=1)
        tax_vat_refund = account_tax_obj.search([
            ('amount','=',12.0),
            ('tax_group_id.l10n_ec_type','=','vat12'),
            ('type_tax_use','=','sale'),
            ('l10n_ec_code_base','=','444'),
            ('l10n_ec_code_applied','=','454'),
            ], limit=1)
        if not tax_zero_refund:
            raise UserError(_(u'No se encuentra el IVA 0% en reembolsos de gastos, codigo base 444, por favor configurelo correctamente.'))
        if not tax_vat_refund:
            raise UserError(_(u'No se encuentra el IVA 12% en reembolsos de gastos, codigo base 444, por favor configurelo correctamente.'))
        for purchase in self.refund_ids: 
            amount_0_vat = purchase.base_tax_free + purchase.no_vat_amount + purchase.base_vat_0
            amount_vat = purchase.base_vat_no0
            #se espera construir un texto de la siguiente forma:
            #Reembolso de gastos RUC: 1792366836001, Fact No. 001-001-0000000001, Neto Tarifa 0% $99.99
            #Reembolso de gastos RUC: 1792366836001, Fact No. 001-001-0000000001, Neto Tarifa 12% $100.00, IVA $12.00
            if not purchase.l10n_latam_document_type_id.doc_code_prefix:
                raise UserError(_(u'Configure una "Descripcion" (Por ejemplo "Fact." o "Doc") como nombre corto para el tipo de documento %s') % purchase.l10n_latam_document_type_id.name)
            base_name = []
            base_name.append('Reembolso de gastos RUC ' + purchase.partner_id.vat)
            base_name.append(purchase.l10n_latam_document_type_id.doc_code_prefix + ' No. ' + purchase.number)
            if amount_0_vat:
                inv_line = account_move_line_obj.new({
                    'move_id': self.id,
                    'product_id': self.company_id.refund_product_id.id,
                    })
                inv_line._onchange_product_id()                
                name = list(base_name)
                name.append('Neto Tarifa 0% $ ' + "{:.2f}".format(amount_0_vat))
                inv_line.name = "; ".join(name)
                inv_line.credit = amount_0_vat
                inv_line.price_unit = amount_0_vat
                inv_line.tax_ids = tax_zero_refund
                inv_line_values = account_move_line_obj._convert_to_write(inv_line._cache)
                line = account_move_line_obj.with_context(check_move_validity=False).create(inv_line_values)
                line.recompute_tax_line = True
            if amount_vat:
                inv_line = account_move_line_obj.new({
                    'move_id': self.id,
                    'product_id': self.company_id.refund_product_id.id
                    })
                inv_line._onchange_product_id()
                name = list(base_name)
                name.append('Neto $ ' + "{:.2f}".format(amount_vat))
                name.append('IVA 12% $ ' + "{:.2f}".format(purchase.vat_amount_no0))
                inv_line.name = "; ".join(name)
                inv_line.credit = amount_vat
                inv_line.price_unit = amount_vat
                inv_line.tax_ids = tax_vat_refund
                inv_line_values = account_move_line_obj._convert_to_write(inv_line._cache)
                line = account_move_line_obj.with_context(check_move_validity=False).create(inv_line_values)
                line.recompute_tax_line = True
        self.with_context(check_move_validity=False)._onchange_invoice_line_ids()
        self.onchange_set_l10n_ec_invoice_payment_method_ids()

    def action_view_refunds(self):
        '''
        - Desde la factura de compra muestra la factura de venta por reembolso como intermediario
        - Desde la factura de venta muestra las facturas de compra por reembolso como intermediario
        '''
        self.ensure_one()
        invoice_ids = []
        if self.move_type == 'in_invoice':
            #lo logico es retornar las facturas de venta por reembolso de gastos
            #para encontrarlas nos basamos en el proveedor, tipo de documento y nro de factura
            #(esto nos da un identificador univoco, sin necesidad de crear un campo de relacion)
            refund_lines = self.env['account.refund.client'].search([
                ('partner_id','=', self.partner_id.commercial_partner_id.id),
                ('l10n_latam_document_type_id','=', self.l10n_latam_document_type_id.id),
                ('number','=', self.l10n_latam_document_number),
                ])
            invoice_ids = refund_lines.mapped('move_id').ids
        if self.move_type == 'out_invoice':
            #lo logico es retornar las facturas de compra por reembolso de gastos
            #para encontrarlas nos basamos en el proveedor, tipo de documento y nro de factura
            #(esto nos da un identificador univoco, sin necesidad de crear un campo de relacion)
            for purchase in self.refund_ids:
                #Se usa sql pues un search falla en el campo l10n_latam_document_number
                self.env.cr.execute('''
                    select 
                        id 
                    from account_move
                    where commercial_partner_id=%s and l10n_latam_document_type_id=%s and name ilike %s and type='in_invoice'
                ''', (purchase.partner_id.commercial_partner_id.id, purchase.l10n_latam_document_type_id.id, '%' + purchase.number + '%'))
                purchases = self.env.cr.fetchall()
                for purchase in purchases:
                    invoice_ids.append(purchase[0])
        if self.move_type == 'out_invoice' and not invoice_ids:
            #lanzamos una notificacion al usuario indicandole que no se encontraron las facturas buscadas
            raise UserError(u'En el módulo contable no se encontraron las facturas de compra para el reembolso, posiblemente no las digitó en el sistema')
        if self.move_type == 'in_invoice' and not invoice_ids:
            #lanzamos una notificacion al usuario indicandole que no se encontraron las facturas buscadas
            raise UserError(u'No se encontró una factura de venta por reembolso como intermediario, puede generar una con el boton "Generar Venta"') 
        if self.move_type == 'in_invoice':
            action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        else: #out_invoice
            action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        action['domain'] = [('id', 'in', invoice_ids)]
        return action

    def generate_sale_refund(self):
        """
        A partir de facturas de compra por reembolso como intermediario genera
        una factura de venta por reembolso como intermediario, en un solo paso.
        """
        account_move_obj = self.env['account.move']
        # ponemos unas validaciones
        if any(x.move_type not in ('in_invoice') for x in self):
            raise UserError(_(
                u'La generación de facturas de venta por reembolso de gastos solo aplica para facturas de compra por reembolso de gastos.'))
        if any(x.state not in ('posted') for x in self):
            raise UserError(_(u'Las facturas seleccionadas deben estar aprobadas.'))
        l10n_latam_document_type_id = self.env.ref('l10n_ec.ec_59')
        if not l10n_latam_document_type_id:
            raise UserError(_(
                u'No se encontro un tipo de documento de reembolso para venta, por favor verifique la configuración del documento de venta con código 41.'))
        # computo del campo origin
        origin = []
        for purchase in self:
            text = []
            if purchase.invoice_origin:
                text.append(purchase.invoice_origin)
            text.append(purchase.l10n_latam_document_number)
            text = ",".join(text)
            origin.append(text)
        origin = ";".join(origin)
        # creamos la factura
        invoice_header = {
            'partner_id': self[0].company_id.partner_id.id,
            # temporalmente se deja con esta empresa hasta que el usuario selecciona una manualmente
            'move_type': 'out_invoice',  # se indica aqui el tipo de factura para el resto de la creacion
            # 'date_invoice': fields.Date.context_today(self),
            'invoice_origin': origin,
            'l10n_latam_document_type_id': l10n_latam_document_type_id.id
        }
        inv_id = account_move_obj.new(invoice_header)
        res_partner = inv_id._onchange_partner_id()
        # volvemos a crear el inv_id pero con la data del onchange del partner incorporada
        # esto incluye el printer_id que estaba faltando
        inv_id_dict = inv_id._convert_to_write({name: inv_id[name] for name in inv_id._cache})
        inv_id = account_move_obj.new(inv_id_dict)
        # los otros dos onchanges no requieren redefinicion del inv_id
        res_document = inv_id._inverse_l10n_latam_document_number()
        res_printer = inv_id.onchange_l10n_ec_printer_id()
        inv_id_dict = inv_id._convert_to_write({name: inv_id[name] for name in inv_id._cache})
        inv_id_dict.update(invoice_header)  # para mantener nuestros datos maestros
        # computo de las lineas de reembolso
        refund_lines_vals = []
        for purchase in self:
            refund_lines_vals.append(
                (0, 0,
                 {'creation_date': purchase.invoice_date,
                  'move_id': purchase.id,
                  'partner_id': purchase.partner_id.id,
                  'transaction_type': False,
                  'l10n_latam_document_type_id': purchase.l10n_latam_document_type_id.id,
                  'authorization': purchase.l10n_ec_authorization,
                  'number': purchase.l10n_latam_document_number,
                  'base_tax_free': purchase.l10n_ec_base_tax_free,
                  'no_vat_amount': purchase.l10n_ec_base_not_subject_to_vat,
                  'base_vat_0': purchase.l10n_ec_base_cero_iva,
                  'base_vat_no0': purchase.l10n_ec_base_doce_iva,
                  'vat_amount_no0': purchase.l10n_ec_vat_doce_subtotal,
                  'ice_amount': 0.0,
                  'total': purchase.l10n_ec_total_with_tax
                  }
                 )
            )
        inv_id_dict.update({'refund_ids': refund_lines_vals})  # agregamos las lineas
        sale_invoice_id = account_move_obj.create(inv_id_dict)
        # computamos los rubros a facturar
        sale_invoice_id.compute_sale_lines_from_refunds()
        # retornamos la factura de venta por reembolso de gastos
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        action['domain'] = [('id', 'in', sale_invoice_id.ids)]
        return action

    def _post(self, soft=True):
        '''
        Invocamos el metodo post para garantizar que el total de la facturas coindida con el total del reembolso
        '''
        for invoice in self:
            if invoice.show_reimbursements_detail:
                #si se debio llenar 
                refund_total = 0.0
                for refund in invoice.refund_ids:
                    refund_total += refund.total
                if float_compare(invoice.l10n_ec_total_with_tax,refund_total,invoice.company_id.currency_id.decimal_places) != 0:
                    raise ValidationError(u'No coincide el total de la factura con el total del reembolso.')
                # Verify if have at least one line of data refund and the date
                if not invoice.refund_ids:
                    raise UserError(_(u'El reembolso de gastos para clientes requiere al menos una línea de detalle de las facturas a reembolsar.'))
                if not invoice.invoice_date:
                    raise UserError(_(u'Ingrese una fecha para el reembolso.'))
                for line_ats in invoice.refund_ids:
                    if line_ats.creation_date > invoice.invoice_date:
                        raise UserError(_(u'La fecha en los datos de reembolso para el ATS del proveedor %s, Factura: %s, es mayor que la fecha de la factura de reembolso.' %(line_ats.partner_id.name, line_ats.number)))
                #TODO: Ver que no estemos usando dos veces la misma factura de compra
                self.env.cr.execute(
                    '''
                    --consulta que busca si existen registros duplicados en base a una combinacion de campos
                    SELECT 
                        rp.commercial_partner_id,
                        l10n_latam_document_type_id,
                        arc.number,
                        count(*) as qty 
                    FROM account_refund_client arc
                    LEFT JOIN res_partner rp on arc.partner_id = rp.id
                    WHERE move_id = %s
                    GROUP BY rp.commercial_partner_id, l10n_latam_document_type_id, arc.number 
                    HAVING count(*) > 1
                    ''',(invoice.id,))
                result = self.env.cr.dictfetchone()
                if result:
                    raise ValidationError(u'Ha seleccionado varias veces la misma factura de compra, debe incluirla una sola vez.')
            if not invoice.show_reimbursements_detail and invoice.refund_ids:
                #si no se debio llenar los detalles de reembolso
                raise ValidationError(u'Es extraño, la tabla de detalles de reembolso no debería seguir llena, por favor contacte a soporte o repita la transacción desde el inicio.')
            if invoice.move_type == 'in_invoice' and invoice.l10n_latam_document_type_id.code == '41':
                #no se emite retencion sobre facturas de compra por reembolso como cliente final (en este caso el codigo es 41)
                if invoice.l10n_ec_total_to_withhold != 0.0: #aplica para compras
                    raise UserError(_(u'La factura de reembolsos de gastos como cliente final no puede tener impuestos de retención, por favor elimínelos para poder validarla.'))
            #validamos los impuestos para EMISION de REEMBOLSOS COMO INTERMEDIARIO
            if invoice.move_type == 'out_invoice' and invoice.l10n_latam_document_type_id.code == '41':
                #solo permitimos con la base 444 *equivale al codigo aplicado 454
                base_codes = invoice.line_ids.mapped('tax_ids').mapped('l10n_ec_code_base')
                base_codes = list(dict.fromkeys(base_codes)) #remueve duplicados
                try:
                    base_codes.remove('444') #removemos el unico codigo permitido
                except ValueError:
                    #si el codigo 444 no esta en la lista lanza un error, lo capturamos. 
                    pass
                if base_codes:
                    raise UserError(_(u'La emisión de reembolsos de gastos como intermediario debe realizarse con el impuesto 454, erroneamente esta utilizando los códigos: %s' %", ".join(base_codes)))
            #validamos los impuestos para RECEPCION de compras para REEMBOLSOS COMO INTERMEDIARIO
            if invoice.move_type == 'in_invoice' and invoice.l10n_ec_sri_tax_support_id.code == '08':
                #solo permitimos con la base 545 *equivale al codigo aplicado 555
                vat_taxes = invoice.line_ids.mapped('tax_ids').filtered(lambda r: r.tax_group_id.l10n_ec_type in ['vat12', 'vat14','zero_vat','not_charged_vat','exempt_vat'])
                base_codes = vat_taxes.mapped('l10n_ec_code_base')
                base_codes = list(dict.fromkeys(base_codes)) #remueve duplicados
                try:
                    base_codes.remove('545') #removemos el unico codigo permitido
                except ValueError:
                    #si el codigo 545 no esta en la lista lanza un error, lo capturamos. 
                    pass
                if base_codes:
                    raise UserError(_(u'La recepción de egresos para reembolso de gastos como intermediario debe realizarse con el impuesto 555, erroneamente esta utilizando los códigos: %s' %", ".join(base_codes)))
        return super(AccountMove, self)._post(soft)

    @api.depends('l10n_latam_document_type_id', 'type', 'l10n_ec_sri_tax_support_id')
    def _show_reimbursements(self):
        '''
        Si es una factura de venta o compra por reembolso de gastos como INTERMEDIARIO
        activa el campo para que se muestre el boton de ver reembolsos
         
        En el resto de casos de reembolso de gastos *(como intermediario o final)
        activa el campo para que se muestre el detalle de los reembolsos
        '''
        for move in self:
            if move.country_code == 'EC':
                show_reimbursements_related = False
                show_reimbursements_detail = False
                if move.move_type in ['out_invoice'] and move.l10n_latam_document_type_id.code == '41':
                    #es una factura de venta por reembolso de gastos como INTERMEDIARIO
                    show_reimbursements_related = True
                    show_reimbursements_detail = True
                elif move.move_type in ['in_invoice'] and move.l10n_latam_document_type_id.code == '41':
                    #es una factura de compra por reembolso de gastos como CLIENTE FINAL
                    show_reimbursements_related = False
                    show_reimbursements_detail = True
                elif move.move_type in ['in_invoice'] and move.l10n_ec_sri_tax_support_id.code == '08':
                    #es una factura de compra por reembolso de gastos como INTERMEDIARIO
                    show_reimbursements_related = True
                    show_reimbursements_detail = False
                move.show_reimbursements_related = show_reimbursements_related
                move.show_reimbursements_detail = show_reimbursements_detail

    #Columns
    show_reimbursements_related = fields.Boolean(
        string='Mostrar Reembolsos Intermediario',
        compute='_show_reimbursements',
        method=True,
        store=False,
        help='Campo tecnico, ayuda a ocultar o presentar el boton de ver facturas de reembolso vinculadas desde compras o ventas'
        ) 
    show_reimbursements_detail = fields.Boolean(
        string='Mostrar Detalle Reembolso',
        compute='_show_reimbursements',
        method=True,
        store=False,
        help='Campo tecnico, ayuda a ocultar o presentar el detalle de las facturas reembolsadas'
        )
    refund_ids = fields.One2many(
        'account.refund.client', 
        'move_id',
        string='Refund Client Line',
        help='List of purchase invoices used in this refund'
        )

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import base64
import io
from odoo.tools.misc import xlsxwriter
from datetime import datetime


class AccountTaxFormHeader(models.TransientModel):
    _name = 'l10n_ec.account.tax.form.header'

    def name_get(self):
        result = []
        for header in self:
            name = ''
            if header.env.context.get('origin') == 'form_103':
                name = '103'
            elif header.env.context.get('origin') == 'form_104':
                name = '104'
            result.append((header.id, "Formulario %s del %s al %s" % (
                name, header.date_from, header.date_to)))
        return result

    def _compute_name(self):
        name = ''
        if self.env.context.get('origin') == 'form_103':
            name = '103'
        elif self.env.context.get('origin') == 'form_104':
            name = '104'
        self.name  = "Formulario %s" % name

    def _get_filters(self):
        '''
        Mostrar filtros para reporte 103 y 104.
        '''
        object = self
        date_from = object.date_from
        date_to = object.date_to
        return [
            (u'Rango', u'%s al %s' % (date_from or u'Todos los Registros', date_to or u'.')),
            (u'Generado el', fields.Datetime.context_timestamp(self, datetime.now()).strftime('%Y-%m-%d %H:%M:%S'))
        ]

    def print_xls(self):
        '''
        Imprimir reporte de formulario de impuesto en XLS.
        '''
        def evalobj(obj, field):
            for attr in field.split('.'):
                if hasattr(obj, attr):
                    obj = getattr(obj, attr)
                else:
                    break
            return obj
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output, {'in_memory': True})
        obj = self
        formgrouptaxes = {}
        state = {
            'posted': 'Publicado',
        }
        for group in obj.tax_group_ids:
            formgrouptaxes[group.group_name] = formgrouptaxes.get(group.group_name, []) + [group]
        FIELDS = [
            (u'Fecha', 'invoice_date', 'datef', 30),
            (u'Asiento', 'invoice_id.name', 'std', 40),
            (u'Contribuyente', 'partner_id.name', 'std', 100),
            (u'R.U.C.', 'partner_id.vat', 'std', 40),
            (u'Retención No', 'withholding_number', 'std', 40),
            (u'Base imponible', 'base', 'num', 40),
            (u'Valor', 'amount', 'num', 40),
            (u'Estado', 'invoice_id.state', 'std', 20)
        ]
        FIELDS_RES = [
            (u'Codigo Aplicado', 'tax_code', 'std'),
            (u'Codigo Base', 'tax_code_base', 'std'),
            (u'Codigo ATS', 'tax_code_ats', 'std'),
            (u'Impuesto', 'tax_name', 'std'),
            (u'Total base imponible', 'base', 'num'),
            (u'Total valor', 'amount', 'num'),
        ]

        titleheader = book.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'valign': 'center', 'align': 'center'})
        bold = book.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12})
        std =  book.add_format({'font_name': 'Arial', 'font_size': 11})
        title = book.add_format({'font_name': 'Arial', 'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#C3CDE6', 'font_size': 12, 'align': 'center'})
        perc = book.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': '0.00%'})
        datef = book.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': 'YYYY/mm/dd'})
        num = book.add_format({'font_name': 'Arial', 'font_size': 11, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00', 'align': 'right'})
        num_bold = book.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 11, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00', 'align': 'right'})


        for formulario, taxes_group in iter(formgrouptaxes.items()):
            sheet = book.add_worksheet(formulario and str(formulario) or 'Des')
            sheet.merge_range(0, 0, 0, 2, self.company_id.l10n_ec_legal_name or self.company_id.name, titleheader)
            sheet.merge_range(1, 0, 1, 2, u'Detalles de '+ self.name, titleheader)
            row = 2
            for row, (key, value) in enumerate(self._get_filters(), 3):
                sheet.write(row, 0, key, std)
                sheet.write(row, 1, value, std)
                row += 1
            row += 2
            for group in taxes_group:
                sheet.write(row, 0, 'Impuesto: %s (%s)'%(group.tax_name,group.tax_code), bold)
                for col, field in enumerate(FIELDS, 0):
                    sheet.set_column(col, col, field[3])
                    sheet.write(row+1, col, field[0], title)
                for aux, line in enumerate(group.account_tax_line_ids, 0):
                    for col, (field, attr, sty, width) in enumerate(FIELDS, 0):
                        if attr == 'invoice_id.state':
                            sheet.write(aux + row + 2, col, state[evalobj(line, attr)] or '', std)
                        else:
                            style = std
                            if sty == 'num':
                                style = num
                            elif sty == 'datef':
                                style = datef
                            sheet.write(aux + row + 2, col, evalobj(line, attr) or '', style)
                row += len(group.account_tax_line_ids) + 3
            #=======================================================================
            # Resumen Tributario
            sheet.write(row, 0, 'RESUMEN TRIBUTARIO', bold)
            for col, field in enumerate(FIELDS_RES, 0):
                sheet.write(row+2, col, field[0], title)
            for aux, group in enumerate(taxes_group, 0):
                col_aux = 0
                for col, (field, attr, sty) in enumerate(FIELDS_RES):
                    if field[0] != ' ':
                        value = evalobj(group, attr)
                        value = '(%s Registros)'%len(value) if field == u'Movimientos' else value
                        sheet.write(aux+row+3, col + col_aux, value or '', std)
            #=======================================================================
        book.close()
        output.seek(0)
        generated_file = base64.b64encode(output.read())
        output.close()
        return self.env['base.file.report'].show(generated_file, 'Impuestos.xls')

    #Columns
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get(),
                                 required=True, help='')
    name = fields.Char('Name', compute='_compute_name')
    date_from = fields.Date('Date From', required=True, help='')
    date_to = fields.Date('Date To', required=True, help='')
    tax_group_ids = fields.One2many('l10n_ec.account.tax.form.group', 'account_tax_header_id', string='Taxes Group', help='')


class AccountTaxFormGroup(models.TransientModel):
    _name = 'l10n_ec.account.tax.form.group'
    _order = 'tax_code'

    def action_view_tax_form_lines(self):
        '''
        Accion para mostrar las lineas asociadas a un impuesto.
        '''
        self.ensure_one()
        action = {
            'name': 'Account Tax Form Lines',
            'view_mode': 'tree',
            'res_model': 'l10n_ec.account.tax.form.line',
            'view_id': self.env.ref('l10n_ec_reports.view_account_tax_form_line_tree').id,
            'type': 'ir.actions.act_window',
            'domain': [('account_tax_group_id', '=', self.id)],
            'target': 'current'
        }
        return action

    # Columns
    account_tax_header_id = fields.Many2one('l10n_ec.account.tax.form.header', string='Tax Form', required=True, help='')
    tax_id = fields.Many2one('account.tax', string='Tax', help='')
    tax_code = fields.Char(related='tax_id.l10n_ec_code_applied', string='Tax Code', store=True, help='')
    tax_code_base = fields.Char(related='tax_id.l10n_ec_code_base', string='Tax Code Base', store=True, help='')
    tax_code_ats = fields.Char(related='tax_id.l10n_ec_code_ats', string='Tax Code ATS', store=True, help='')
    tax_name = fields.Char(string='Tax Name', help='')
    base = fields.Monetary(string='Base', help='')
    amount = fields.Monetary(string='Tax Amount', help='')
    perc = fields.Float(string='Percentage', help='')
    currency_id = fields.Many2one('res.currency', string='Currency', help='')
    tax_group_id = fields.Many2one('account.tax.group', string='Tax Group', help='')
    group_name = fields.Char(related='tax_group_id.name', store=True, help='')
    account_tax_line_ids = fields.One2many('l10n_ec.account.tax.form.line', 'account_tax_group_id', string='Tax Group', help='')


class AccountTaxFormGroup(models.TransientModel):
    _name = 'l10n_ec.account.tax.form.line'

    @api.depends('invoice_id')
    def _get_withholding_number(self):
        '''
        Se computa para obtener los numeros de retenciones.
        '''
        for record in self:
            withholding_number = ''
            if record.invoice_id.l10n_ec_withhold_ids:
                for withholding in record.invoice_id.l10n_ec_withhold_ids:
                    if withholding_number:
                        withholding_number += ',' + withholding.name
                    else:
                        withholding_number += withholding.name
            record.withholding_number = withholding_number

    def action_view_invoice_tax_form(self):
        '''
        Accion para visualizar factura.
        '''
        self.ensure_one()
        action = {
            'name': 'Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': self.invoice_id.id,
            'target': 'current'
        }
        return action

    # Columns
    account_tax_group_id = fields.Many2one('l10n_ec.account.tax.form.group', string='Tax Group', required=True, help='')
    invoice_id = fields.Many2one('account.move', string='Invoice', help='')
    internal_number = fields.Char(related='invoice_id.name', string='Internal Number', help='')
    invoice_date = fields.Date(related='invoice_id.invoice_date', string='Date Invoice', help='')
    partner_id = fields.Many2one(related='invoice_id.partner_id', string='Partner',help='')
    vat = fields.Char(related='partner_id.vat', string='Vat', help='')
    tax_id = fields.Many2one('account.tax', string='Tax', help='')
    tax_group_id = fields.Many2one('account.tax.group', string='Tax Group', help='')
    tax_code = fields.Char(related='tax_id.l10n_ec_code_applied', string='Tax Code', help='')
    tax_code_base = fields.Char(related='tax_id.l10n_ec_code_base', string='Tax Code Base', help='')
    tax_code_ats = fields.Char(related='tax_id.l10n_ec_code_ats', string='Tax Code ATS', help='')
    account_id = fields.Many2one('account.account', string='Account', help='')
    tax_name = fields.Char(string='Tax Name', help='')
    base = fields.Monetary(string='Base', help='')
    amount = fields.Monetary(string='Tax Amount', help='')
    currency_id = fields.Many2one('res.currency', string='Currency', help='')
    perc = fields.Float(string='Percentage', help='')
    withholding_number = fields.Char(string='Withholding number', compute='_get_withholding_number', help='')

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
from odoo.tools.misc import xlsxwriter


class L10nECA1DetailReport(models.TransientModel):
    _name = 'l10n_ec.a1.detail.report'
    _description = 'l10n_ec.a1.detail.report'

    def _get_sales_detail_report_invoice_domain(self):
        """
        Get base domain to search invoices
        :return: domain list
        """
        domain = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]
        type = [('move_type', 'in', ('out_invoice', 'out_refund'))]
        if self.env.context.get('only_invoice'):
            type = [('move_type', '=', 'out_invoice')]
        if self.env.context.get('only_credit_note'):
            type = [('move_type', '=', 'out_refund')]
        domain.extend(type)
        return domain

    def _get_withholding_group_values(self, invoice_id):
        values = {'max_count': 0,
                  'withhold_vat': [],
                  'withhold_income_tax': [],
                  }
        withhold_vat = len(invoice_id.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted')
                           .l10n_ec_withhold_line_ids
                           .tax_id.filtered(lambda l: l.l10n_ec_type == 'withhold_vat'))
        withhold_income_tax = len(invoice_id.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted')
                                  .l10n_ec_withhold_line_ids
                                  .tax_id.filtered(lambda l: l.l10n_ec_type == 'withhold_income_tax'))

        for line in invoice_id.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted').l10n_ec_withhold_line_ids:
            if line.tax_id.l10n_ec_type in ('withhold_vat', 'withhold_income_tax'):
                values[line.tax_id.l10n_ec_type] += [{'withholding_number': line.move_id.l10n_latam_document_number,
                                                      'withholding_authorization': line.move_id.l10n_ec_authorization,
                                                      'withholding_name': line.tax_id.name,
                                                      'withholding_base': line.base,
                                                      'withholding_amt': line.amount,
                                                      }]
            else:
                raise UserError('Factura: (%s) registra una Retencion no reconocida: %s' % (line.invoice_id.name, line.tax_id.name))
        values['max_count'] = max(withhold_vat, withhold_income_tax)
        return values

    def print_xls(self):
        '''
        Imprimir reporte en XLS.
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

        FIELDS = [
            (u'ITEM', 'index', '', 'std', 6),
            (u'TIPO ID.', 'invoice_id', 'l10n_ec_transaction_type', 'std', 7),
            (u'RUC/CI', 'invoice_id', 'partner_id.vat', 'std', 10),
            (u'CLIENTE', 'invoice_id', 'partner_id.name', 'std', 40),
            (u'PAR REL', 'invoice_id', 'partner_id.l10n_ec_related_part', 'std', 10),
            (u'TIPO COMP.', 'invoice_id', 'l10n_latam_document_type_id.display_name', 'std', 15),
            (u'NÚMERO DE DOCUMENTO', 'invoice_id', 'l10n_latam_document_number', 'std', 20),
            (u'AUTORIZACIÓN', 'invoice_id', 'l10n_ec_authorization', 'std', 40),
            (u'F. EMISIÓN', 'invoice_id', 'invoice_date', 'datef', 10),
            (u'F. CONTABIL.', 'invoice_id', 'date', 'datef', 12),
            (u'BASE NO GRAVA IVA', 'invoice_id', 'l10n_ec_base_not_subject_to_vat', 'num', 20),
            (u'BASE IVA 0%', 'invoice_id', 'l10n_ec_base_cero_iva', 'num', 15),
            (u'BASE GRAVA IVA', 'invoice_id', 'l10n_ec_base_doce_iva', 'num', 15),
            (u'VALOR IVA', 'invoice_id', 'l10n_ec_vat_doce_subtotal', 'num', 12),
            (u'Nro. RETENCIÓN', 'withholding_vat_number', '', 'std', 20),
            (u'AUTORIZACIÓN', 'withholding_vat_authorization', '', 'std', 40),
            (u'CONCEPTO RET. IVA', 'withholding_vat_name', '', 'std', 20),
            (u'BASE RET. IVA', 'withholding_vat_base', '', 'num', 15),
            (u'VALOR RET. IVA', 'withholding_vat_amt', '', 'num', 15),
            (u'CONCEPTO RET. RENTA', 'withholding_income_name', '', 'std', 20),
            (u'BASE RET. RENTA', 'withholding_income_base', '', 'num', 15),
            (u'VALOR RET. RENTA', 'withholding_income_amt', '', 'num', 15),
            (u'FORMA PAGO', 'invoice_id', 'l10n_ec_sri_payment_id.name', 'std', 25),
        ]

        titleheader = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 10, 'align': 'left'})
        titlesubheader = book.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'align': 'left'})
        bold = book.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 10})
        std = book.add_format({'font_name': 'Arial', 'font_size': 9})
        std_short = book.add_format({'font_name': 'Arial', 'font_size': 8})
        title = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 10,
             'align': 'center'})
        footer = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 10,
             'align': 'left'})
        perc = book.add_format({'font_name': 'Arial', 'font_size': 9, 'num_format': '0.00%'})
        datef = book.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'num_format': 'YYYY/mm/dd'})
        num = book.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00',
             'align': 'right'})
        num_footer = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 10,
             'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00', 'align': 'right'})
        num_bold = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 9, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00',
             'align': 'right'})

        l10n_ec_base_not_subject_to_vat = 0.0
        l10n_ec_base_cero_iva = 0.0
        l10n_ec_base_doce_iva = 0.0
        l10n_ec_vat_doce_subtotal = 0.0
        l10n_ec_wth_vat_base = 0.0
        l10n_ec_wth_vat_amt = 0.0
        l10n_ec_wth_income_base = 0.0
        l10n_ec_wth_income_amt = 0.0

        report_name = 'ANEXO 1 - DETALLE DE VENTAS'
        sheet = book.add_worksheet(report_name)
        sheet.write(0, 0, report_name, titleheader)
        sheet.write(1, 0, 'Reporte detallado de facturas de venta, con retenciones aplicadas y forma de pago prevista', titlesubheader)
        sheet.write(2, 0, 'Reporte auxiliar para el ATS y para el Formulario 101', titlesubheader)
        sheet.write(3, 0, self.company_id.l10n_ec_legal_name or self.company_id.name, bold)
        sheet.write(4, 0, "Desde el %s al %s" % (obj.date_from, obj.date_to), bold)
        row = 5
        for col, field in enumerate(FIELDS, 0):
            sheet.set_column(col, col, field[4])
            sheet.write(row + 1, col, field[0], title)
        row = 6
        invoices = obj.env['account.move'].search(obj._get_sales_detail_report_invoice_domain())
        for index, invoice_id in enumerate(invoices):
            if invoice_id.move_type == 'out_invoice':
                sign = 1
            else:
                sign = -1
            wth_values = obj._get_withholding_group_values(invoice_id)
            count = wth_values['max_count'] or 1
            for i in range(count):
                row += 1
                for col, (name, objt, attr, sty, width) in enumerate(FIELDS, 0):
                    if objt == 'index':
                        sheet.write(row, col, index + 1 or '', std)
                    elif objt == 'withholding_vat_number':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_vat']):
                                sheet.write(row, col, wth_values['withhold_vat'][i].get('withholding_number', ''), std)
                            elif i < len(wth_values['withhold_income_tax']):
                                sheet.write(row, col, wth_values['withhold_income_tax'][i].get('withholding_number', ''), std)
                        else:
                            sheet.write(row, col, '', std)
                    elif objt == 'withholding_vat_authorization':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_vat']):
                                sheet.write(row, col, wth_values['withhold_vat'][i].get('withholding_authorization', ''), std)
                            elif i < len(wth_values['withhold_income_tax']):
                                sheet.write(row, col, wth_values['withhold_income_tax'][i].get('withholding_authorization', ''), std)
                        else:
                            sheet.write(row, col, '', std)
                    elif objt == 'withholding_vat_name':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_vat']):
                                sheet.write(row, col, wth_values['withhold_vat'][i].get('withholding_name', ''), std)
                        else:
                            sheet.write(row, col, '', std)
                    elif objt == 'withholding_vat_base':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_vat']):
                                value = sign * wth_values['withhold_vat'][i].get('withholding_base', 0.0)
                                sheet.write(row, col, value, num)
                                l10n_ec_wth_vat_base += value
                            else:
                                sheet.write(row, col, 0.0, num)
                        else:
                            sheet.write(row, col, 0.0, num)
                    elif objt == 'withholding_vat_amt':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_vat']):
                                value = sign * wth_values['withhold_vat'][i].get('withholding_amt', 0.0)
                                sheet.write(row, col, value, num)
                                l10n_ec_wth_vat_amt += value
                            else:
                                sheet.write(row, col, 0.0, num)
                        else:
                            sheet.write(row, col, 0.0, num)
                    elif objt == 'withholding_income_name':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_income_tax']):
                                sheet.write(row, col, wth_values['withhold_income_tax'][i].get('withholding_name', ''), std)
                        else:
                            sheet.write(row, col, '', std)
                    elif objt == 'withholding_income_base':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_income_tax']):
                                value = sign * wth_values['withhold_income_tax'][i].get('withholding_base', 0.0)
                                sheet.write(row, col, value, num)
                                l10n_ec_wth_income_base += value
                            else:
                                sheet.write(row, col, 0.0, num)
                        else:
                            sheet.write(row, col, 0.0, num)
                    elif objt == 'withholding_income_amt':
                        if wth_values['max_count'] > 0:
                            if i < len(wth_values['withhold_income_tax']):
                                value = sign * wth_values['withhold_income_tax'][i].get('withholding_amt', 0.0)
                                sheet.write(row, col, value, num)
                                l10n_ec_wth_income_amt += value
                            else:
                                sheet.write(row, col, 0.0, num)
                        else:
                            sheet.write(row, col, 0.0, num)
                    else:
                        style = std
                        if sty == 'num':
                            style = num
                        elif sty == 'datef':
                            style = datef
                        if objt == 'invoice_id':
                            value = evalobj(invoice_id, attr)
                            if attr == 'l10n_ec_base_not_subject_to_vat' and i == 0:
                                value = sign * value
                                l10n_ec_base_not_subject_to_vat += value
                            elif attr == 'l10n_ec_base_cero_iva' and i == 0:
                                value = sign * value
                                l10n_ec_base_cero_iva += value
                            elif attr == 'l10n_ec_base_doce_iva' and i == 0:
                                value = sign * value
                                l10n_ec_base_doce_iva += value
                            elif attr == 'l10n_ec_vat_doce_subtotal' and i == 0:
                                value = sign * value
                                l10n_ec_vat_doce_subtotal += value
                            if sty != 'num':
                                sheet.write(row, col, value or '', style)
                            elif sty == 'num' and i == 0:
                                sheet.write(row, col, value or 0.0, style)
                            else:
                                sheet.write(row, col, 0.0, style)
        if invoices:
            row += 1
            sheet.write(row, 0, 'TOTAL REGISTROS: %s' % len(invoices), footer)
            sheet.write(row, 1, '', footer)
            sheet.write(row, 2, '', footer)
            sheet.write(row, 3, '', footer)
            sheet.write(row, 4, '', footer)
            sheet.write(row, 5, '', footer)
            sheet.write(row, 6, '', footer)
            sheet.write(row, 7, '', footer)
            sheet.write(row, 8, '', footer)
            sheet.write(row, 9, '', footer)
            sheet.write(row, 10, l10n_ec_base_not_subject_to_vat, num_footer)
            sheet.write(row, 11, l10n_ec_base_cero_iva, num_footer)
            sheet.write(row, 12, l10n_ec_base_doce_iva, num_footer)
            sheet.write(row, 13, l10n_ec_vat_doce_subtotal, num_footer)
            sheet.write(row, 14, '', footer)
            sheet.write(row, 15, '', footer)
            sheet.write(row, 16, '', footer)
            sheet.write(row, 17, l10n_ec_wth_vat_base, num_footer)
            sheet.write(row, 18, l10n_ec_wth_vat_amt, num_footer)
            sheet.write(row, 19, '', footer)
            sheet.write(row, 20, l10n_ec_wth_income_base, num_footer)
            sheet.write(row, 21, l10n_ec_wth_income_amt, num_footer)
            sheet.write(row, 22, '', footer)
        book.close()
        output.seek(0)
        generated_file = base64.b64encode(output.read())
        output.close()
        return self.env['l10n_ec.reports.base.file.report'].show(generated_file, report_name + '.xls')

    # Columns
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get(),
                                 required=True, help='')
    date_from = fields.Date('Date From', required=True, help='')
    date_to = fields.Date('Date To', required=True, help='')
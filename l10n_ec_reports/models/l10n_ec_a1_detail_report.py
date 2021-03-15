# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import base64
import io
from odoo.tools.misc import xlsxwriter


class L10nECA1DetailReport(models.TransientModel):
    _name = 'l10n_ec.a1.detail.report'

    def _get_sales_detail_report_invoice_domain(self):
        """
        Get base domain to search invoices
        :return: domain list
        """
        domain = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to)
        ]
        type = [('move_type', 'in', ('out_invoice', 'out_refund'))]
        if self.env.context.get('only_invoice'):
            type = [('move_type', '=', 'out_invoice')]
        if self.env.context.get('only_credit_note'):
            type = [('move_type', '=', 'out_refund')]
        domain.extend(type)
        return domain

    def _get_withholding_number(self, invoice_id):
        '''
        Se computa para obtener los numeros de retenciones.
        '''
        withholding_number = ''
        if invoice_id.l10n_ec_withhold_ids:
            for withholding in invoice_id.l10n_ec_withhold_ids.filtered(lambda w:w.state == 'posted'):
                if withholding_number:
                    withholding_number += ',' + withholding.name
                else:
                    withholding_number += withholding.name
        return withholding_number

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
            (u'CLIENTE', 'invoice_id', 'partner_id.name', 'std', 50),
            (u'PAR REL', 'invoice_id', 'partner_id.l10n_ec_related_part', 'std', 10),
            (u'TIPO COMP.', 'invoice_id', 'l10n_latam_document_type_id.display_name', 'std', 15),
            (u'NÚMERO DE DOCUMENTO', 'invoice_id', 'l10n_latam_document_number', 'std', 20),
            (u'F. EMISIÓN', 'invoice_id', 'invoice_date', 'datef', 10),
            (u'F. CONTABIL.', 'invoice_id', 'date', 'datef', 12),
            (u'BASE NO GRAVA IVA', 'invoice_id', 'l10n_ec_base_not_subject_to_vat', 'num', 20),
            (u'BASE IVA 0%', 'invoice_id', 'l10n_ec_base_cero_iva', 'num', 15),
            (u'BASE GRAVA IVA', 'invoice_id', 'l10n_ec_base_doce_iva', 'num', 15),
            (u'VALOR IVA', 'invoice_id', 'l10n_ec_vat_doce_subtotal', 'num', 12),
            (u'Nro. RETENCIÓN', 'withholding', '', 'std', 20),
            (u'FORMA PAGO', 'invoice_id', 'l10n_ec_payment_method_id.name', 'std', 25),
        ]

        titleheader = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 11, 'valign': 'vjustify', 'align': 'center'})
        titlesubheader = book.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'valign': 'vjustify', 'align': 'center'})
        bold = book.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 11, 'valign': 'vjustify'})
        std = book.add_format({'font_name': 'Arial', 'font_size': 10, 'valign': 'vjustify'})
        std_short = book.add_format({'font_name': 'Arial', 'font_size': 8, 'valign': 'vjustify'})
        title = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 11,
             'align': 'center', 'valign': 'vjustify'})
        footer = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 11,
             'align': 'left', 'valign': 'vjustify'})
        perc = book.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': '0.00%', 'valign': 'vjustify'})
        datef = book.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'num_format': 'YYYY/mm/dd', 'valign': 'vjustify'})
        num = book.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00',
             'align': 'right', 'valign': 'vjustify'})
        num_footer = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 11,
             'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00', 'align': 'left', 'valign': 'vjustify'})
        num_bold = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 10, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00',
             'align': 'right', 'valign': 'vjustify'})

        l10n_ec_base_not_subject_to_vat = 0.0
        l10n_ec_base_cero_iva = 0.0
        l10n_ec_base_doce_iva = 0.0
        l10n_ec_vat_doce_subtotal = 0.0

        report_name = 'ANEXO 1 - DETALLE DE VENTAS'
        sheet = book.add_worksheet(report_name)
        sheet.merge_range(0, 0, 0, 4, report_name, titleheader)
        sheet.merge_range(1, 0, 1, 4, 'Reporte detallado de facturas de venta, con retenciones aplicadas y forma de pago prevista', titlesubheader)
        sheet.merge_range(2, 0, 2, 4, 'Reporte auxiliar para el ATS y para el Formulario 101', titlesubheader)
        sheet.merge_range(3, 0, 3, 4, self.company_id.l10n_ec_legal_name or self.company_id.name, bold)
        sheet.merge_range(4, 0, 4, 4, "Desde el %s al %s" % (obj.date_from, obj.date_to), bold)
        row = 5
        for col, field in enumerate(FIELDS, 0):
            sheet.set_column(col, col, field[4])
            sheet.write(row + 1, col, field[0], title)
        row = 6
        invoices = obj.env['account.move'].search(obj._get_sales_detail_report_invoice_domain())
        for index, invoice_id in enumerate(invoices):
            row += 1
            for col, (name, objt, attr, sty, width) in enumerate(FIELDS, 0):
                if objt == 'index':
                    sheet.write(row, col, index + 1 or '', std)
                elif objt == 'withholding':
                    sheet.write(row, col, obj._get_withholding_number(invoice_id), std)
                else:
                    style = std
                    if sty == 'num':
                        style = num
                    elif sty == 'datef':
                        style = datef
                    if objt == 'invoice_id':
                        value = evalobj(invoice_id, attr)
                        if attr == 'l10n_ec_base_not_subject_to_vat':
                            l10n_ec_base_not_subject_to_vat += value
                        elif attr == 'l10n_ec_base_cero_iva':
                            l10n_ec_base_cero_iva += value
                        elif attr == 'l10n_ec_base_doce_iva':
                            l10n_ec_base_doce_iva += value
                        elif attr == 'l10n_ec_vat_doce_subtotal':
                            l10n_ec_vat_doce_subtotal += value
                        if sty != 'num':
                            sheet.write(row, col, value or '', style)
                        else:
                            sheet.write(row, col, value or 0.0, style)
        if invoices:
            row += 1
            sheet.merge_range(row, 0, row, 8, 'TOTAL REGISTROS: ' + len(invoices), footer)
            sheet.write(row, 9, l10n_ec_base_not_subject_to_vat, num_footer)
            sheet.write(row, 10, l10n_ec_base_cero_iva, num_footer)
            sheet.write(row, 11, l10n_ec_base_doce_iva, num_footer)
            sheet.write(row, 12, l10n_ec_vat_doce_subtotal, num_footer)
            sheet.write(row, 13, '', footer)
            sheet.write(row, 14, '', footer)
        book.close()
        output.seek(0)
        generated_file = base64.b64encode(output.read())
        output.close()
        return self.env['base.file.report'].show(generated_file, report_name + '.xls')

    # Columns
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get(),
                                 required=True, help='')
    date_from = fields.Date('Date From', required=True, help='')
    date_to = fields.Date('Date To', required=True, help='')
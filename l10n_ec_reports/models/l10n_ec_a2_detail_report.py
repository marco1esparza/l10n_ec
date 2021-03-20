# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import base64
import io
from odoo.tools.misc import xlsxwriter
from datetime import datetime


class L10nECA2DetailReport(models.TransientModel):
    _name = 'l10n_ec.a2.detail.report'

    def _get_purchase_deduction_report_invoice_tax_domain(self):
        """
        Get base domain to search invoices taxes
        :return: domain list
        """
        domain = [('move_id.state', '=', 'posted'),
                  ('move_id.country_code', '=', 'EC'),
                  ('move_id.l10n_ec_withhold_type', '=', 'in_withhold'),
                  ('move_id.l10n_latam_document_type_id.code', '=', '07'),
                  ('move_id.invoice_date', '>=', self.date_from),
                  ('move_id.invoice_date', '<=', self.date_to),
                  ('tax_id.l10n_ec_type', '=', 'withhold_income_tax'),
                  ]
        return domain

    def print_xls(self):
        '''
        Imprimir reporte en XLS.
        '''
        output = io.BytesIO()
        book = xlsxwriter.Workbook(output, {'in_memory': True})
        obj = self

        titleheader = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 11, 'align': 'left'})
        titlesubheader = book.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'align': 'left'})
        bold = book.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 11})
        std = book.add_format({'font_name': 'Arial', 'font_size': 10})
        std_center = book.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'center'})
        std_short = book.add_format({'font_name': 'Arial', 'font_size': 8})
        title_lightb = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#FFD9B3', 'font_size': 9,
             'align': 'center'})
        title_lightg = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C6ECC6', 'font_size': 9,
             'align': 'center'})
        title = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 9,
             'align': 'center'})
        footer = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 9,
             'align': 'left'})
        perc = book.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': '0.00%'})
        datef = book.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'num_format': 'YYYY/mm/dd'})
        num = book.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00',
             'align': 'right'})
        num_footer = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C3CDE6', 'font_size': 9,
             'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00', 'align': 'right'})
        num_footer_g = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'bg_color': '#C6ECC6', 'font_size': 9,
             'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00', 'align': 'right'})
        num_bold = book.add_format(
            {'font_name': 'Arial', 'bold': True, 'font_size': 10, 'num_format': '[$$-300A]#,##0.00;[$$-300A]-#,##0.00',
             'align': 'right'})

        report_name = 'ANEXO 2 - DETALLE DE RETENCIONES IMPUESTO A LA RENTA POR CÓDIGO'
        sheet = book.add_worksheet(report_name)
        sheet.write(0, 0, report_name, titleheader)
        sheet.write(1, 0, 'Reporte detallado de códigos de retención del impuesto a la renta aplicados a las compras, agrupados y subtotalizados por código. Incluye detalle de la retención y de la compra correspondiente.', titlesubheader)
        sheet.write(2, 0, 'Reporte auxiliar para el ATS y para el Formulario 103', titlesubheader)
        sheet.write(3, 0, self.company_id.l10n_ec_legal_name or self.company_id.name, bold)
        sheet.write(4, 0, "Desde el %s al %s" % (obj.date_from, obj.date_to), bold)
        row = 6
        tax_lines = obj.env['l10n_ec.account.withhold.line'].search(obj._get_purchase_deduction_report_invoice_tax_domain())
        if tax_lines:
            sheet.set_column(0, 0, 6)
            sheet.write(row, 0, '', title)
            sheet.write(row + 1, 0, u'ITEM', title)
            sheet.set_column(1, 1, 15)
            sheet.write(row, 1, '', title)
            sheet.write(row + 1, 1, u'NÚMERO FACTURA', title)
            sheet.set_column(2, 2, 15)
            sheet.write(row, 2, '', title)
            sheet.write(row + 1, 2, u'NÚMERO RETENCIÓN', title)
            sheet.set_column(3, 3, 10)
            sheet.write(row, 3, '', title)
            sheet.write(row + 1, 3, u'SUS. TRIB.', title)
            sheet.set_column(4, 4, 6)
            sheet.write(row, 4, '', title)
            sheet.write(row + 1, 4, u'TIPO ID.', title)
            sheet.set_column(5, 5, 12)
            sheet.write(row, 5, '', title)
            sheet.write(row + 1, 5, u'NRO. RUC/C.I.', title)
            sheet.set_column(6, 6, 50)
            sheet.write(row, 6, '', title)
            sheet.write(row + 1, 6, u'CLIENTE', title)
            sheet.write(row, 7, '', title_lightb)
            sheet.write(row, 8, u'DOCUMENTO DE COMPRA', title_lightb)
            sheet.write(row, 9, '', title_lightb)
            sheet.set_column(7, 7, 25)
            sheet.write(row + 1, 7, u'TIPO COMP.', title_lightb)
            sheet.set_column(8, 8, 10)
            sheet.write(row + 1, 8, u'F. EMISIÓN', title_lightb)
            sheet.set_column(9, 9, 10)
            sheet.write(row + 1, 9, u'F. CONTAB.',title_lightb)
            sheet.write(row, 10, '', title_lightg)
            sheet.write(row, 11, '', title_lightg)
            sheet.write(row, 12, '', title_lightg)
            sheet.write(row, 13, '', title_lightg)
            sheet.write(row, 14, '', title_lightg)
            sheet.write(row, 15, u'RETENCIÓN EN LA FUENTE', title_lightg)
            sheet.write(row, 16, '', title_lightg)
            sheet.write(row, 17, '', title_lightg)
            sheet.write(row, 18, '', title_lightg)
            sheet.write(row, 19, '', title_lightg)
            sheet.write(row, 20, '', title_lightg)
            sheet.set_column(10, 10, 8)
            sheet.write(row + 1, 10, u'COD', title_lightg)
            sheet.set_column(11, 11, 15)
            sheet.write(row + 1, 11, u'B. EXENTA IVA', title_lightg)
            sheet.set_column(12, 12, 15)
            sheet.write(row + 1, 12, u'NO OBJ. IVA', title_lightg)
            sheet.set_column(13, 13, 15)
            sheet.write(row + 1, 13, u'BASE IVA 0%', title_lightg)
            sheet.set_column(14, 14, 15)
            sheet.write(row + 1, 14, u'BASE IVA 12%', title_lightg)
            sheet.set_column(15, 15, 15)
            sheet.write(row + 1, 15, u'BASE IMP.', title_lightg)
            sheet.set_column(16, 16, 5)
            sheet.write(row + 1, 16, u'%', title_lightg)
            sheet.set_column(17, 17, 15)
            sheet.write(row + 1, 17, u'MONTO', title_lightg)
            sheet.set_column(18, 18, 15)
            sheet.write(row + 1, 18, u'SERIE', title_lightg)
            sheet.set_column(19, 19, 25)
            sheet.write(row + 1, 19, u'NRO. AUTORIZACIÓN', title_lightg)
            sheet.set_column(20, 20, 12)
            sheet.write(row + 1, 20, u'FECHA', title_lightg)
            row = 8
            group_by_code = {}
            totals = {'total_base_exenta_iva': 0.00, 'total_no_objeto_iva': 0.00, 'total_base_cero': 0.00,
                      'total_base_doce': 0.00,
                      'total_base': 0.00, 'total_amount': 0.00, 'row_count': len(tax_lines)}
            ats_code_list = []
            # Group invoices tax by code
            for line in tax_lines:
                if line.tax_id.l10n_ec_code_ats in group_by_code:
                    group_by_code[line.tax_id.l10n_ec_code_ats]['line_ids'].append(line)
                    group_by_code[line.tax_id.l10n_ec_code_ats]['total_base_exenta_iva'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_tax_free
                    group_by_code[line.tax_id.l10n_ec_code_ats]['total_no_objeto_iva'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_not_subject_to_vat
                    group_by_code[line.tax_id.l10n_ec_code_ats]['total_base_cero'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_cero_iva
                    group_by_code[line.tax_id.l10n_ec_code_ats]['total_base_doce'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_doce_iva
                    group_by_code[line.tax_id.l10n_ec_code_ats]['total_base'] += line.base
                    group_by_code[line.tax_id.l10n_ec_code_ats]['total_amount'] += line.amount
                else:
                    group_by_code[line.tax_id.l10n_ec_code_ats] = {
                        'line_ids': [line],
                        'total_base_exenta_iva': line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_tax_free,
                        'total_no_objeto_iva': line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_not_subject_to_vat,
                        'total_base_cero': line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_cero_iva,
                        'total_base_doce': line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_doce_iva,
                        'total_base': line.base,
                        'total_amount': line.amount
                    }
                    ats_code_list.append(line.tax_id.l10n_ec_code_ats)
                # Summarize base and amount
                totals['total_base_exenta_iva'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_tax_free
                totals['total_no_objeto_iva'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_not_subject_to_vat
                totals['total_base_cero'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_cero_iva
                totals['total_base_doce'] += line.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_doce_iva
                totals['total_base'] += line.base
                totals['total_amount'] += line.amount
            # Order reference list alphabetically
            ats_code_list.sort()
            for tax_code in ats_code_list:
                grouped_values = group_by_code[tax_code]
                grouped_invoice_tax_ids = grouped_values.get('line_ids')
                sheet.write(row, 0, u'CÓDIGO RETENCIÓN EN LA FUENTE: %s' % tax_code, footer)
                sheet.write(row, 1, '', title)
                sheet.write(row, 2, '', title)
                sheet.write(row, 3, '', title)
                sheet.write(row, 4, '', title)
                sheet.write(row, 5, '', title)
                sheet.write(row, 6, '', title)
                sheet.write(row, 7, '', title_lightb)
                sheet.write(row, 8, '', title_lightb)
                sheet.write(row, 9, '', title_lightb)
                sheet.write(row, 10, '', title_lightg)
                sheet.write(row, 11, '', title_lightg)
                sheet.write(row, 12, '', title_lightg)
                sheet.write(row, 13, '', title_lightg)
                sheet.write(row, 14, '', title_lightg)
                sheet.write(row, 15, '', title_lightg)
                sheet.write(row, 16, '', title_lightg)
                sheet.write(row, 17, '', title_lightg)
                sheet.write(row, 18, '', title_lightg)
                sheet.write(row, 19, '', title_lightg)
                sheet.write(row, 20, '', title_lightg)
                grouped_invoice_tax_ids.sort(key=lambda r: r.move_id.invoice_date)
                for index, invoice_tax in enumerate(grouped_invoice_tax_ids):
                    row += 1
                    sheet.write(row, 0, index + 1, std_center)
                    sheet.write(row, 1, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_latam_document_number, std)
                    sheet.write(row, 2, invoice_tax.move_id.l10n_latam_document_number, std)
                    sheet.write(row, 3, invoice_tax.move_id.l10n_ec_sri_tax_support_id.code, std_center)
                    sheet.write(row, 4, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_ec_transaction_type, std_center)
                    sheet.write(row, 5, invoice_tax.move_id.partner_id.commercial_partner_id.vat, std)
                    sheet.write(row, 6, invoice_tax.move_id.partner_id.commercial_partner_id.name, std)
                    sheet.write(row, 7, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_latam_document_type_id.display_name, std)
                    sheet.write(row, 8, invoice_tax.move_id.l10n_ec_withhold_origin_ids.invoice_date, datef)
                    sheet.write(row, 9, invoice_tax.move_id.l10n_ec_withhold_origin_ids.date or invoice_tax.move_id.l10n_ec_withhold_origin_ids.invoice_date, datef)
                    sheet.write(row, 10, invoice_tax.tax_id.l10n_ec_code_ats, std_center)
                    sheet.write(row, 11, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_tax_free, num)
                    sheet.write(row, 12, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_not_subject_to_vat, num)
                    sheet.write(row, 13, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_cero_iva, num)
                    sheet.write(row, 14, invoice_tax.move_id.l10n_ec_withhold_origin_ids.l10n_ec_base_doce_iva, num)
                    sheet.write(row, 15, invoice_tax.base, num)
                    sheet.write(row, 16, '%s%%' % int(invoice_tax.tax_id.amount * -1), num)
                    sheet.write(row, 17, invoice_tax.amount * -1, num)
                    sheet.write(row, 18, invoice_tax.move_id.l10n_latam_document_number, std)
                    authorization_name = invoice_tax.move_id.l10n_ec_authorization or ''
                    sheet.write(row, 19, authorization_name, std)
                    withhold_date = invoice_tax.move_id.invoice_date
                    sheet.write(row, 20, withhold_date, datef)
                # Write group subtotals
                row += 1
                sheet.write(row, 0, u'TOTAL REGISTROS X CÓDIGO: %s' % len(grouped_invoice_tax_ids), footer)
                sheet.write(row, 1, '', title)
                sheet.write(row, 2, '', title)
                sheet.write(row, 3, '', title)
                sheet.write(row, 4, '', title)
                sheet.write(row, 5, '', title)
                sheet.write(row, 6, '', title)
                sheet.write(row, 7, '', title_lightb)
                sheet.write(row, 8, '', title_lightb)
                sheet.write(row, 9, '', title_lightb)
                sheet.write(row, 10, '', title_lightg)
                sheet.write(row, 11, grouped_values.get('total_base_exenta_iva'), num_footer_g)
                sheet.write(row, 12, grouped_values.get('total_no_objeto_iva'), num_footer_g)
                sheet.write(row, 13, grouped_values.get('total_base_cero'), num_footer_g)
                sheet.write(row, 14, grouped_values.get('total_base_doce'), num_footer_g)
                sheet.write(row, 15, grouped_values.get('total_base'), num_footer_g)
                sheet.write(row, 16, '', title_lightg)
                sheet.write(row, 17, float(grouped_values.get('total_amount')) * -1, num_footer_g)
                sheet.write(row, 18, '', title_lightg)
                sheet.write(row, 19, '', title_lightg)
                sheet.write(row, 20, '', title_lightg)
                # Increase to leave white line
                row += 1
                # Set line height to half
                sheet.set_row(row, height=6)
                # Increase to continue writing
                row += 1
            sheet.write(row, 0, u'REGISTROS TOTALES: %s' % totals.get('row_count', 0), footer)
            sheet.write(row, 1, '', title)
            sheet.write(row, 2, '', title)
            sheet.write(row, 3, '', title)
            sheet.write(row, 4, '', title)
            sheet.write(row, 5, '', title)
            sheet.write(row, 6, '', title)
            sheet.write(row, 7, '', title_lightb)
            sheet.write(row, 8, '', title_lightb)
            sheet.write(row, 9, '', title_lightb)
            sheet.write(row, 10, '', title_lightg)
            sheet.write(row, 11, totals.get('total_base_exenta_iva'), num_footer_g)
            sheet.write(row, 12, totals.get('total_no_objeto_iva'), num_footer_g)
            sheet.write(row, 13, totals.get('total_base_cero'), num_footer_g)
            sheet.write(row, 14, totals.get('total_base_doce'), num_footer_g)
            sheet.write(row, 15, totals.get('total_base'), num_footer_g)
            sheet.write(row, 16, '', title_lightg)
            sheet.write(row, 17, float(totals.get('total_amount')) * -1, num_footer_g)
            sheet.write(row, 18, '', title_lightg)
            sheet.write(row, 19, '', title_lightg)
            sheet.write(row, 20, '', title_lightg)

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
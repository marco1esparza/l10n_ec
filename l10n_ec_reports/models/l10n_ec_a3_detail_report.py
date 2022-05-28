# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import base64
import io
from odoo.tools.misc import xlsxwriter


class L10nECA3DetailReport(models.TransientModel):
    _name = 'l10n_ec.a3.detail.report'
    _description = 'l10n_ec.a3.detail.report'

    def _get_purchase_detail_report_invoice_domain(self):
        """
        Get base domain to search invoices
        :return: domain list
        """
        domain = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to)
        ]
        type = [('move_type', 'in', ('in_invoice', 'in_refund'))]
        if self.env.context.get('only_invoice'):
            type = [('move_type', '=', 'in_invoice')]
        if self.env.context.get('only_credit_note'):
            type = [('move_type', '=', 'in_refund')]
        domain.extend(type)
        return domain

    def _get_withholding_data(self, invoice_id):
        '''
        Se computa para obtener los numeros de retenciones y autorizaciones
        '''
        withholding_number = ''
        withholding_authorization = ''
        if invoice_id.l10n_ec_withhold_ids:
            for withhold in invoice_id.l10n_ec_withhold_ids.filtered(lambda w: w.state == 'posted'):
                if withholding_number:
                    withholding_number += ',' + withhold.name
                else:
                    withholding_number += withhold.name
                if withholding_authorization:
                    withholding_authorization += ',' + withhold.l10n_ec_authorization
                else:
                    withholding_authorization += withhold.l10n_ec_authorization
        return withholding_number, withholding_authorization

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
            (u'RUC/CI', 'invoice_id', 'partner_id.vat', 'std', 10),
            (u'PROVEEDOR', 'invoice_id', 'partner_id.name', 'std', 40),
            (u'TIPO COMP.', 'invoice_id', 'l10n_latam_document_type_id.display_name', 'std', 15),
            (u'NÚMERO DE DOCUMENTO', 'invoice_id', 'l10n_latam_document_number', 'std', 20),
            (u'REFERENCIA', 'invoice_id', 'ref', 'std', 40),
            (u'F. EMISIÓN', 'invoice_id', 'invoice_date', 'datef', 10),
            (u'F. CONTABIL.', 'invoice_id', 'date', 'datef', 12),
            (u'BASE NO GRAVA IVA', 'invoice_id', 'l10n_ec_base_not_subject_to_vat', 'num', 20),
            (u'BASE IVA 0%', 'invoice_id', 'l10n_ec_base_cero_iva', 'num', 15),
            (u'BASE GRAVA IVA', 'invoice_id', 'l10n_ec_base_doce_iva', 'num', 15),
            (u'VALOR IVA', 'invoice_id', 'l10n_ec_vat_doce_subtotal', 'num', 12),
            (u'Nro. RETENCIÓN', 'withholding_number', '', 'std', 20),
            (u'AUTORIZACIÓN', 'withholding_authorization', '', 'std', 40),
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

        report_name = 'ANEXO 3 - DETALLE DE COMPRAS'
        sheet = book.add_worksheet(report_name)
        sheet.write(0, 0, report_name, titleheader)
        sheet.write(1, 0, 'Reporte detallado de facturas de compras, con retenciones aplicadas y forma de pago prevista', titlesubheader)
        sheet.write(2, 0, 'Reporte auxiliar para el Formulario 104', titlesubheader)
        sheet.write(3, 0, self.company_id.l10n_ec_legal_name or self.company_id.name, bold)
        sheet.write(4, 0, "Desde el %s al %s" % (obj.date_from, obj.date_to), bold)
        row = 5
        for col, field in enumerate(FIELDS, 0):
            sheet.set_column(col, col, field[4])
            sheet.write(row + 1, col, field[0], title)
        row = 6
        invoices = obj.env['account.move'].search(obj._get_purchase_detail_report_invoice_domain())
        for index, invoice_id in enumerate(invoices):
            row += 1
            if invoice_id.move_type == 'in_invoice':
                sign = 1
            else:
                sign = -1
            for col, (name, objt, attr, sty, width) in enumerate(FIELDS, 0):
                if objt == 'index':
                    sheet.write(row, col, index + 1 or '', std)
                elif objt == 'withholding_number':
                    sheet.write(row, col, obj._get_withholding_data(invoice_id)[0], std)
                elif objt == 'withholding_authorization':
                    sheet.write(row, col, obj._get_withholding_data(invoice_id)[1], std)
                else:
                    style = std
                    if sty == 'num':
                        style = num
                    elif sty == 'datef':
                        style = datef
                    if objt == 'invoice_id':
                        value = evalobj(invoice_id, attr)
                        if attr == 'l10n_ec_base_not_subject_to_vat':
                            value = sign * value
                            l10n_ec_base_not_subject_to_vat += value
                        elif attr == 'l10n_ec_base_cero_iva':
                            value = sign * value
                            l10n_ec_base_cero_iva += value
                        elif attr == 'l10n_ec_base_doce_iva':
                            value = sign * value
                            l10n_ec_base_doce_iva += value
                        elif attr == 'l10n_ec_vat_doce_subtotal':
                            value = sign * value
                            l10n_ec_vat_doce_subtotal += value
                        if sty != 'num':
                            sheet.write(row, col, value or '', style)
                        else:
                            sheet.write(row, col, value or 0.0, style)
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
            sheet.write(row, 8, l10n_ec_base_not_subject_to_vat, num_footer)
            sheet.write(row, 9, l10n_ec_base_cero_iva, num_footer)
            sheet.write(row, 10, l10n_ec_base_doce_iva, num_footer)
            sheet.write(row, 11, l10n_ec_vat_doce_subtotal, num_footer)
            sheet.write(row, 12, '', footer)
            sheet.write(row, 13, '', footer)
            sheet.write(row, 14, '', footer)
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
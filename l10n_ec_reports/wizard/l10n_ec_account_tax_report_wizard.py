# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
import calendar


class AccountTaxReportWizard(models.TransientModel):
    _name = 'l10n_ec.account.tax.report.wizard'

    @api.model
    def _get_group_taxes(self):
        '''
        Se obtienen el formulario a mostrar 103 o 104 en field Selection.
        '''
        group_taxes = []
        tax_group = self.env.ref('l10n_ec.ec_tax_group_withhold_vat')
        group_taxes += [(tax_group.id, tax_group.name)]
        tax_group = self.env.ref('l10n_ec.ec_tax_group_withhold_income')
        group_taxes += [(tax_group.id, tax_group.name)]
        return group_taxes

    @api.model
    def _get_tax_group(self):
        '''
        Se obtienen el formulario a mostrar 103 o 104 o ambos, en salida de reporte.
        '''
        group_tax = [0]
        if self.env.context.get('origin') == 'form_103':
            tax_group = self.env['account.tax.group'].search([('l10n_ec_type', '=', 'withhold_income_tax')])
            group_tax.append(tax_group.id)
        elif self.env.context.get('origin') == 'form_104':
            tax_group = self.env['account.tax.group'].search([('l10n_ec_type', 'in',
                                                               ['withhold_vat', 'vat12', 'vat14', 'zero_vat', 'not_charged_vat', 'exempt_vat'])])
            if len(tax_group) > 1:
                group_tax = tax_group.ids
            else:
                group_tax.append(tax_group.ids)
        return tuple(group_tax)

    @api.model
    def _get_invoices_tax(self):
        '''
        Obtener informacion de impuestos.
        '''
        params = []
        sql = """
            select
                ai.id as invoice_id,
                ai.move_type,
                t.id as tax_id,
                t.tax_group_id,
                t.name as taxname,
                case
                    when move_type='in_refund' then ait.tax_base_amount *-1
                    when move_type!='in_refund' then abs(ait.tax_base_amount)
                end as base,
                case
                    when move_type='in_refund' then ait.balance
                    when move_type!='in_refund' then abs(ait.balance)
                end as amount,
                ait.account_id,
                abs(t.amount) as perc
            from account_move ai
                join account_move_line ait on ai.id = ait.move_id and exclude_from_invoice_tab
                join account_tax t on ait.tax_line_id = t.id
            where ai.state in ('posted') """
        if self.date_from:
            sql += " AND ai.invoice_date >= %s "
            params.append(self.date_from)
        if self.date_to:
            sql += " AND ai.invoice_date <= %s "
            params.append(self.date_to)
        if self.company_id:
            sql += " AND ai.company_id = %s "
            params.append(self.company_id.id)
        sql += " AND t.tax_group_id IN %s "
        params.append(self._get_tax_group())
        sql += "ORDER BY t.id, ai.invoice_date, ai.id"
        self._cr.execute(sql, tuple(params))
        res = self._cr.fetchall()
        return res

    @api.onchange('date_from')
    def onchange_date_from(self):
        '''
        Setea la fecha de inicio y fin.
        '''
        if not self.date_from:
            today = datetime.now()
            date_from = datetime.strptime('%s-%s-01' % (today.year, today.month), DEFAULT_SERVER_DATE_FORMAT)
            self.date_from = date_from
        else:
            date_from = self.date_from
            self.date_from = datetime.strptime('%s-%s-01' % (date_from.year, date_from.month),
                                               DEFAULT_SERVER_DATE_FORMAT)
        self.date_to = datetime.strptime('%s-%s-%s' % (date_from.year, date_from.month,
                                                       calendar.monthrange(date_from.year, date_from.month)[1]),
                                         DEFAULT_SERVER_DATE_FORMAT)

    def group_taxe_line(self, invoice_taxes):
        '''
        Se computa la informacion de impuestos.
        '''
        group = {}
        for tax in invoice_taxes:
            base = tax[5]
            amount = tax[6]
            l10n_ec_type = self.env['account.tax.group'].browse(tax[3]).l10n_ec_type
            if tax[1] == 'out_refund':
                base *= -1
                amount *= -1
            if l10n_ec_type in ('withhold_vat', 'withhold_income_tax'):
                amount *= -1
            invoice = {'invoice_id': tax[0],
                       'tax_id': tax[2],
                       'tax_name': tax[4],
                       'tax_group_id': tax[3],
                       'base': base,
                       'amount': amount,
                       'perc': tax[8],
                       'account_id': tax[7],
                       'type': tax[1]
                       }
            values = group.get(tax[2], {'base': 0.0, 'amount': 0.0, 'invoice_ids': []})
            values.update({
                'tax_id': tax[2],
                'tax_name': tax[4],
                'base': values['base'] + base,
                'amount': values['amount'] + amount,
                'perc': tax[8],
                'tax_group_id': tax[3],
                'invoice_ids': values['invoice_ids'] + [invoice]
            })
            group[tax[2]] = values
        return group.values()

    def show_report_account_tax(self):
        '''
        se muestra la informacion en ventana.
        '''
        invoice_taxes = self._get_invoices_tax()
        if invoice_taxes:
            taxes_group = self.group_taxe_line(invoice_taxes)
            form = self.env['l10n_ec.account.tax.form.header'].create({'date_from': self.date_from,
                                                               'date_to': self.date_to,
                                                               'company_id': self.company_id.id})
            for tax in taxes_group:
                group = self.env['l10n_ec.account.tax.form.group'].with_context({'recompute': False}).create({'account_tax_header_id': form.id,
                                                                   'tax_id': tax['tax_id'],
                                                                   'tax_name': tax['tax_name'],
                                                                   'base': tax['base'],
                                                                   'amount': tax['amount'],
                                                                   'perc': tax['perc'],
                                                                   'tax_group_id': tax['tax_group_id'],
                                                                   'currency_id': self.company_id.currency_id.id})
                for invoice in tax['invoice_ids']:
                    record = self.env['l10n_ec.account.tax.form.line'].create({'account_tax_group_id': group.id,
                                                                       'invoice_id': invoice['invoice_id'],
                                                                       'tax_id': invoice['tax_id'],
                                                                       'tax_name': invoice['tax_name'],
                                                                       'tax_group_id': invoice['tax_group_id'],
                                                                       'account_id': invoice['account_id'],
                                                                       'base': invoice['base'],
                                                                       'amount': invoice['amount'],
                                                                       'perc': invoice['perc'],
                                                                       'currency_id': self.company_id.currency_id.id})

            action = {
                'name': 'Account Tax Form',
                'view_mode': 'form',
                'res_model': 'l10n_ec.account.tax.form.header',
                'view_id': self.env.ref('l10n_ec_reports.view_account_tax_form_header_form').id,
                'type': 'ir.actions.act_window',
                'context': self._context.copy(),
                'res_id': form.id,
            }
            return action
        else:
            raise UserError('No hay registros para mostrar en este período.')

    #Columns
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get(),
                                 required=True, help='')
    date_from = fields.Date('Date From', required=True, help='')
    date_to = fields.Date('Date To', required=True, help='')

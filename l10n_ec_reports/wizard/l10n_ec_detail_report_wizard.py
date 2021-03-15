# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError


class L10nECDetailReportWizard(models.TransientModel):
    _name = 'l10n_ec.detail.report.wizard'

    def show_detail_report(self):
        report = False
        if self.env.context.get('show_report', False) == 'report_A1':
            report = self.env['l10n_ec.a1.detail.report'].create({'date_from': self.date_from,
                                                                  'date_to': self.date_to,
                                                                  'company_id': self.company_id.id})
        elif self.env.context.get('show_report', False) == 'report_A2':
            report = self.env['l10n_ec.a2.detail.report'].create({'date_from': self.date_from,
                                                                  'date_to': self.date_to,
                                                                  'company_id': self.company_id.id})
        else:
            raise UserError('No ha seleccionado un reporte valido.')
        if report:
            return report.print_xls()

    # Columns
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get(),
                                 required=True, help='')
    date_from = fields.Date('Date From', required=True, help='')
    date_to = fields.Date('Date To', required=True, help='')

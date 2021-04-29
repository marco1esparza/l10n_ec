# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class WizardReportTrialGeneral(models.TransientModel):
    _name = 'wizard.report.trial.balance'
    _description = "Trial General"

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries'),
                                    ], string='Target Moves', required=True, default='posted')
    hide_account_balance_at_0 = fields.Boolean(
        string='Hide account ending balance at 0',
        help='Use this filter to hide an account or a partner '
             'with an ending balance at 0. '
             'If partners are filtered, '
             'debits and credits totals will not match the trial balance.',
        default=True,
    )

    def button_export(self):
        """
        Se utiliza el reporte trial balance(sumas y saldos) para generar este basado en lo que se pide en
        el asistente.
        """
        self.ensure_one()
        trial_wizard_dict = {
            'date_from': max([self.date_from, self.company_id.invoicing_switch_threshold or self.date_from]),
            'date_to': self.date_to,
            'target_move': self.target_move,
            'hide_account_at_0': self.hide_account_balance_at_0,
            'account_ids': self.env['account.account'].search(
                [('company_id', '=', self.company_id.id), '|', '|', '|', '|', '|', '|', '|', '|',
                 ('code', '=like', '1%'), ('code', '=like', '2%'), ('code', '=like', '3%'),
                 ('code', '=like', '4%'), ('code', '=like', '5%'), ('code', '=like', '6%'),
                 ('code', '=like', '7%'), ('code', '=like', '8%'), ('code', '=like', '9%')]
            ).ids,
            'hierarchy_on': 'relation',
            'company_id': self.company_id.id,
        }
        trial_wizard_id = self.env['trial.balance.report.wizard'].create(trial_wizard_dict)
        four_and_five_account_ids = []
        return trial_wizard_id.with_context({
            'show_signatures': True,
            'custom_report_name': 'Balance de Comprobación',
            'pretty_rows': True,
            'show_4_and_5': four_and_five_account_ids,
            'unaffected_earnings_account': False,
        }).button_export_xlsx()
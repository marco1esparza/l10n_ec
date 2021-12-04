# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class WizardReportBalanceResultados(models.TransientModel):
    _name = 'wizard.report.balance.resultados'
    _description = "Perdidas y Ganancias"

    def _get_fisrt_day(self):
        """
        Obtiene el primer dia del anno
        """
        today = fields.Date.context_today(self)
        dateYearStart = "%s-01-01" % (today.year)
        return datetime.strptime(dateYearStart, DEFAULT_SERVER_DATE_FORMAT)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=_get_fisrt_day
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today
    )
    target_move = fields.Selection(
        [('posted', 'All Posted Entries'),
         ('all', 'All Entries')],
        string='Target Moves',
        required=True,
        default='posted')
    account_ids = fields.Many2many(
        'account.account', string='Filter accounts'
    )
    level = fields.Selection(
        [('1', '1'),
         ('2', '2'),
         ('3', '3'),
         ('4', '4'),
         ('5', '5'),
         ('6', '6'),
         ('7', '7'),
         ('8', '8'),
         ('9', '9'),
         ('10', '10'),
         ('all', 'Todos')
         ],
        string='Nivel',
        required=True,
        default='all'
        )
    hide_account_balance_at_0 = fields.Boolean(
        string='Hide account ending balance at 0',
        help='Use this filter to hide an account or a partner '
             'with an ending balance at 0. '
             'If partners are filtered, '
             'debits and credits totals will not match the trial balance.',
        default=True,
    )

    @api.model
    def validate_data(self, trial_wizard_id):
        """
        Valida los datos del asistente:
        - Las fechas no pueden pertenecer a annos diferentes.
        """
        year_start = fields.Date.to_date(trial_wizard_id.date_from).year
        year_end = fields.Date.to_date(trial_wizard_id.date_to).year
        if year_start != year_end:
            raise ValidationError(
                'Sólo puede escoger fecha de inicio y fin dentro del año en curso.'
            )

    def button_export(self):
        self.ensure_one()
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
                [('company_id', '=', self.company_id.id), '|', '|', '|', '|', '|',
                 ('code', '=like', '4%'), ('code', '=like', '5%'), ('code', '=like', '6%'), ('code', '=like', '7%'),
                 ('code', '=like', '8%'), ('code', '=like', '9%')]
            ).ids,
            'hierarchy_on': 'relation',
            'company_id': self.company_id.id,
        }
        if self.level != 'all':
            trial_wizard_dict.update({
                'hierarchy_on': 'relation',
                'limit_hierarchy_level': True,
                'show_hierarchy_level': int(self.level),
            })
        trial_wizard_id = self.env['trial.balance.report.wizard'].create(trial_wizard_dict)
        four_and_five_account_ids = self.env['account.account'].search(
            [('company_id', '=', self.company_id.id), '|', '|', '|', '|', '|',
             ('code', '=like', '4%'), ('code', '=like', '5%'), ('code', '=like', '6%'), ('code', '=like', '7%'),
             ('code', '=like', '8%'), ('code', '=like', '9%')]
        ).ids
        self.validate_data(trial_wizard_id)
        return trial_wizard_id.with_context({
            'show_signatures': True,
            'custom_report_name': 'Pérdidas y Ganancias',
            'pretty_rows': True,
            'show_4_and_5': four_and_five_account_ids,
            'unaffected_earnings_account': False,
            '4_and_5_text': u'RESULTADO DEL EJERCICIO',
        }).button_export_xlsx()

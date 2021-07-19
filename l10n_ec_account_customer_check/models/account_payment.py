# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date

from odoo.addons.l10n_ec_edi.models.amount_to_words import l10n_ec_amount_to_words

import textwrap

AMOUNT_IN_WORDS_LENGHT = 150 #numero de caracteres a usar para imprimir el monto en palabras en el cheque

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    _CHECK_TYPE = [
        ('insight', u'A la vista'),
        ('postdated', u'Posfechado')
    ]
    
    _STATES_CHECKS = [
        ('draft_check', u'Cheques borrador'),
        ('received_check', u'Cheques recibido'),
        ('returned_check', u'Cheques devueltos'),
        ('delayed_check', u'Cheques detenido'),
        ('deposited_check', u'Cheques depositado'),
        ('rejected_check', u'Cheques protestado'),
        ('cancel_check', u'Cheques anulados')
    ]
    
    deposit_date = fields.Date(
        string=u'Fecha de depósito',
        copy=False,
        help=u'Fecha en la que se prevee depositar el cheque, en base a la negociación realizada con el cliente'
        )
    date_rejected = fields.Date(
        string=u'Fecha de transacción',
        copy=False,
        help=u'La fecha de afectación contable en base a la cual se afecta al balance de la compañía'
        )
    rejected_move_id = fields.Many2one(
        'account.move',
        copy=False,
        string=u'Asiento contable',
        help=u'Este campo define los apuntes contables relacionados con el protesto del cheque'
        )
    bank_commission = fields.Float(
        string=u'Comisión bancaria',
        copy=False,
        help=u''
        )
    rejected_reason = fields.Char(
        string=u'Descripción',
        copy=False,
        help=u'Razón por la cual el cheque fue devuelto'
        )
    check_type = fields.Selection(
        selection=_CHECK_TYPE,
        string=u'Tipo de cheque',
        help=u'Un cheque es posfechado cuando la fecha de depósito es mayor que la fecha de registro'
        )
    state_check_control = fields.Selection(
        _STATES_CHECKS,
        string=u'Estado de cheque',
        track_visibility='onchange',
        #default='draft_check', #Comento la siguiente linea para evitar presentar el log si no es pago con cheque.
        copy=False,
        help=u'Es usado para mostrar en que estado del proceso se encuentra el cheque'
        )
    bank_account_partner_id = fields.Many2one(
        'res.partner.bank',
        string=u'Número de cuenta',
        track_visibility='onchange',
        help=u'Número de cuenta bancaria del cliente',
        )    

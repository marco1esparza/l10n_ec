# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning

from odoo.addons.l10n_ec_edi.models.amount_to_words import l10n_ec_amount_to_words



class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    #TODO hacer visible l10n_ec_payee_name cuando este seteado
    
    #TODO V15, evaluar si esta logica sigue siendo necesaria, talvez lo implementamos con un wizard similar
    #          al de impresión de cheques
    l10n_ec_payee_name = fields.Char(
        string='Payee Name',
        readonly=True, #editable from print check wizard
        track_visibility='onchange',
        help='The name that will be printed on the check, a few times the check is cashed by an intermediary'
        )
    
    ##SECCIÓN PARA OMITIR WIZARD DE NUMERACIÓN
    #     @api.model
    #     def create(self, vals):
    #         #Invocamos el metodo create para setear la siguiente secuencia
    #         res = super(AccountPayment, self).create(vals)
    #         if self.payment_method_code == 'check_printing' and\
    #            vals['payment_method_id'] == self.env.ref('account_check_printing.account_payment_method_check').id:
    #                 seq = self._update_sequence(vals['journal_id'], vals['check_number'])
    #                 seq.next_by_id()
    #         return res
    #     
    #     @api.onchange('journal_id')
    #     def _onchange_journal_id(self): 
    #         #Seteamos el campo check_number con el número de secuencia correspondiente
    #         res = super(AccountPayment, self)._onchange_journal_id()
    #         if self.journal_id.check_manual_sequencing and self.payment_method_code == 'check_printing':
    #             self.check_number = str(self.journal_id.check_sequence_id.number_next_actual).zfill(6)
    #         elif self.payment_method_code == 'check_printing':
    #             sequence = self.env['account.journal'].browse(self.journal_id.id).check_sequence_id
    #             if sequence :
    #                 self.check_number = str(sequence.number_next_actual).zfill(6)
    #             else:
    #                 self.check_number = str(1).zfill(6)
    #         else:
    #             self.check_number = ''
    #         return res
    #     
    #     @api.onchange('check_number','payment_method_code')
    #     def onchange_check_number(self):
    #         '''
    #         Mensaje de alerta cuando se modifica la secuencia de los cheques de forma manual
    #         '''
    #         res = {'value': {},'warning': {},'domain': {}}
    #         if self.payment_method_code == 'check_printing':
    #             try:
    #                 if self.journal_id.check_manual_sequencing:
    #                     current_number = self.journal_id.check_sequence_id.number_next_actual
    #                 else:
    #                     sequence = self.env['account.journal'].browse(self.journal_id.id).check_sequence_id
    #                     if sequence :
    #                         current_number = sequence.number_next_actual
    #                     else:
    #                         current_number = 1
    #                 if self.check_number:
    #                     check_number = str(self.check_number).zfill(6)
    #                 elif not current_number:
    #                     check_number = str('1').zfill(6)
    #                 elif current_number:
    #                     check_number = str(current_number).zfill(6)
    #                 check_number_ = int(check_number)
    #                 if check_number_ < 1:
    #                     raise ValidationError(u'El valor no puede ser menor a 1.')
    #                 if check_number_ > int(current_number):
    #                     res['warning'].update({
    #                         'title': u'Número de cheque manual',
    #                         'message': u'Se está cambiando manualmente el número de cheque. Esto implicará que los números que '
    #                                    u'se hayan saltado no serán utilizados. Los siguientes números a emitir pasarían a ser %d, %d, %d ...'
    #                                    % (check_number_ + 1, check_number_ + 2, check_number_ + 3)
    #                         })
    #                 elif check_number_ < int(current_number):
    #                     res['warning'].update({
    #                             'title': u'Número de cheque manual',
    #                             'message': u'Se está cambiando manualmente el número de cheque. Esto implicará la posibilidad de que '
    #                                        u'eventualmente se esté intentando utilizar un número ya utilizado y se produzcan errores '
    #                                        u'de validación. Los siguientes números a emitir pasarían a ser %d, %d, %d ...'
    #                                        %(check_number_ + 1, check_number_ + 2, check_number_ + 3)
    #                         })
    #                 res['value'].update({'check_number': check_number})
    #             except (TypeError, ValidationError) as e:
    #                 res['warning'].update({
    #                         'title': u'Valor inválido',
    #                         'message': u'Debe escribir un número positivo válido en el número de cheque.'
    #                     })
    #                 res['value'].update({'check_number': ''})
    #         else:
    #             res['value'].update({'check_number': ''})
    #         return res
    #     
    #     @api.multi
    #     def print_checks(self):
    #         '''
    #         Valida cheques antes de imprimir, omite el wizard del core
    #         '''
    #         self = self.filtered(lambda r: r.payment_method_id.code == 'check_printing' and r.state != 'reconciled')
    #         if not self[0].journal_id.check_manual_sequencing:
    #             if len(self) == 0:
    #                 raise ValidationError(u'Los pagos para imprimir como cheques deben tener "Cheque" seleccionado '
    #                                       u'como método de pago y no estar conciliados.')
    #             if any(payment.journal_id != self[0].journal_id for payment in self):
    #                 raise ValidationError(u'Para poder imprimir múltiples cheques de una, deben pertenecer al mismo diario.')
    #             return self.do_print_checks()
    #         else:
    #             return super(AccountPayment, self).print_checks()
    #         
    #     @api.multi
    #     def _update_sequence(self, journal_id, check_number):
    #          ''' 
    #          Actualiza la secuencias de los diarios
    #          '''
    #          sequence = self.env['account.journal'].browse(journal_id).check_sequence_id
    #          sequence.update({
    #             'number_next': int(check_number),
    #             'number_increment': 1,
    #         })
    #          return sequence
    #      
    #     @api.model
    #     def consume_check_sequence(self):
    #         '''
    #         Se depreca el consume de secuencias del cheque en la creacion del pago, prevale el valor que sugiere
    #         el sistema o digita el usuario
    #         '''
    #         return False
    #     
    #     @api.multi
    #     def post(self):
    #         '''
    #         Invocamos el método post para cuando se valide el pago en caso que sea de tipo cheque enviarlo
    #         a estado sent con esto evitamos que salgan en el menu de cheques por imprimir en el tablero de
    #         contabilidad
    #         '''
    #         res = super(AccountPayment, self).post()
    #         for payment in self:
    #             if payment.payment_method_code == 'check_printing' and payment.payment_type == 'outbound':
    #                 payment.journal_id.with_context(update_journal_sequence=True).check_next_number = int(payment.check_number) + 1
    #                 payment.state = 'sent'
    #         return res

    
    ##SECCIÓN CHEQUES POSFECHADOS
    #     @api.onchange('payment_date')
    #     def onchange_payment_date(self):
    #         #Este metodo setea la fecha del cheque en base a la la fecha del cobro
    #         vals = {'value': {}, 'warning': {}, 'domain': {}} 
    #         vals['value'].update({ 
    #             'check_date': self.payment_date
    #         })
    #         return vals
    #     check_date = fields.Date(
    #         string=u'Fecha del cheque',
    #         track_visibility='onchange',
    #         help=u'Fecha que el cheque tiene registrado'
    #         )
    
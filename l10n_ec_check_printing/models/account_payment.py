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
    
    @api.depends('payment_method_id', 'currency_id', 'amount')
    def _compute_check_amount_in_words(self):
        #overwrite Odoo core, Ecuadorian way is not currently supported by Odoo or num2words
        for pay in self:
            if not pay.country_code == 'EC':
                return super(AccountPayment, pay)._compute_check_amount_in_words()
            if pay.currency_id and pay.payment_method_id.code == 'check_printing':
                pay.check_amount_in_words = l10n_ec_amount_to_words(pay.amount)
            else:
                pay.check_amount_in_words = False

    def _check_fill_line(self, amount_str):
        #overwrite odoo core for Ecuador
        if self.country_code == 'EC':
            #parametros
            amount_str = amount_str or ''
            length = AMOUNT_IN_WORDS_LENGHT #maximum number of characters to print
            #relleno con " *"
            amount_str = amount_str.ljust(length, '*')
            amount_str = amount_str.replace("**", " *")
            amount_str = amount_str.replace("**", " *") #a veces queda un ultimo **
            return amount_str
        super(AccountPayment, self)._check_fill_line(amount_str)
    
    def do_print_checks(self):
        #Overwrite Odoo core because validations should be by journal not by company 
        if not self[0].country_code == 'EC':
            #odoo core ya valida q sean del mismo diario, asi que todas son de la misma compañia y por ende del mismo pais
            return super(AccountPayment, self).do_print_checks()
        if not self[0].company_id.city:
            raise ValidationError(_("You have to setup a city in your company form, it is needed to print the issuing city on the check."))
        return super(AccountPayment, self).do_print_checks()
    
    @api.constrains('check_number', 'journal_id')
    def _constrains_check_number(self):
        #extra validations for Ecuador
        #TODO, el core de Odoo en estado borrador permite numeros de cheque duplicado, bug reportado #xxxxxx
        #      si no lo arreglan ellos tendremos que arreglarlo nosotros
        for pay in self:
            if pay.country_code == 'EC':
                if not pay.check_number:
                    return
                if len(pay.check_number) != 6:
                    raise ValidationError(_('Ecuadorian check numbers must have 6 digits, you should add some zeros to the left?'))
                if not pay.check_number.isnumeric():
                    raise ValidationError(_('Ecuadorian check numbers must be a positive number'))
        return super(AccountPayment, self)._constrains_check_number()

    def action_print_check(self):
        '''
        Action que permite imprimir el  cheque nuevamente si este ya tiene asignado un numero.
        '''
        if self.check_number:
            check = self.env['print.prenumbered.checks'].create({'next_check_number': self.check_number})
            return check.with_context(payment_ids=self.id).print_checks()
        else:
            raise ValidationError(u'El Pago no cuenta con un número de cheque asignado.')

    def print_checks(self):
        #ask the user for the check beneficiary name
        res = super(AccountPayment, self).print_checks()
        if not self[0].journal_id.check_manual_sequencing:
            if len(self) == 1:
                #solo cuando es un cheque individual pregunto por el beneficiario
                res['context']['default_l10n_ec_check_beneficiary_name'] = self.partner_id and self.partner_id.commercial_partner_id.name or self.l10n_ec_check_beneficiary_name
            
            #FIX until Odoo one beautifull day accepts PR https://github.com/odoo/odoo/pull/67303/files
            self.env.cr.execute("""
                  SELECT payment.id
                    FROM account_payment payment
                    JOIN account_move move ON movE.id = payment.move_id
                   WHERE journal_id = %(journal_id)s
                     AND check_number IS NOT NULL
                ORDER BY check_number::INTEGER DESC
                   LIMIT 1
            """, {
                'journal_id': self.journal_id.id,
            })
            last_printed_check = self.browse(self.env.cr.fetchone())
            number_len = len(last_printed_check.check_number or "")
            next_check_number = '%0{}d'.format(number_len) % (int(last_printed_check.check_number) + 1)
            res['context']['default_next_check_number'] = next_check_number
            #END OF FIX
            
        return res

    def _check_build_page_info(self, i, p):
        page = super(AccountPayment, self)._check_build_page_info(i, p)
        amount_in_word = page['amount_in_word']
        lines = textwrap.wrap(amount_in_word, int(AMOUNT_IN_WORDS_LENGHT/2))
        l10n_ec_check_beneficiary_name = self.l10n_ec_check_beneficiary_name or self.commercial_partner_id and self.commercial_partner_id.name or '.'
        page.update({
            'city_and_date': self.company_id.city + ', ' + format_date(self.env, self.date, date_format='yyyy-MM-dd'),
            'partner_name': l10n_ec_check_beneficiary_name,
            'amount_line1': lines[0],
            'amount_line2': lines[1],
        })
        return page
    
    l10n_ec_check_beneficiary_name = fields.Char(
        string='Check Beneficiary',
        tracking=True,
        help='Supplier name to print in check, usefull as sometimes it is required to issue the check to other supplier or to a third party'
        )
    check_number = fields.Char(
        tracking=True,
        )

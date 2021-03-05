# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_ec_edi.models.amount_to_words import l10n_ec_amount_to_words


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
            length = 150 #maximum number of characters to print
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

    def print_checks(self):
        #ask the user for the check beneficiary name
        res = super(AccountPayment, self).print_checks()
        if not self[0].journal_id.check_manual_sequencing:
            if len(self) == 1:
                #solo cuando es un cheque individual pregunto por el beneficiario
                res['context']['default_l10n_ec_check_beneficiary_name'] = self.partner_id.commercial_partner_id.name
        return res

    l10n_ec_check_beneficiary_name = fields.Char(
        string='Check Beneficiary',
        help='Supplier name to print in check, usefull as sometimes it is required to issue the check to other supplier or to a third party'
        )
    
    
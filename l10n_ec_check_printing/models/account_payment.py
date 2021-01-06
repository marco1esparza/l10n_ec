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
    
    def do_print_checks(self):
        #Overwrite Odoo core because validations should be by journal not by company
        if not self.country_code == 'EC':
            return super(AccountPayment, self).do_print_checks()
        if not self.company_id.city:
            raise ValidationError(_("You have to setup a city in your company form, it is needed to print the issuing city on the check."))
        check_layout = self.journal_id.l10n_ec_check_printing_layout_id
        if not check_layout:
            raise ValidationError(_("Something went wrong with Check Layout, please select another layout in Invoicing/Configuration/Journals and try again."))
        self.write({'is_move_sent': True})
        return check_layout.report_action(self)
    
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
    
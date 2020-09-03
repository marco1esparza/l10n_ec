# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

def migrate(cr, version):
    l10n_ec_delete_view_accounts(cr)

def l10n_ec_delete_view_accounts(cr):
    '''
    Elimina las cuentas tipo vistas del account_account
    Elimina todas las cuentas del account_account_template
    Desinstala el modulo account_parent
    '''
    cr.execute("DELETE FROM account_account WHERE user_type_id IN (SELECT id FROM account_account_type WHERE type = 'view')")
    cr.execute("DELETE FROM account_account_template")
    cr.execute("UPDATE ir_module_module SET state = 'to remove' where name = 'account_parent'")

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID
import odoo

def migrate(cr, version):
    l10n_ec_delete_view_accounts(cr)
    l10n_ec_set_doc_type_no_update_false(cr)

def l10n_ec_delete_view_accounts(cr):
    '''
    Elimina las cuentas tipo vistas del account_account
    Elimina todas las cuentas del account_account_template
    Desinstala el modulo account_parent
    '''
    cr.execute("DELETE FROM account_account WHERE user_type_id IN (SELECT id FROM account_account_type WHERE type = 'view')")
    cr.execute("DELETE FROM account_account_template")
    cr.execute("UPDATE ir_module_module SET state = 'to remove' where name = 'account_parent'")

def l10n_ec_set_doc_type_no_update_false(cr):
    '''
    Setea el ir.model.data de los tipos de documentos a noupdate = False para poder actualizarlos.
    '''
    registry = odoo.registry(cr.dbname)
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_record_ids = env['ir.model.data'].search([
        ('model', 'in', ['l10n_latam.document.type']),
        ('module', 'like', 'l10n_ec')
    ]).ids
    if xml_record_ids:
        cr.execute("update ir_model_data set noupdate = 'f' where id in %s", (tuple(xml_record_ids),))

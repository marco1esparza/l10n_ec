from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    l10n_ec_delete_view_accoutns(cr)


def l10n_ec_delete_view_accoutns(cr):
    cr.execute("DELETE FROM account_account WHERE user_type_id IN (SELECT id FROM account_account_type WHERE type = 'view')")
    aux = 1

# -*- coding: utf-8 -*-

from odoo import api
from odoo import SUPERUSER_ID

def migrate(cr, version):
    # Migrate para eliminar las vistas antes de actualizar el modulo l10n_ec_account_extended
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_view = env.ref('l10n_ec_edi.view_users_printer_point_form', raise_if_not_found=False)
    if xml_view:
        cr.execute("""delete from ir_ui_view where id = %s;""" % xml_view.id)
    xml_view = env.ref('l10n_ec_edi.view_users_simple_modif_printer_point_form', raise_if_not_found=False)
    if xml_view:
        cr.execute("""delete from ir_ui_view where id = %s;""" % xml_view.id)
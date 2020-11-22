# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    not_show_on_dashboard_withhold_journal(cr)
    
def not_show_on_dashboard_withhold_journal(cr):
    # Se busca los Journal para Retenciones de Compras y Ventas.
    # Para Inactivar que se muestren en el Dashboard
    env = api.Environment(cr, SUPERUSER_ID, {})
    sale_withhold_journal = env.ref("l10n_ec_withhold.withhold_sale")
    purchase_withhold_journal = env.ref("l10n_ec_withhold.withhold_purchase")
    sale_withhold_journal.show_on_dashboard = False
    purchase_withhold_journal.show_on_dashboard = False

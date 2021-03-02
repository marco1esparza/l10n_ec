# -*- coding: utf-8 -*-

from odoo import api
from odoo import SUPERUSER_ID

from openupgradelib import openupgrade

@openupgrade.migrate(use_env=True)
def migrate(env, version):
    repair_broken_view(env)

@openupgrade.logging()
def repair_broken_view(env):
    # Migrate para recargar vistas del base para que no explote al instalar nuestras vistas
    # parece que Odoo modifico algo en el core y causa que sin reinstalar el base se rompa la instalación
    broken_view = env.ref('base.user_groups_view')
    broken_view.unlink()
    openupgrade.load_data(
        env.cr, 'base', 'views/res_users_views.xml',
        )
    
    
    
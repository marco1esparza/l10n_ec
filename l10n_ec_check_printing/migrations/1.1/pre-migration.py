# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    make_paperformat_updatable(env)
    
@openupgrade.logging()
def make_paperformat_updatable(env):
    #setear el xml_id como no update = False
    openupgrade.set_xml_ids_noupdate_value(env,"l10n_ec_check_printing",["paperformat_check_ec","action_print_check_top"],False,)

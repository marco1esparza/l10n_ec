# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID
from openupgradelib import openupgrade
 
@openupgrade.migrate()
def migrate(env, version):
    recompute_account_root(env)
 
@openupgrade.logging()
def recompute_account_root(env):
    # re-computes the first 2 digits of the account.
    accounts = env['account.account'].search([])
    accounts._compute_account_root()

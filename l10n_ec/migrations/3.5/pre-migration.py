# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, SUPERUSER_ID

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    set_document_type_updatable(env)

@openupgrade.logging()
def set_document_type_updatable(env):
    openupgrade.logged_query(env.cr,'''
        --sets the ecuadorian document types as updatables      
        UPDATE ir_model_data as imd
        SET noupdate = False
        WHERE module = 'l10n_ec'
        AND model = 'l10n_latam.document.type'
        ''')
    
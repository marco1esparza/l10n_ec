# -*- coding: utf-8 -*-
# Copyright 2021 Trescloud <https://www.trescloud.com>
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    '''Se realiza la migración de los cambios para el label de clientes con el módulo ya instalado'''
    from odoo.addons.l10n_ec_ecommerce import _l10n_ec_set_ecommerce_labels
    _l10n_ec_set_ecommerce_labels(env.cr, version)

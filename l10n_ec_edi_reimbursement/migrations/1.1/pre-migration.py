# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    update_xml_id_refund_product(env)

@openupgrade.logging()
def update_xml_id_refund_product(env):
    openupgrade.rename_xmlids(env.cr, [
        ('l10n_ec_account_extended.refund_default_product', 'l10n_ec_edi_reimbursement.refund_default_product'), #Producto de reembolsos
    ])
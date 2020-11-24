# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    set_sri_tax_support(env)

def set_sri_tax_support(env):
    '''
    Seteando el sustento tributario para facturas migradas
    '''
    openupgrade.logged_query(
        env.cr, """
            update account_move 
            set l10n_ec_sri_tax_support_id=t2.sri_tax_support_id from (
                select 
                    invoice_id,
                    t1.move_id, 
                    sri_tax_support_id
                from (
                    select distinct 
                        invoice_id,
                        move_id 
                    from account_move_line
                    where invoice_id is not null
                    ) as t1 join account_invoice ai
                        on t1.invoice_id=ai.id
                        where sri_tax_support_id is not null
                ) as t2
            where account_move.id=t2.move_id
    """,
    )

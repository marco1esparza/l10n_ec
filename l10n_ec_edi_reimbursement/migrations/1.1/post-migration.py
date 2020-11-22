# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    remove_orphan_refunds(env)
    update_latam_document_type(env)
    update_authorization(env)
    update_move_id(env)

def remove_orphan_refunds(env):
    '''
    Eliminando reembolsos huerfanos
    '''
    openupgrade.logged_query(
        env.cr, """
        delete from account_refund_client where refund_invoice_id is null
    """,
    )

def update_latam_document_type(env):
    '''
    Actualizando el tipo de documento latam
    '''
    openupgrade.logged_query(
        env.cr, """
        update account_refund_client set l10n_latam_document_type_id=document_invoice_type_id
    """,
    )

def update_authorization(env):
    '''
    Copiando el nombre de la autorizacion
    '''
    openupgrade.logged_query(
        env.cr, """
        update account_refund_client arc
        set "authorization" = t.name from (
            select 
                id,
                name
            from sri_authorizations
            ) as t
        where arc.authorizations_id = t.id
    """,
    )

def update_move_id(env):
    '''
    Estableciendo la relacion con factura
    '''
    openupgrade.logged_query(
        env.cr, """
        update account_refund_client arc
        set move_id = t.move_id from (
            select distinct 
                invoice_id,
                move_id 
            from account_move_line
            where invoice_id is not null
            ) as t
        where arc.refund_invoice_id = t.invoice_id
    """,
    )

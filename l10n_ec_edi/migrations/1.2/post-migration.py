# -*- coding: utf-8 -*-
# Copyright 2022 Trescloud <https://www.trescloud.com>
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openupgradelib import openupgrade


@openupgrade.logging()
def delete_duplicate_attachments(env):
    '''
    Eliminando documentos adjuntos duplicados en las facturas, nos quedamos con el xml y el pdf mas antiguo
    '''
    env.cr.execute('''
        select distinct res_id as invoice_id from ir_attachment where res_model='account.move'
    ''')
    records = env.cr.dictfetchall()
    for record in records:
        invoice_id = record.get('invoice_id')
        #Se separa la condicion para garantizar que quede 1 xml y 1 pdf, los mas antiguos
        xml_attachment_to_delete = env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', invoice_id), ('name', 'ilike', '%.xml')], order='create_date, id')[1:].ids
        pdf_attachment_to_delete = env['ir.attachment'].search([('res_model', '=', 'account.move'), ('res_id', '=', invoice_id), ('name', 'ilike', '%.pdf')], order='create_date, id')[1:].ids
        #El borrador se hace por sql pues en un unlik con el orm saltaba el siguiente mensaje "Al ser un EDI que se envió al gobierno, no se puede desvincular el adjunto."
        #Se pone el delete dentro del for para ir eliminando poco a poco, por ejemplo para rvingenieria son 210 mil adjuntos a eliminar y todo junto se muere
        if xml_attachment_to_delete or pdf_attachment_to_delete:
            env.cr.execute('''
                delete from ir_attachment where id in %s
            ''', (tuple(xml_attachment_to_delete + pdf_attachment_to_delete),))
        
@openupgrade.migrate(use_env=True)
def migrate(env, version):
    delete_duplicate_attachments(env)
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID

def _change_email_template_edi_invoice(cr, registry):
    '''
    Este método se encarga de modificar la plantilla de correo para las Facturas.
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env['mail.template'].search([('name', '=', 'Invoice: Send by email')])
    if template:
        template[0].subject = "${object.company_id.name} (${not object.l10n_latam_document_type_id and 'Invoice' or object.l10n_latam_document_type_id.report_name or object.l10n_latam_document_type_id.name}  ${object.name or 'n/a'})"
        template[0].report_name = "${(object.name or '').replace('/','_')}${object.state == 'draft' and '_draft' or ''}"

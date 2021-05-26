# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    #Columns
    include_electronic_document_in_ats = fields.Boolean(
        string=u'Incluir retenciones electrónicas emitidas a proveedores en el ATS',
        default = True,
        help=u'Active esta opción si desea incluir las retenciones electrónicas emitidas a proveedores en el ATS.'
        )

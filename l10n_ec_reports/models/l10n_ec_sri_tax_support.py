# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class L10nEcSRITaxSupport(models.Model):
    _name = 'l10n_ec.sri.tax.support'
    _order = 'priority'
    _inherit = ['mail.thread']

    def name_get(self):
        '''
        Concatena el código y el nombre del sustento tributario
        '''
        result = []
        for support in self:
            new_name = (support.code and '[' + support.code + '] ' or '') + support.name
            result.append((support.id, new_name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        '''
        Permite buscar ya sea por nombre o por codigo del sustento tributario
        '''
        if args is None:
            args = []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        support = self.search(domain + args, limit=limit)
        return support.name_get()

    #Columns
    code = fields.Char(
        string='Code', 
        size=2, 
        track_visibility='onchange',
        help='Field of two digits that indicate the code for this tax support'
        )
    name = fields.Char(
        string='Name',
        size=255,
        track_visibility='onchange',
        help='Name of tax support'
        )
    priority = fields.Integer(
        string='Priority',
        track_visibility='onchange',
        help='Priority of tax support'
        )
    active = fields.Boolean(
        string='Active',
        default=True,
        track_visibility='onchange',
        help='This field determines whether the tax support is active or not'
        )
    

class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'
     
    #Columns
    l10n_ec_sri_tax_support_ids = fields.Many2many(
        'l10n_ec.sri.tax.support',
        'document_type_sri_tax_support_rel',
        'document_type_id',
        'tax_support_id',
        string='Tax support lines',
        help=''
        )     

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Company(models.Model):
    _inherit = 'res.company'
    
    def _digital_signature(self):
        """
        Asigna la firma digital en estado confirmado, caso contrario
        deja vacio 
        """
        for company in self:
            valid_cert = self.env['l10n_ec.digital.signature'].search([('l10n_ec_company_id', '=', company.id), ('l10n_ec_state', '=', 'confirmed')], limit=1)
            if valid_cert:
                company.l10n_ec_digital_cert_id = valid_cert[0] 
            else:
                company.l10n_ec_digital_cert_id = False

    _ENVIRONMENT_TYPE = [
        ('1', 'Testing Environment'),
        ('2', 'Production Environmet')
    ]

    #Columns
    l10n_ec_legal_name = fields.Char(
        string=u'Nombre legal',
        track_visibility=u'onchange',
        required=True,
        help=u'El nombre de la compañía a ser enviado al SRI en documentos electrónicos, 103, 104, ATS, etc. Utilizado también para enviarlo al IESS en archivos CSV.'
        )
    l10n_ec_environment_type = fields.Selection(
        _ENVIRONMENT_TYPE,
        string='Type of Environment',
        default='2',
        help='Identifica si Odoo emitira los documentos electronicos en un Ambiente de Pruebas o de Produccion'
    )
    l10n_ec_digital_cert_id = fields.Many2one(
        'l10n_ec.digital.signature',
        compute='_digital_signature',
        string="Digital Signature",
        help='Digital signature valid to send electronic documents to SRI'
    )
    l10n_ec_special_contributor_number = fields.Char(
        string='Special Tax Contributor Number',
        track_visibility='onchange',
        help='If set, your company is considered a Special Tax Contributor, this number will be printed in electronic invoices and reports'
        )
    l10n_ec_forced_accounting = fields.Boolean(
        string='Forced to Keep Accounting Books',
        track_visibility='onchange',
        default=True,
        help='If set you are obligated to keep accounting, it will be used for printing electronic invoices and reports'
        )

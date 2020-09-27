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
            valid_cert = self.env['l10n_ec.digital.signature'].search([('company_id', '=', company.id), ('state', '=', 'confirmed')], limit=1)
            if valid_cert:
                company.l10n_ec_digital_cert_id = valid_cert[0] 
            else:
                company.l10n_ec_digital_cert_id = False

    _ENVIRONMENT_TYPE = [
        ('0', 'Demo Environment'),
        ('1', 'Testing Environment'),
        ('2', 'Production Environment'),
    ]

    #Columns
    l10n_ec_legal_name = fields.Char(
        string=u'Nombre legal',
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
        help='For signing SRI electronic documents, configure one in Accounting / Configuration / Digital Signatures'
    )
    l10n_ec_special_contributor_number = fields.Char(
        string='Special Tax Contributor Number',
        help='If set, your company is considered a Special Tax Contributor, this number will be printed in electronic invoices and reports'
        )
    l10n_ec_forced_accounting = fields.Boolean(
        string='Forced to Keep Accounting Books',
        default=True,
        help='If set you are obligated to keep accounting, it will be used for printing electronic invoices and reports'
        )

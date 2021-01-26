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

    def _get_l10n_ec_environment_type(self):
        """
        Se obtiene el tipo de entorno, requerido para entornos Demo.
        """
        self.ensure_one()
        if self.l10n_ec_environment_type and self.l10n_ec_environment_type == '0':
            return '1'
        else:
            return self.l10n_ec_environment_type

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
        ondelete='restrict',
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
    l10n_ec_regime = fields.Selection(
        [('regular', 'Regimen Regular (sin msgs adicionales en el RIDE)'),
         ('micro', 'Régimen Impositivo para  Microempresas')],
        string=u"Regimen",
        default='regular',
        required=True,
        help=u"Mostrará el mensaje adicional en el RIDE 'Regimen Contribuyente Regimen Microempresas', utilicelo si su empresa esta en los catastros del SRI.\n"
        u"No tiene efecto en el computo de retenciones del sistema, si desea desactivar las retenciones utilice el campo emitir retenciones\n"
        )
    l10n_ec_withhold_agent = fields.Selection(
        [('not_designated', 'Sin designación (sin msgs adicionales en el RIDE)'),
         ('designated_withhold_agent', 'Agente de Retención Designado')],
        string=u"Agente de Retención",
        default='not_designated',
        required=True,
        help=u"Mostrará el mensaje adicional en el RIDE 'Agente de Retención No Resolución 12345' conforme la Resolución Nro. NAC-DGERCGC20-00000057\n"
        u"No tiene efecto en el computo de retenciones del sistema, si desea desactivar las retenciones utilice el campo emitir retenciones\n"
        )
    l10n_ec_wihhold_agent_number = fields.Char(
        string=u"Agente Ret. No.",
        help=u"Ultimos digitos del número de resolución del SRI donde se declara que se es agente de retención.\n"
        u"Si el número de Resolución es NAC-DNCRASC20-00001234 entonces ell No. Resolución sería: 1234",
        )

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
import re


class L10nLatamDocumentType(models.Model):
    _inherit = "l10n_latam.document.type"
    
    def _format_document_number(self, document_number):
        self.ensure_one()
        if self.country_id != self.env.ref("base.ec"):
            return super()._format_document_number(document_number)
        if not document_number:
            return False
        if (
            not re.match(r"\d{3}-\d{3}-\d{9}$", document_number)
            and self.l10n_ec_check_format
            and not self.env.context.get("l10n_ec_foreign", False)
        ):
            raise UserError(
                _(u"Ecuadorian Document %s must be like 001-001-123456789")
                % (self.display_name)
            )
        return document_number
    
    _EC_TYPE = [
        ('out_invoice', 'Customer Document'),
        ('in_invoice', 'Supplier Document'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Supplier Refund'),
        ('out_waybill', 'Issued Waybill'),
        ('out_withhold', 'Customer Withhold'),
        ('in_withhold', 'Supplier Withhold'),
        ('other', 'Others'),
    ]

    _EC_AUTHORIZATION = [
        ('none', 'None'), #use authorization 9999999999 instead
        ('own', 'Issued by my company'),
        ('third', 'Issued by Third Parties')
    ]

    l10n_ec_type = fields.Selection(
        _EC_TYPE, 
        string='Ecuadorian Type',
        help='Indicates the aplicability of the document',
        )
    l10n_ec_authorization = fields.Selection(
        _EC_AUTHORIZATION,
        default='none',
        string='Authorization',
        help='Ecuadorian tax authority requires an authorization for certain documents',
        )
    l10n_ec_require_vat = fields.Boolean(
        string='Require Vat Number', 
        help='Force the registration of customer vat number on invoice validation',
        )
    internal_type = fields.Selection(
        selection_add=[
            ("purchase_liquidation", "Purchase Liquidation"),
        ]
    )
    l10n_ec_check_format = fields.Boolean(
        string="Check Number Format EC", default=False
    )
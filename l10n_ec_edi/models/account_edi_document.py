# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from lxml import etree
import base64

class AccountEdiDocument(models.Model):
    _inherit = 'account.edi.document'

    def _get_additional_info(self):
        #TODO TRESCLOUD, discuss with Odoo what should be in the notes and then remove method
        self.ensure_one()
        additional_info = super()._get_additional_info()
        if self.move_id.is_withholding():
            additional_info = []
            get_invoice_partner_data = self.move_id.partner_id.get_invoice_partner_data()
            if get_invoice_partner_data['invoice_email']:
                additional_info.append('Email: %s' % get_invoice_partner_data['invoice_email'])
            if get_invoice_partner_data['invoice_address']:
                additional_info.append('Direccion: %s' % get_invoice_partner_data['invoice_address'])
            if get_invoice_partner_data['invoice_phone']:
                additional_info.append('Telefono: %s' % get_invoice_partner_data['invoice_phone'])
        return additional_info

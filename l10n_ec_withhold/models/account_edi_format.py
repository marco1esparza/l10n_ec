# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.tests.common import Form
from odoo.exceptions import UserError, ValidationError, except_orm
from odoo.tools import float_repr

import re
from datetime import date, datetime
import logging
import base64

import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from time import sleep

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'
    
    #Redefinitions based on account_edi
    def _is_required_for_invoice(self, invoice):
        """ Indicate if this EDI must be generated for the move passed as parameter.
        :param invoice: An account.move having the invoice type.
        :returns:       True if the EDI must be generated, False otherwise.
        """
        self.ensure_one()
        withhold = invoice #for ease reading
        if withhold.country_code == 'EC' and self.code == 'l10n_ec_tax_authority':
            is_required_for_invoice = False
            if not withhold.l10n_ec_printer_id.allow_electronic_document:
                #first lets verify that the printer point is an electronic one
                return is_required_for_invoice
            #Retenciones compra
            if withhold.is_withholding() and withhold.l10n_ec_withhold_type == 'in_withhold':
                is_required_for_invoice = True
            return is_required_for_invoice
        return super()._is_required_for_invoice(withhold)
    

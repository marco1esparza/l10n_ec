# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

class WebsiteSale(WebsiteSale):
    
    def _get_mandatory_billing_fields(self):
        result = super()._get_mandatory_billing_fields()
        if request.website.company_id.country_code == 'EC':
            result.append("company_name","vat")
        return result
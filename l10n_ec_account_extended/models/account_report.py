# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import copy
import json
import io
import logging
import lxml.html
import datetime
import ast
from collections import defaultdict
from math import copysign

from dateutil.relativedelta import relativedelta

from odoo.tools.misc import xlsxwriter
from odoo import models, fields, api, _
from odoo.tools import config, date_utils, get_lang
from odoo.osv import expression
from babel.dates import get_quarter_names
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action

_logger = logging.getLogger(__name__)


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def get_account_codes(self, account):
        # Hacemos super para cambiar la logica estandar de ordenamiento de cuentas por el id del group,
        # y tomamos en cuenta el prefijo de inicio de agrupacion
        res = super().get_account_codes(account)
        if account.company_id.country_code == 'EC':
            for index, code in enumerate(res):
                aux = list(code)
                group = self.env['account.group'].browse(code[0])
                aux[0] = group.code_prefix_start or str(code[0])
                res[index] = tuple(aux)
        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import models

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

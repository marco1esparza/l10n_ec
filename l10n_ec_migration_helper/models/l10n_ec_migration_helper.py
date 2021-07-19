# -*- coding: utf-8 -*-

import copy
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import formatLang, format_date, parse_date

    
class L10nEcMigrationHelper(models.AbstractModel):
    _name = 'l10n_ec.migration.helper'
    _description = 'Programa de migración de Trescloud'
        
    name = fields.Char()
        

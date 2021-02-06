# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.date_utils import get_month, get_fiscal_year
from odoo.tools.misc import format_date

import re
from collections import defaultdict
import json


class ReSequenceWizard(models.TransientModel):
    _inherit = 'account.move.reversal'

    def resequence(self):
        #impedimos la renumeración de asientos contables con "use documents" (ejemplo facturas)
        journal = self.move_ids[0] #todos son del mismo diario
        if journal.l10n_latam_use_documents:
            raise UserError(_('You can not reorder sequence when the journal has the option "Use Documents?".'))
        return super(ReSequenceWizard, self).resequence()
    
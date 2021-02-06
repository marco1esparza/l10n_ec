# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ReSequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'

    def resequence(self):
        #impedimos la renumeración de asientos contables con "use documents" (ejemplo facturas)
        journal = self.move_ids[0] #todos son del mismo diario
        if journal.l10n_latam_use_documents:
            raise UserError(_('You can not reorder sequence when the journal has the option "Use Documents?".'))
        return super(ReSequenceWizard, self).resequence()
    
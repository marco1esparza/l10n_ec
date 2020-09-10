# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WizardReceiveWithhold(models.TransientModel):
    _name = 'wizard.receive.withhold'

    def action_receive(self):
        '''
        Este metodo se encarga de mandar a generar la retencion
        '''
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if active_model == 'account.move' and active_ids:
            invoices = self.env[active_model].browse(active_ids)
            for invoice in invoices:
                if not invoice.type == 'out_invoice':
                    raise ValidationError(u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')
                if not invoice.state in ['posted']:
                    raise ValidationError(u'Solo se puede registrar retenciones sobre facturas abiertas o pagadas.')
            if len(list(set(invoices.mapped('partner_id').mapped('commercial_partner_id').mapped('id')))) > 1:
                raise ValidationError(u'Las facturas seleccionadas no pertenecen al mismo cliente.')
            #Duplicamos solo la cabecera de la factura(va hacer funcion de cabecera de retencion), nada de lineas, usamos la primera factura
            l10n_latam_document_type_id = self.env.ref('l10n_ec.ec_03').id
            journal_id = self.env.ref('l10n_ec_withhold.withhold_sale').id
            withhold = invoices[0].copy(default={'l10n_latam_document_type_id': l10n_latam_document_type_id,
                                          'journal_id': journal_id,
                                          'invoice_line_ids': [], 
                                          'line_ids': [], 
                                          'l10n_ec_withhold_line_ids': [],
                                          'l10n_ec_invoice_payment_method_ids': [],
                                          'l10n_ec_authorization': False,
                                          'type':'entry',
                                          'withhold_type': 'customer'})
            withhold.l10n_ec_invoice_ids = [(6, 0, invoices.ids)]
            return self.view_withhold(withhold)
  
    def view_withhold(self, withhold):
        '''
        '''
        [action] = self.env.ref('account.action_move_journal_line').read()
        action['domain'] = [('id', 'in', [withhold.id])]
        return action

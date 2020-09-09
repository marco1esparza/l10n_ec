# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class WizardReceiveWithhold(models.TransientModel):
    _name = 'wizard.receive.withhold'

    @api.multi
    def action_receive(self):
        '''
        Este metodo se encarga de mandar a generar la retencion
        '''
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if active_model == 'account.invoice' and active_ids:
            invoices = self.env[active_model].browse(active_ids)
            for invoice in invoices:
                if not invoice.type == 'out_invoice':
                    raise ValidationError(u'En Odoo las retenciones sobre múltiples facturas solo se permiten en facturas de ventas.')
                if not invoice.state in ['open', 'paid']:
                    raise ValidationError(u'Solo se puede registrar retenciones sobre facturas abiertas o pagadas.')
            if len(list(set(invoices.mapped('partner_id').mapped('commercial_partner_id').mapped('id')))) > 1:
                raise ValidationError(u'Las facturas seleccionadas no pertenecen al mismo cliente.')
            ctx = {}
            if self.env.context:
                ctx = self.env.context.copy()
            ctx['default_type'] = 'sale_withhold'
            ctx['active_ids'] = active_ids
            ctx['active_model'] = active_model
            withhold = self.env['account.withhold'].with_context(ctx).create({})
            return self.view_withhold([withhold.id])

    @api.multi
    def view_withhold(self, withhold_ids):
        '''
        Este metodo muestra la reteccion
        '''
        action = 'ecua_tax_withhold.action_account_withhold_sale'
        view = 'ecua_tax_withhold.view_account_withhold_form_sale'
        action = self.env.ref(action)
        result = action.read()[0]
        if len(withhold_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(withhold_ids) + ")]"
        elif len(withhold_ids) == 1:
            res = self.env.ref(view)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = withhold_ids[0]
        return result

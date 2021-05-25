# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def create_missing_stock_account(self):
        company_ids = self.env['res.company'].search([])
        company_ids._create_inventory_loss_account()
        company_ids._create_production_account()
        company_ids._create_scrap_account()

    def _create_inventory_loss_account(self):
        '''
        Metodo que crea la cuenta de inventario por defecto para las ubicacion virtual Ajuste de inventario.
        '''
        for company in self.filtered(lambda x: x.country_code == 'EC'):
            parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
            if parent_location:
                location = self.env['stock.location'].search([('name', '=', 'Inventory adjustment'),
                                                              ('usage', '=', 'inventory'),
                                                              ('location_id', '=', parent_location.id),
                                                              ('company_id', '=', company.id)])
                if location and (not location.valuation_in_account_id or not location.valuation_out_account_id):
                    account = self.env['account.account'].search([
                        ('code', '=', '51040802'),
                        ('company_id', '=', company.id)
                    ])
                    if account:
                        location.valuation_in_account_id = account
                        location.valuation_out_account_id = account

    def _create_production_account(self):
        '''
        Metodo que crea la cuenta de inventario por defecto para las ubicacion virtual Produccion.
        '''
        for company in self.filtered(lambda x: x.country_code == 'EC'):
            parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
            if parent_location:
                location = self.env['stock.location'].search([('name', '=', 'Production'),
                                                              ('usage', '=', 'production'),
                                                              ('location_id', '=', parent_location.id),
                                                              ('company_id', '=', company.id)])
                if location and (not location.valuation_in_account_id or not location.valuation_out_account_id):
                    account = self.env['account.account'].search([
                        ('code', '=', '110302'),
                        ('company_id', '=', company.id)
                    ])
                    if account:
                        location.valuation_in_account_id = account
                        location.valuation_out_account_id = account

    def _create_scrap_account(self):
        '''
        Metodo que crea la cuenta de inventario por defecto para las ubicacion virtual Desperdicio.
        '''
        for company in self.filtered(lambda x: x.country_code == 'EC'):
            parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
            if parent_location:
                location = self.env['stock.location'].search([('name', '=', 'Scrap'),
                                                              ('usage', '=', 'inventory'),
                                                              ('location_id', '=', parent_location.id),
                                                              ('company_id', '=', company.id),
                                                              ('scrap_location', '=', True)])
                if location and (not location.valuation_in_account_id or not location.valuation_out_account_id):
                    account = self.env['account.account'].search([
                        ('code', '=', '51040803'),
                        ('company_id', '=', company.id)
                    ])
                    if account:
                        location.valuation_in_account_id = account
                        location.valuation_out_account_id = account
